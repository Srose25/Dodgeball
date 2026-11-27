# Dodgeball! Networking Proposal — v1

**Status: Approved v1 networking handoff; SP-6 design gate finalized.**

No networking or game code is implemented by this document.

## 1. Consensus scope

The Architect and Engineer agree on a LAN-first, authoritative client-server design for Chrome desktop:

- Python 3.12 owns the lobby, simulation, validation, timers, collisions, damage, scores, turns, rounds, and match results.
- The browser owns keyboard/UI input and canvas/HUD rendering only.
- The browser sends intents; it never submits positions, velocities, scores, damage, collision results, or winner decisions.
- The game supports at most four active players. There are no spectators, reconnect slots, host migration, or public-lobby requirements in v1.
- Pygame is optional for a local test harness and is not a browser-rendering or frame-transmission layer.

## 2. Eight networking decisions

### 2.1 Transport and library — agreed

Use browser-native WebSockets carrying UTF-8 JSON and Python's focused `websockets` asyncio package for the v1 LAN server.

`aiohttp` is rejected for v1 as the default because its combined HTTP/WebSocket stack is not needed to prove the four-player authoritative milestone. It remains an acceptable change proposal if serving static assets and WebSockets in one process is demonstrated to materially reduce implementation complexity. WebRTC, polling, and Socket.IO are out of scope unless requirements change.

### 2.2 Hosting topology — resolved provisionally

The host runs the authoritative Python server on the LAN and may also occupy one player seat. The default bind is `0.0.0.0` on TCP port `8765`; if unavailable, the server selects the next available port in `8766`–`8775` and reports it. A six-character uppercase alphanumeric join code identifies the lobby. The host shares `http://<lan-ip>:<port>/`; the browser derives `ws://<same-host>:<port>/ws`.

Public hosting, TLS/`wss://`, NAT traversal, authentication, persistence, and host migration are out of scope for v1.

### 2.3 Protocol schema — implementation contract

Messages are versioned JSON objects. Each message has a required protocol version and `type`. Gameplay commands include connection/player identity where applicable and a client sequence number. The server validates message shape and game authority before passing an accepted intent to the simulation.

Proposed client-to-server messages:

- `hello`
- `create_lobby`
- `join_lobby`
- `ready`
- `host_config`
- `start_match`
- `move_start`
- `move_stop`
- `attack`
- `leave`

Proposed server-to-client messages:

- `welcome`
- `lobby_state`
- `turn_started`
- `state_snapshot`
- `command_rejected`
- `round_result`
- `match_result`
- `host_disconnected`
- `error`

Malformed, oversized, stale, duplicate, out-of-state, out-of-turn, and over-capacity messages must be rejected without partial mutation. A consistent machine-readable error code plus human-readable message is required.

`hello` is mandatory before lobby actions. Messages require `version: 1`, `type`, and a request ID for client-originated lobby/setup commands; gameplay commands additionally require a strictly increasing per-connection `seq`. Maximum decoded message size is 16 KiB. Validate JSON shape and value ranges before authority checks, reject unknown required fields only where unsafe, and use codes such as `MALFORMED`, `TOO_LARGE`, `BAD_PHASE`, `NOT_HOST`, `OUT_OF_TURN`, `DUPLICATE_SEQ`, and `CAPACITY_FULL`. Rejections never partially mutate state.

### 2.4 Snapshot policy — resolved at 30 Hz

The simulation runs at a fixed 60 Hz. The server broadcasts authoritative snapshots at 30 Hz and emits lifecycle/result events immediately. If manual LAN testing shows 30 Hz is unnecessarily heavy, 15 Hz is the only permitted v1 tuning alternative. Every snapshot includes a server tick and monotonic state revision.

Minimum snapshot contents:

- lifecycle phase;
- active player and remaining turn time;
- round number;
- stable entity IDs and logical-coordinate transforms;
- velocities if needed for display correction;
- damage and visible scores;
- result/winner fields when applicable.

The browser may interpolate display-only motion between snapshots, but must render authoritative corrections and must never send interpolated positions back to the server. Raising snapshot cadence to 60 Hz is a possible later simplification only if manual testing demonstrates a clear benefit and the user approves the scope change.

