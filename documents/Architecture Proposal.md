# Dodgeball! Architecture Proposal — v1 Handoff

Status: Approved architecture handoff with provisional implementation defaults. No game code is implemented by this document.

## 1. Authority and scope

This handoff follows the authoritative answers in `documents/User Q&A.md` and the compatible parts of `documents/Engineer Proposal.md`.

V1 targets Chrome on desktop, with a Python 3.12 authoritative server and a JavaScript browser client. The first network milestone is LAN-based, with an explicit boundary that can later support online hosting. The game supports up to four active players, with no spectators, reconnect slots, or host migration.

The browser renders the game. Python owns simulation and game state. Pygame must not own the browser display or transmit rendered frames. The simulation core must be runnable without a Pygame window, DOM, or network connection.

## 2. Approved system boundary

```
Browser keyboard/UI input
        -> validated JSON commands over WebSocket
Python server: lobby + authoritative simulation + transport
        -> snapshots and lifecycle events
Browser JavaScript: canvas renderer + HUD + screens
```

The browser may collect keyboard state, draw snapshots, interpolate display-only motion, and display errors. It may not submit positions, velocities, damage, scores, collision results, turn changes, or winner decisions.

The Python server owns player and dodgeball transforms, boundaries, hitboxes, collision resolution, damage, scores, attack limits, turn order, timers, rounds, win conditions, host authority, and disconnect handling.

Pygame is optional inside the simulation implementation. If used, it is a server-side utility or local test harness; it is not a rendering bridge. The preferred dependency boundary is a simulation package that can be unit-tested independently of Pygame.

## 3. Proposed module layout

```
server/
  main.py              # network-server entry point
  lobby.py             # lobby creation, join codes, admission, host permissions
  transport.py         # WebSocket lifecycle, decode/encode, message validation

simulation/
  config.py            # centralized limits, tick rate, stage and turn presets
  entities.py          # player, dodgeball, stage, attack value objects
  state.py             # authoritative match state and serializable state contracts
  phases.py            # lifecycle enum and legal transition table
  commands.py          # intent types and command validation results
  rules.py             # movement, attacks, damage, scoring, transition rules
  physics.py           # fixed-step movement, bounds, hitboxes, collision ordering
  clock.py             # fixed 60 Hz stepping and tick accounting

client/
  index.html           # lobby, setup, canvas, HUD, result screens
  styles.css
  client.js            # WebSocket connection, keyboard input, screen flow
  renderer.js          # canvas drawing from snapshots only
  hud.js               # timer, round, damage/score lines, result display

shared/
  protocol.md          # message contract and examples
  protocol_schema.json # machine-readable message/schema definitions, if agreed

tests/
  unit/                # deterministic simulation and validation tests
```

Entry points are `server/main.py` for the LAN server and `client/index.html` for the browser. A local simulation entry point may be provided for deterministic tests, but it is not a second rules implementation.

Responsibilities must not cross module boundaries: transport decodes and validates shape; commands represent intent; rules and physics mutate authoritative state; rendering consumes snapshots and does not mutate simulation objects.

## 4. Authoritative state contracts

The conceptual state objects are:

- `Player`: stable player ID, assigned color, connection status, position, velocity, damage, current score, ready state, and attack-used flag.
- `Dodgeball`: stable ball ID, position, velocity, hit value, and contact-sequence state needed for the first three valid hits.
- `Stage`: fixed logical width and height plus boundary policy.
- `Turn`: active player, ordered player list, start tick, end tick, and completed/inactive status.
- `Round`: round number, turn order, frozen round result, and accumulated match totals.
- `Match`: configuration, lifecycle phase, players, balls, rounds, host ID, current tick, and terminal result.
- `Command`: connection/player identity, client sequence, command type, and only command-specific intent fields.
- `Snapshot`: server tick, revision, lifecycle phase, active player, remaining time, transforms, damage/scores, round number, and result fields where applicable.

Only the simulation owns mutable authoritative objects. Transport receives a command, validates it against connection, phase, player, sequence, and rules, then passes an accepted intent to the simulation. The client receives serialized snapshots and events.

Provisional dimensions, entity sizes, movement values, collision rules, and scoring interpretation are defined in `documents/Implementation Decisions.md`. They are centralized in configuration and remain deliberately tunable during manual testing; tuning does not require a new approval round unless it changes the approved game behavior.

## 5. State machine and game flow

The recommended lifecycle is:

```
LOBBY
  -> SETUP
  -> TURN_START
  -> ACTIVE_TURN
  -> TURN_RESULT
  -> (TURN_START for next player | ROUND_RESULT)
  -> (TURN_START for next round | MATCH_RESULT)

Any active phase --host disconnect--> HOST_DISCONNECTED -> CLOSED
```

