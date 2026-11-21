# Engineer Proposal — v1

Status: Draft for user and Architect approval. No game code is implemented by this proposal.

## 1. Recommended v1 boundary

Use a Python 3.12 authoritative simulation core and a browser-only renderer. Pygame may be used for local development or a local test harness, but it must not own browser rendering. The simulation must be usable without Pygame, transport, or DOM code.

Recommended conceptual boundaries:

- `config`: centralized player limit (4), tick rate (60 Hz), stage dimensions, turn presets, and round limits.
- `state`: player, ball, turn, round, match, collision event, score, and lifecycle state.
- `rules`: command validation, movement, collision ordering, attacks, damage, knockback, scoring, and transitions.
- `transport`: connection lifecycle, JSON message validation, snapshot delivery, and disconnect handling.
- `client`: keyboard input, canvas rendering, HUD, lobby/setup screens, and display-only interpolation if needed.
- `main`: local simulation entry point and network-server entry point.

The client sends intents only. The server owns positions, velocities, collision results, damage, scores, turn order, timers, rounds, and win conditions.

## 2. Deterministic simulation contract

The simulation advances exactly 60 fixed ticks per second. A tick is an integer step; elapsed wall-clock time is used only to decide how many fixed steps are due. No client timestamp, frame rate, or client position is authoritative.

Recommended tick ordering:

1. Drain and validate commands received before the tick boundary, in a defined sequence-number order.
2. Apply held left/right intent to the active player's velocity or position using fixed-point or consistently quantized numeric values.
3. Advance all moving bodies using the fixed tick duration.
4. Resolve stage-boundary bounces and player/ball/attack hitboxes in a documented, stable order.
5. Emit damage, knockback, score, and duplicate-contact events once per tick/contact rule.
6. Resolve turn timeout, round completion, and match completion.
7. Publish a snapshot with a monotonically increasing tick and state revision.

The Architect must approve the coordinate units, stage dimensions, player/ball radii, maximum speed, acceleration/deceleration, bounce coefficients, collision priority, and numeric representation before implementation. The browser uses the same coordinate space and scales the canvas for display only.

## 3. Controls and turn behavior

- Movement is continuous left/right movement. A/D and left/right arrows map to the same two intents.
- The browser should send explicit `move_start(direction)`, `move_stop(direction)`, and `attack` intents, each with a client sequence number. The server may also accept a normalized `move(direction)` state command if the Architect prefers it, but the contract must be one or the other.
- E produces at most one accepted attack during the player's current timed turn. Repeated E messages, stale messages, and attacks after the turn are rejected or ignored deterministically and cannot mutate state.
- The active player may move and attack during that player's turn. Other players' gameplay commands are rejected as out-of-turn.
- A round contains one turn for each connected active player, in a fixed server-assigned order. With four players there are at most four turns per round.
- Each turn uses the host-selected preset: 30, 45, 60, or 120 seconds. The server timer, not the browser countdown, ends the turn.
- A player who sends no movement or attack still consumes their turn and is passed over at timeout. “Inactive” must not silently mean disconnected; the Architect must approve the exact ready/timeout wording in the state machine.

## 4. Damage, knockback, and bouncing ball

Recommend treating `damage` and `round_points` as separate named fields even though the requirements relate them. Damage is the accumulated knockback driver. Points are the victim's remaining non-negative round score. This avoids making knockback depend on a presentation value or allowing score underflow.

For a bouncing dodgeball's first three valid player contacts in the relevant contact sequence:

- first hit: 100% of the ball's hit value;
- second hit: 50%;
- third hit: 25%;
- later hits: 0 damage.

Damage is deducted from the player hit, clamped at zero. Knockback magnitude increases from accumulated damage according to an Architect-approved formula. A hitbox is the ball's circular hit shape expanded by an Architect-approved margin. Multiple players in the hitbox may be affected, but each contact must have a defined event identity so the same overlap cannot deduct repeatedly every tick unless the approved contact policy allows it.

Players and balls remain inside the boxed stage. Boundary contacts reflect velocity rather than allowing an exit. The collision contract must define grazing, overlap, high-speed tunneling prevention, simultaneous contacts, invalid dimensions, and the order of multiple same-tick events.

## 5. Round and match scoring

At round end, freeze the authoritative round results, record each player's round score and accumulated damage, then advance to the next configured round or match-result state. After the final round, display the winning color.

Required unresolved scoring decision: the Q&A does not define each player's starting points, whether “score” means remaining points, points lost, or a separate win total, or how round totals accumulate across rounds. Recommended default for approval: start every round with an explicitly configured equal pool; deduct victim points as specified; rank by total remaining points across rounds, with a tie state when totals match. Do not implement this default until approved.

Required unresolved tie decision: recommended v1 behavior is a declared tie shown on the match-result screen, with no automatic sudden-death round. Rematch behavior can be a return to setup without changing the prior result.

