# Architect–Engineer Approval Q&A

This checklist consolidates the remaining architecture and engineering decisions after review of the approved `User Q&A.md`, `Architecture Proposal.md`, `Engineer Proposal.md`, and `Networking Proposal.md`.

For each row, enter **yes** or **no** in the answer column. Rows marked **Details required** also need the requested value or rule in the final column before implementation can begin.

## Architecture and scope

| [y/n] Question | Yes / no answer | Further context | Required follow-up / details |
|---|---|---|---|
| Do you approve the system boundary where Python owns the lobby, transport, simulation, and authoritative state, while JavaScript owns input, rendering, HUD, and screens? | yes | The browser must not submit positions, scores, damage, collision results, or winner decisions. | Record approval in `Architecture Proposal.md`. |
| Do you approve the proposed module layout: `server/`, `simulation/`, `client/`, `shared/`, and `tests/`? | yes | Responsibilities remain separated between transport, rules/physics, state, and rendering. | Note any module or filename changes. |
| Do you approve the proposed state objects: `Player`, `Dodgeball`, `Stage`, `Turn`, `Round`, `Match`, `Command`, and `Snapshot`? | yes | These define the initial simulation and protocol contracts. | Note any fields or objects that must be added or removed. |
| Do you approve a fixed logical coordinate system whose display size may scale in Chrome without changing gameplay coordinates or hitboxes? | yes | Canvas/CSS scaling and interpolation are display-only. | **Details required:** logical width, logical height, coordinate units, and scaling rule. |
| Do you approve a maximum of four active players with no spectators, reconnect slots, host migration, or public lobbies in v1? | yes | Online hosting, reconnect support, and public matchmaking remain later-scope work. | Record any scope exception. |
| Do you approve Python 3.12, PEP 8, type hints, concise public docstrings, and comments for non-obvious rules? | yes | Example: `"""Advance the active turn when its timer expires."""` | Note any style or documentation exception. |

## Simulation and gameplay rules

| [y/n] Question | Yes / no answer | Further context | Required follow-up / details |
|---|---|---|---|
| Do you approve a Python-authoritative simulation running at exactly 60 fixed ticks per second? | yes | Client frame rate, timestamps, and positions are never authoritative. | Record approval in the simulation contract. |
| Do you approve the proposed tick order: commands, movement, body advancement, boundary/collision resolution, damage/knockback/scoring, timers/transitions, then snapshots? | yes | The order must be deterministic for identical inputs and initial state. | **Details required:** final collision priority and simultaneous-contact order. |
| Do you approve continuous movement using `move_start(direction)` and `move_stop(direction)` intents? | yes | A/D and arrow keys map to left/right; the server maintains held movement state. | **Details required:** acceleration, deceleration, maximum speed, and opposing-input behavior. |
| Do you approve one discrete `attack` intent per active turn, with the server deciding whether it arrived before the authoritative turn boundary? | yes | Repeated, stale, out-of-turn, and late attacks cannot mutate state. | Record the boundary rule. |
| Do you approve the 30-, 45-, 60-, and 120-second turn presets? | yes | The server timer, not the browser countdown, ends a turn. | Record whether custom durations are excluded from v1. |
| Do you approve one turn per connected active player per round in a fixed server-assigned order? | yes | The order is stable for the round and there are at most four turns. | **Details required:** how the order is selected and when it is frozen. |
| Do you approve a player with no input consuming the full turn and advancing at timeout? | yes | “Inactive” must not silently mean disconnected. | **Details required:** ready-state and timeout wording/behavior. |
| Do you approve the expanded circular dodgeball hitbox affecting every valid target inside it? | yes | The user described the ball hitbox as slightly larger than the visible circular shape. | **Details required:** expansion margin and target-filtering rules. |
| Do you approve explicit collision/contact identities to prevent repeated damage from one unchanged overlap? | yes | Contact behavior must be deterministic across ticks and bounces. | **Details required:** contact-ID format and whether damage occurs on enter, once per bounce, once per tick, or another transition. |
| Do you approve the 100% / 50% / 25% / 0% damage sequence for the first four valid bouncing-ball contacts? | yes | The first three contacts cause damage; later contacts cause none. | **Details required:** base hit value and whether the sequence resets on bounce, turn, round, or another event. |
| Do you approve keeping accumulated damage separate from remaining round points? | yes | Damage drives knockback; points are clamped at zero. | Confirm whether the separation matches the intended scoring model. |
| Do you approve the proposed knockback rule that knockback increases with accumulated damage? | yes | The formula, force, duration, cap, and boundary interaction are still unspecified. | **Details required:** exact formula and constants. |
| Do you approve the proposed round and match scoring model? | yes | The current recommendation is an equal starting pool, point deductions during the round, and a documented cross-round ranking. | **Details required:** starting points, meaning of score, reset/persistence, aggregation, and winner calculation. |
| Do you approve declaring a tie rather than using automatic sudden death? | yes | Rematch behavior is separate from match-result display. | **Details required:** tie display and rematch/setup behavior. |

## Networking and browser/server design