### Lobby and setup

1. Host creates a lobby and receives a short join code.
2. Other players join with that code; admission stops at four active players.
3. The server assigns stable IDs and colors.
4. The host selects round count and one turn preset: 30, 45, 60, or 120 seconds.
5. Players can mark ready. The host alone can start the match.
6. The server rejects non-host configuration/start actions, invalid configuration, late joins, and starts from the wrong phase.

### Turns and rounds

Each round gives every currently active player one turn in a fixed server-assigned order. The active player may move continuously left or right and may perform at most one attack. The server timer ends the turn. A no-input player still consumes the turn and advances at timeout; “inactive” must not be treated as an implicit disconnect.

The approved Q&A says a disconnected game should continue, while QA explicitly requires a host disconnect to end the game. This handoff resolves that distinction as follows: a non-host disconnect finishes the current server turn if that player is active, then removes the player from future scheduling; outside an active turn the player is removed immediately. Host disconnect is terminal and is not recoverable in v1.

Round results freeze before the next round. Each round starts every player at zero round score. Score determines the round winner; for a multi-round match, the match winner is the player with the most won rounds. Ties display all tied winners. No scores or results persist after the match, and the result screen provides a return-to-start-menu action.

## 6. Deterministic 60 Hz simulation

The server advances a fixed simulation tick of exactly 1/60 second. Wall-clock time only determines how many fixed steps are due; it never becomes a gameplay delta. Client frame rate and client timestamps are non-authoritative.

The proposed per-tick ordering is:

1. Drain commands accepted before the tick boundary.
2. Order them deterministically by server receive sequence, then client sequence where applicable.
3. Validate phase, player turn, attack availability, and stale/duplicate status.
4. Apply held movement intent and accepted attack intent.
5. Advance all moving bodies using the fixed tick duration.
6. Resolve stage-boundary bounces.
7. Resolve player, dodgeball, attack, and other hitboxes in the approved stable priority order.
8. Emit one damage/knockback/score event per approved contact identity and tick.
9. Advance timers and detect turn timeout.
10. Resolve turn, round, match, and terminal transitions.
11. Increment tick/revision and publish a snapshot or immediate lifecycle event.

The exact numeric representation, collision priority, contact identity, and command boundary are defined provisionally in `documents/Implementation Decisions.md`. Unit tests must verify identical initial state plus identical command sequence produces identical state and results, including grazing, overlap, high-speed, simultaneous, boundary, and invalid-dimension cases.

## 7. Browser lobby, HUD, and rendering flow

The browser screens are:

- Lobby: create a server/code or enter a code to join.
- Setup: show players/readiness; host selects rounds and turn duration; host starts.
- Gameplay: draw the fixed logical stage and authoritative entities.
- HUD: color-matched player lines with damage/score number below, centered countdown timer, and round number in the top-left.
- Result: simple winner-color display, or the approved tie/terminal reason.

Keyboard input is A/D or left/right arrows for movement and E for attack. Input is converted to explicit commands. The renderer uses a fixed logical coordinate system; canvas/CSS scaling changes display size only and never changes simulation coordinates or hitboxes.

## 8. Networking agreement items — Architect position

These are explicit Architect positions for discussion with the Engineer. They are not presented as unanimous agreement. Items marked “User approval required” remain implementation gates.

### 8.1 Transport/library

**Architect position:** use browser-native WebSockets carrying UTF-8 JSON, with Python's focused `websockets` asyncio package for v1. Keep the server small; use a separate static-file serving approach if that is simpler than coupling HTTP and WebSocket concerns.

`aiohttp` remains a valid alternative if the Engineer demonstrates that one-process static serving materially reduces complexity. Do not use WebRTC, polling, or Socket.IO for v1 without a new requirement.

**Status:** Approved for v1; Engineer implements the selected package behind the transport interface.

### 8.2 Hosting topology

**Architect position:** the host runs the authoritative Python server locally on the LAN; the host browser may also be one of the four players. The server binds to an explicitly configured LAN address and port. The join code identifies the lobby; the host must share the reachable LAN URL/address separately unless the implementation supplies a clearly approved discovery mechanism.

Public hosting, TLS, NAT traversal, authentication, persistence, and host migration are out of scope for v1.

**Status:** Resolved provisionally in `documents/Implementation Decisions.md`; Engineer may tune only for local machine conflicts.

### 8.3 Protocol schema

**Architect position:** versioned JSON messages with a required `type`, protocol version, connection/player identity where applicable, and client sequence number for gameplay commands. Recommended messages include `hello`, `create_lobby`, `join_lobby`, `ready`, `host_config`, `start_match`, `move_start`, `move_stop`, `attack`, `state_snapshot`, `command_rejected`, `round_result`, `match_result`, and `host_disconnected`.