### 2.5 Command semantics — resolved implementation contract

Continuous movement uses `move_start(direction)` and `move_stop(direction)` with client sequence numbers. `attack` is a discrete intent. The server applies held movement state on fixed simulation ticks, avoiding per-tick browser traffic.

Commands accepted before a tick boundary are ordered deterministically by server receive sequence, then client sequence where applicable. The authoritative server decides whether a command arrived before the turn boundary. E may produce at most one accepted attack per active turn.

Repeated, stale, duplicate, malformed, out-of-state, and out-of-turn commands are rejected with `command_rejected` when the connection is still usable; they never mutate state. A command is eligible only if received and validated before the tick's command-drain cutoff. Commands in the same tick are ordered by server receive ordinal, then client `seq`. Duplicate or lower `seq` values are rejected. After a turn boundary, late commands are rejected as `TURN_EXPIRED`.

### 2.6 Connection policy — resolved

Admission stops at four active players. There are no spectators, reconnect slots, or host migration in v1.

If the host disconnects during lobby, setup, or match play, the server transitions to `HOST_DISCONNECTED`, sends the terminal event to remaining clients, accepts no further commands, shows an ended screen, and closes the remaining connections after the event is flushed.

For a non-host disconnect, finish the current server turn if that player is active, but stop accepting commands from that connection immediately. At turn completion, remove the player from future scheduling. If no turn is active, remove them immediately. If the player was the last active player, end the match as an abandoned session with a structured terminal event.

### 2.7 Browser/server packaging — resolved provisionally

Keep static-file serving separate from simulation and transport responsibilities. For the LAN milestone, prefer serving the browser client from the same Python host so Chrome loads the host's HTTP URL and connects to the matching `ws://` endpoint. A separate static server is allowed only if it does not change the LAN join instructions or create an avoidable origin problem.

The Python host serves `client/` static files and the WebSocket endpoint from one process. The server allows the exact origin derived from its own HTTP URL and same-origin requests; loopback origins may be allowed for local development. `wss://`, public deployment security, and authentication are deferred.

The final implementation decision must specify whether the selected Python process serves static files, the exact origin policy, and how the browser derives the WebSocket endpoint from the host URL.

### 2.8 Determinism boundary — agreed

The server is the sole owner of numeric gameplay calculations and mutable simulation state. The browser shares protocol names, field definitions, logical coordinate units, and configuration identifiers; it does not receive mutable Python objects or become a second rules implementation.

The simulation uses:

- an integer fixed-tick counter at 60 Hz;
- monotonic snapshot/state revisions;
- stable player and entity IDs;
- deterministic server-receive/client-sequence command ordering;
- explicit collision/contact identities;
- centralized configuration;
- fixed logical coordinates independent of canvas size.

Replays and state hashes are not required for v1. Deterministic command logs should be structured so replay/debugging can be added later.

The exact numeric representation, collision priority, contact identity format, and command-log fields are recorded in `documents/Implementation Decisions.md` and are implementation expectations for the Engineer.

## 3. Implementation detail record

The remaining implementation details are resolved provisionally in `documents/Implementation Decisions.md`. Physics constants are intentionally tunable during manual testing and do not change the authority or protocol contract.

## 4. Implementation gates

1. The Engineer reviews this approved handoff and the implementation detail record.
2. Networking proceeds only at SP-7, after local simulation behavior is stable.
3. Implementation must stop for manual LAN testing with up to four clients, including host disconnect behavior.

## 5. Conflict check

No approval blocker remains. The Architect and Engineer may tune provisional physics values during manual testing, while preserving the server authority, message contract, and stopping-point workflow.

## 6. SP-6 artifact record

The implementation-ready shared contract is finalized in:

- `shared/protocol.md` — normative message, authority, lifecycle, disconnect, LAN, snapshot, and determinism rules.
- `shared/protocol_schema.json` — machine-readable v1 message shapes and required fields.
- `shared/protocol.py` — transport-free envelope checks for version, mandatory first `hello`, 16 KiB size, and strictly increasing gameplay sequences.

SP-6 intentionally contains no WebSocket transport, HTTP serving, browser networking, or connection lifecycle implementation. Those begin only at SP-7 after explicit user approval.