| [y/n] Question | Yes / no answer | Further context | Required follow-up / details |
|---|---|---|---|
| Do you approve browser-native WebSockets carrying UTF-8 JSON with Python’s `websockets` asyncio package for v1? | yes | `aiohttp` is only an alternative if same-process static serving materially reduces complexity. | Record approval or alternative. |
| Do you approve the LAN topology where the host runs the authoritative server and may also occupy one player seat? | yes | The server binds to a configured LAN address/port; the host shares the reachable URL/address. | **Details required:** bind address, port-selection method, and join-code-to-address behavior. These details should be handled by the architect and the engineer. |
| Do you approve the versioned JSON message categories proposed in `Networking Proposal.md`? | yes | Messages include lobby, setup, movement, attack, snapshots, results, and errors. | **Details required:** exact required fields, `hello` requirement, validation mechanism, maximum message size, sequence rules, and error format. These details should be handled by the architect and the engineer. |
| Should malformed, oversized, stale, duplicate, out-of-state, and out-of-turn commands be rejected with `command_rejected` rather than silently ignored? | yes | Either behavior can be deterministic; rejection is recommended for debugging and user feedback. | Record one consistent behavior and error-code policy. |
| Do you approve ordering commands by server receive order, then client sequence number where applicable? | yes | Only commands received before the authoritative tick/turn boundary are eligible. | **Details required:** exact boundary and duplicate-sequence handling. The game needs to continue to run if there are these kinds of errors |
| Do you approve authoritative snapshots at 20–30 Hz while simulation runs at 60 Hz? | yes | Lifecycle and result events are sent immediately; snapshots include tick and monotonic revision. | **Details required:** exact snapshot rate and mandatory fields. |
| Do you approve display-only client interpolation between snapshots? | yes | Interpolated positions must never be sent back to the server. | Record correction behavior when a snapshot disagrees with interpolation. |
| Do you approve host disconnect ending the game for all clients with a terminal `host_disconnected` state? | yes | Remaining clients receive the event; no further commands are accepted; connections close after flushing it. | Record the client screen and server shutdown behavior. |
| Do you approve the recommended non-host disconnect rule: finish the active server turn when applicable, then remove that player from future scheduling; remove immediately outside a turn? | TBD | Reconnect is out of scope for v1. | Record the exact timing and whether the current turn can still receive commands. |
| Do you approve serving static browser files from the same Python host/process as the WebSocket server? | yes | A separate static server is allowed only if LAN join instructions and origin behavior remain simple. | Record the selected process topology. |
| Do you approve allowing only the configured LAN origin and deriving the WebSocket endpoint from the host URL? | yes | `ws://` is in scope; `wss://`, TLS, public hosting, NAT traversal, and authentication are deferred. | Record the origin allowlist and endpoint derivation rule. |

## Determinism and approval gates

| [y/n] Question | Yes / no answer | Further context | Required follow-up / details |
|---|---|---|---|
| Do you approve the determinism boundary: integer tick counter, monotonic revisions, stable IDs, centralized configuration, logical coordinates, deterministic command ordering, and explicit contact identities? | yes | The server remains the sole owner of numeric gameplay calculations and mutable simulation state. | **Details required:** numeric representation, collision priority, contact-ID format, and command-log fields. |
| Do you approve excluding replays and state hashes from v1 while retaining structured deterministic command logs? | yes | Replay/debugging enhancements may be added later without changing authority. | Record the minimum command-log fields. |
| Do you approve the updated `Engineer Stopping Points.md` and the rule that implementation cannot begin until blocking decisions are recorded? | yes | The Engineer must pause for manual approval after each stopping point. | Mark SP-0 through SP-8 as approved or identify changes. |
| Do you approve the sequence: Architect–Engineer agreement, explicit user approval, incremental implementation, then manual LAN testing with host-disconnect verification? | yes | Networking implementation remains blocked until the final proposal is approved. | Record the approval gate in the project record. |

## Items requiring more than yes/no

The following rows cannot become implementation-ready with a yes/no answer alone:

- Logical stage dimensions, coordinate units, and entity sizes.
- Movement, attack, bounce, collision, and knockback constants.
- Collision priority, simultaneous-contact behavior, and contact identity.
- Starting points, score meaning, persistence, aggregation, ties, and rematch behavior.
- Exact JSON fields, validation, maximum message size, sequence rules, and error codes.
- Snapshot rate and mandatory fields.
- LAN address/port, join-code behavior, static serving, and origin policy.
- Numeric representation and deterministic command-log fields.


 - I don't have hard dimensions to give for stage building and entity sizes and those can be handled during manual testing.
 - again, no constants for that, and that's why we need manual testing.
 - this needs to be determined between the engineer and architect
 - Starting points are zero, score ultimately determines who wins the round(for the longer game just count round winners), each round should start players at 0 and then the end of the round will count the winner, there shouldn't be any saved data beyond the end of a game(no leaderboards or anything), Just display the tied winners if there is a tie, and simply direct players back to the start menu if they want to play another game.
 - These need to be determined between the architect and engineer.
 - snapshot can be captured once every couple of tick rates. Such as 30hz or 15hz.
 - I don't have LAN addresses/ports, join-codes, static serving, or origin policy. This needs determined between architect and engineer.
 - This needs determined by the architect and engineer, and the user will provide feedback through manual testing.