Malformed, oversized, stale, duplicate, out-of-state, out-of-turn, and over-capacity messages are rejected without partial mutation. The protocol should use a consistent error code and human-readable message.

**Status:** Resolved provisionally in `documents/Implementation Decisions.md`; Engineer must keep the schema versioned and reject invalid messages without mutating state.

### 8.4 Snapshot policy

**Architect position:** simulate at 60 Hz and broadcast authoritative snapshots at 30 Hz for the LAN milestone, with immediate lifecycle/result events. Every snapshot includes server tick and monotonic revision. The browser may interpolate display-only motion but must render authoritative corrections and never send interpolated positions back.

If manual testing shows that 15 Hz is preferable on the LAN, the Engineer may tune the cadence to 15 Hz without changing authority or protocol shape.

**Status:** Resolved at 30 Hz, with 15 Hz permitted as a manual-tuning alternative.

### 8.5 Command semantics

**Architect position:** represent continuous movement with `move_start(direction)` and `move_stop(direction)` plus a client sequence number; `attack` is a discrete intent. This is preferable to per-tick movement messages because it reduces traffic while the server remains authoritative. The server applies accepted held intent on fixed ticks.

Commands received before a tick boundary are ordered deterministically. Commands at the turn end are accepted only if they arrive before the server's authoritative boundary. Repeated attacks, stale commands, and commands from non-active players are rejected or ignored according to one documented rule, with no state mutation.

**Status:** Resolved provisionally in `documents/Implementation Decisions.md`; all rejected commands are non-mutating and produce structured feedback when a client can receive it.

### 8.6 Connection policy

**Architect position:** admit at most four active players and no spectators or reconnection slots. A host disconnect immediately transitions the match to `HOST_DISCONNECTED`, broadcasts the terminal result, and closes remaining game connections. There is no host migration or reconnect behavior in v1.

For a non-host disconnect, finish the current server turn if the disconnected player is active, then remove that player from future turn scheduling. If no turn is active, remove the player immediately. A disconnected player cannot receive further commands.

**Status:** Resolved for v1; reconnect and host migration remain out of scope.

### 8.7 Browser/server packaging

**Architect position:** serve the browser client from the same Python host where practical, while keeping static asset serving separate from simulation and transport responsibilities. During LAN development, Chrome loads the host's HTTP URL and connects to the matching `ws://` endpoint. CORS/origin checks should allow the configured LAN origin only; `wss://` is deferred with public deployment.

**Status:** Resolved provisionally as same-process HTTP plus WebSocket serving, with LAN-origin checks described in `documents/Implementation Decisions.md`.

### 8.8 Determinism boundary

**Architect position:** share protocol names, field definitions, logical coordinate units, and configuration identifiers—not mutable simulation state or Python implementation objects—with the browser. The server owns numeric calculations. Use a fixed tick integer, monotonic state revision, stable entity IDs, deterministic command ordering, and explicit collision/contact identities. Replays and state hashes are not required for v1, but deterministic command logs should be easy to add for debugging.

**Status:** Resolved provisionally in `documents/Implementation Decisions.md`; replay and state hashes remain out of scope.

## 9. Host-disconnect terminal behavior

When the host connection closes in any active or setup phase:

1. The server marks the match/lobby terminal as `HOST_DISCONNECTED`.
2. It sends `host_disconnected` or the agreed equivalent terminal event to remaining clients.
3. No further commands or simulation transitions are accepted.
4. The browser shows a simple ended screen and returns to the lobby entry flow.
5. The server closes the remaining connections after the terminal message is flushed.

This behavior must be covered by the LAN stopping point. Reconnection and host migration are explicitly not implemented.

## 10. Readability and implementation gates

Use Python 3.12, PEP 8, type hints, descriptive names, and concise docstrings on every public class and function. Example:

```python
def advance_turn(self, tick: int) -> None:
    """Advance the active turn when its timer expires."""
```

Document non-obvious rules next to their owning code, especially repeated-hit damage and collision ordering. Do not duplicate rules in JavaScript.

The Engineer's stopping points are compatible with this handoff. SP-0 is satisfied by the approved checklist and this decision record. Physics values remain subject to manual tuning at SP-3/SP-4, and scoring interpretation must be explicitly exercised at SP-5.

Required gates:

1. Engineer reviews this architecture and the implementation decision record.
2. Engineer implements only through the approved stopping points.
3. Engineer pauses for manual approval at each gate; tuning feedback is recorded in the stopping-point document.

## 11. Implementation status

The user-approved architecture and networking checklist authorize implementation. Remaining values are engineering defaults, not approval blockers. The Engineer must surface any deviation from the interface expectations or approved scope at the relevant stopping point.