## 6. Four-player turn flow and lifecycle

Recommended state machine:

`LOBBY -> SETUP -> TURN_START -> ACTIVE_TURN -> TURN_RESULT -> ROUND_RESULT -> TURN_START ... -> MATCH_RESULT`

The host creates a server/code, chooses round count and turn preset, and starts the match. The server validates host-only actions. The player cap is four; no spectators or reconnection slots are included in v1.

Recommended v1 disconnect rule: if the host disconnects, broadcast a terminal `host_disconnected` result and end the game for all clients. This is required by the QA wording and avoids reconnection complexity. A non-host disconnect policy remains an approval gate: recommended behavior is to mark that seat inactive, finish the current simulation safely, and exclude the seat from future turn scheduling; the exact policy must be agreed before networking.

## 7. LAN-first networking recommendation

Use browser-native WebSocket connections carrying UTF-8 JSON messages to a Python server. For the Python implementation, prefer the focused `websockets` asyncio package for the LAN milestone. It directly provides a WebSocket server and connection handler, while the browser has a standard WebSocket API. Aiohttp is a credible alternative when serving static files and WebSockets from one Python process is a priority. FastAPI/Starlette is reasonable if HTTP APIs, validation models, and future service endpoints are expected, but is more framework than this four-player LAN milestone needs.

Do not use WebRTC data channels for v1: they add signaling and peer-connection complexity that is unnecessary for four clients and conflicts with the required authoritative client-server model. Do not use polling or Socket.IO unless a later requirement needs fallback transports or its protocol overhead is explicitly accepted.

LAN-first means the server binds to the LAN interface, advertises a host address/code through the lobby, and uses `ws://` for local development. Public online play, TLS/`wss://`, NAT traversal, authentication, persistence, and reconnection are outside v1 unless separately approved. The protocol should reserve a version field so these can be added without changing simulation rules.

Proposed message categories:

- client to server: `hello`, `ready`, `host_config`, `start_match`, `move_start`, `move_stop`, `attack`, `leave`;
- server to client: `welcome`, `lobby_state`, `state_snapshot`, `command_rejected`, `turn_started`, `round_result`, `match_result`, `error`, `host_disconnected`.

Every gameplay command should include protocol version, player/session identifier, client sequence number, command type, and only the fields allowed for that command. Snapshots should include server tick, revision, lifecycle state, active player, remaining turn time, player transforms, ball transforms, damage, visible scores, round number, and winner/result fields when applicable. The server must reject malformed, oversized, out-of-state, out-of-turn, duplicate, and stale commands without applying partial changes.

Snapshots are periodic and authoritative. Recommend sending at 20–30 Hz for the LAN milestone while simulating at 60 Hz, unless manual testing shows that 60 snapshots is simpler and still stable. The browser renders the latest snapshot and may interpolate display-only motion; it never feeds rendered positions back to the server.

## 8. Exactly what must be agreed with the Architect

The networking proposal cannot be finalized until Architect and Engineer unanimously approve all of the following:

1. Transport/library: `websockets` versus `aiohttp` versus another option, and whether one process serves static files.
2. Hosting topology: host runs the authoritative Python server locally; whether the host browser is also a player; bind address, port selection, and how the join code maps to a LAN address.
3. Protocol schema: message names, required fields, protocol versioning, JSON validation approach, maximum message size, sequence-number rules, and rejection/error format.
4. Snapshot policy: simulation at 60 Hz versus snapshot broadcast rate, snapshot contents, interpolation policy, and whether event messages are separate from snapshots.
5. Command semantics: held movement represented by start/stop or per-tick direction state; ordering of simultaneous commands; attack acceptance boundary at turn start/end; duplicate and stale command handling.
6. Connection policy: four-player admission, whether a seat is reserved after a non-host disconnect, whether a disconnected non-host is removed immediately or after the current turn, and the exact host-disconnect terminal flow.
7. Browser/server packaging: static asset serving, CORS/origin policy for LAN, `ws` versus `wss`, and how Chrome loads the page when the server is on another machine.
8. Determinism boundary: shared constants/schema, numeric representation, tick identifiers, collision event identity, and whether replays or state hashes are required for debugging.

Once these eight items are recorded in the Architect handoff, the Engineer can write the networking proposal for user approval. Until then, networking implementation is blocked by the project plan—not by a missing coding detail.

## 9. Approval gates

- Gate A — approve this v1 scope, simulation assumptions, unresolved scoring decisions, and stopping points.
- Gate B — Architect–Engineer unanimous agreement on all eight networking items above.
- Gate C — user approval of the final networking proposal before any networking code.
- Gate D — manual approval after local deterministic controls/turns, physics, attacks/scoring, and match flow.
- Gate E — manual LAN test approval with up to four clients, including host disconnect behavior.

