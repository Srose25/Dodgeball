# Dodgeball! Shared Protocol — v1

Status: SP-6 design gate complete. This document defines the contract for SP-7; it does not implement transport.

## Scope and invariants

- Transport: browser-native WebSocket carrying one UTF-8 JSON object per message.
- Protocol version: `1` in every message's `version` field.
- Maximum decoded message size: `16,384` bytes (`16 KiB`) of UTF-8 JSON.
- The first client message must be `hello`; no lobby or gameplay message is valid before it.
- The server is authoritative. Clients send intent only and never submit positions, velocities, damage, scores, collision results, turn changes, or winners.
- Gameplay `seq` values are strictly increasing per connection. A duplicate or lower sequence is rejected and never applied.
- Client-originated lobby/setup messages use a `request_id`; gameplay commands use `seq`.
- The server assigns connection/player identity. Client-supplied identity is not authoritative.
- Every rejection uses `command_rejected` when the connection remains usable and includes a machine-readable `code` and human-readable `message`.

The machine-readable shape is in [`protocol_schema.json`](protocol_schema.json). The pure, transport-free envelope checks used by design tests are in `shared/protocol.py`.

## Fixed simulation and snapshot policy

The server advances one deterministic simulation at `60 Hz` (`1/60` second per tick). It drains commands received before the authoritative tick cutoff, assigns a monotonically increasing server receive ordinal, and orders accepted candidates by:

1. server receive ordinal;
2. client gameplay `seq` as a tie-breaker.

Commands that arrive after the cutoff are rejected as `TURN_EXPIRED` or `BAD_PHASE` as appropriate. Rejected commands never partially mutate state.

The server broadcasts authoritative `state_snapshot` messages at `30 Hz`. A manual LAN tuning pass may select `15 Hz`, but no other cadence is in scope without a new decision. Lifecycle and result events are sent immediately. Every snapshot includes an integer `tick` and monotonic `revision`; browser interpolation is display-only.

## Message envelope

All messages are JSON objects with:

```json
{
  "version": 1,
  "type": "message_type"
}
```

`request_id` is required on client lobby/setup requests and is echoed by responses where useful. `seq` is required on `move_start`, `move_stop`, and `attack`. `direction` is required on movement and is either `left` or `right`.

## Client to server messages

| Type | Required fields | Authority and behavior |
|---|---|---|
| `hello` | `version`, `type`, `request_id`, `client_name` | Must be first. Establishes protocol compatibility; the definitive lobby identity is returned after `create_lobby` or `join_lobby`. |
| `create_lobby` | `version`, `type`, `request_id` | Creates the lobby and makes this connection host. |
| `join_lobby` | `version`, `type`, `request_id`, `join_code` | Joins a six-character uppercase alphanumeric LAN lobby; maximum four players. |
| `ready` | `version`, `type`, `request_id`, `ready` | Changes only this player's readiness during setup. |
| `host_config` | `version`, `type`, `request_id`, `rounds`, `turn_seconds` | Host only; valid turn values are `30`, `45`, `60`, `120`; no mid-match changes. |
| `start_match` | `version`, `type`, `request_id` | Host only; valid setup/ready state required. |
| `move_start` | `version`, `type`, `seq`, `direction` | Active player intent; server holds the direction on fixed ticks. |
| `move_stop` | `version`, `type`, `seq`, `direction` | Active player intent; server releases the direction. |
| `attack` | `version`, `type`, `seq` | Active player intent; at most one accepted attack per turn. |
| `leave` | `version`, `type`, `request_id` | Voluntary disconnect; handled using the connection policy below. |

## Server to client messages

| Type | Required fields | Purpose |
|---|---|---|
| `welcome` | `version`, `type`, `request_id`, `connection_id`, `player_id`, `is_host` | Definitive identity for the created or joined lobby; sent once per successful lobby action. |
| `lobby_state` | `version`, `type`, `players`, `host_id`, `join_code`, `phase`, `connected_count`, `max_players`, `configured_rounds`, `turn_seconds`, `all_ready`, `can_start` | Authoritative lobby/setup roster, configuration, readiness, capacity, and start status. |
| `turn_started` | `version`, `type`, `tick`, `revision`, `active_player_id`, `end_tick` | Immediate turn lifecycle event. |
| `state_snapshot` | `version`, `type`, `tick`, `revision`, `phase`, `round_number`, `active_player_id`, `remaining_turn_ticks`, `players`, `balls` | Authoritative display state at 30 Hz. |
| `command_rejected` | `version`, `type`, `code`, `message` | Non-mutating command rejection; may echo `request_id` or `seq`. |
| `round_result` | `version`, `type`, `round_number`, `winner_ids`, `scores` | Frozen round result, including all tied winners. |
| `match_result` | `version`, `type`, `winner_ids`, `result`, `round_wins` | Final winner or `tie`; no result persistence after return to setup. |
| `host_disconnected` | `version`, `type`, `reason` | Terminal event for remaining clients. |
| `error` | `version`, `type`, `code`, `message` | Non-command protocol/session error. |

## Rejection codes

The initial code set is:

`MALFORMED`, `TOO_LARGE`, `BAD_VERSION`, `HELLO_REQUIRED`, `BAD_PHASE`, `NOT_HOST`, `OUT_OF_TURN`, `TURN_EXPIRED`, `DUPLICATE_SEQ`, `INVALID_VALUE`, `CAPACITY_FULL`, `LATE_JOIN`, `UNKNOWN_REQUEST`, and `HOST_DISCONNECTED`.

Shape and size validation precede authority checks. No rejected message changes phase, transforms, scores, damage, timers, readiness, or connection ownership.

## Disconnect and lifecycle policy

- Host disconnect in lobby, setup, or match play transitions the authoritative session to `HOST_DISCONNECTED`, sends the terminal event, accepts no further commands, and closes remaining connections after the event is flushed.
- A non-host disconnect stops accepting commands immediately. If that player is active, the current server turn completes, then the player is removed from future scheduling. Outside an active turn, removal is immediate.
- If no active players remain, the server emits an abandoned-session terminal result.
- There is no reconnect slot, host migration, spectator slot, public lobby, or persistence in v1.

## LAN hosting and packaging

- The host runs the authoritative Python 3.12 process and may occupy one of four player seats.
- Bind default: `0.0.0.0:8765`; fallback ports: `8766` through `8775`.
- The server creates a six-character uppercase alphanumeric join code.
- The host shares `http://<lan-ip>:<port>/`; the browser derives `ws://<same-host>:<port>/ws`.
- The same Python process serves `client/` static files and the WebSocket endpoint where practical.
- Origin checks allow the exact configured LAN HTTP origin and approved loopback development origins. TLS/`wss://`, public deployment, NAT traversal, and authentication are deferred.

## Determinism and authority boundary

The server owns all numeric calculations and mutable simulation state. It uses integer ticks, monotonic revisions, stable IDs, centralized configuration, logical coordinates, deterministic receive/sequence ordering, and explicit contact identities. The browser receives snapshots and lifecycle events only; it never sends interpolated positions or local collision outcomes. Replays and state hashes are not required for v1, but command logs should retain `tick`, receive ordinal, connection/player ID, client sequence, type, and accepted/rejected code.
