# Implementation Decisions — v1

Status: Architect resolution after user approval. These defaults unblock implementation; physics values are intentionally tunable during manual testing.

| Area | v1 decision | Assumption / test note |
|---|---|---|
| Logical stage | `1280 x 720` units; origin top-left; x right, y down | Canvas scales uniformly to fit; gameplay coordinates never change. |
| Player body | Circle radius `24` | Tune visually at SP-3; server owns the value. |
| Dodgeball body | Visible radius `14`; collision radius `18` | Implements a modest enlarged circular hitbox. |
| Movement | Horizontal only; acceleration `1800 units/s²`, deceleration `2400 units/s²`, max speed `360 units/s` | Opposing held directions cancel; releasing both decelerates to zero. Tune at SP-2. |
| Ball physics | Fixed-step integration; boundary restitution `0.85`; player boundary is clamped | No frame-rate-dependent physics. |
| Attack | Forward semicircle/reach `72` units, active for one tick; one accepted attack per turn | Exact feel is manual-tuned at SP-4. |
| Knockback | Direction from attacker/ball contact; impulse `220 + 2 * accumulated_damage`, capped at `520`; linear decay over `0.25s` | Safe bounded default; verify no stage escape or unfair stacking. |
| Collision priority | Boundary containment/bounce, then attack contacts, then ball-player contacts, then player-player separation | Within a category sort by stable entity ID. Simultaneous events resolve once per tick. |
| Contact identity | `(source_id, target_id, contact_epoch)`; epoch increments on separation or ball bounce | Damage applies on contact enter, and once again only after a new epoch. |
| Ball damage | Base value `100`; first three valid contacts use `100%`, `50%`, `25%`; later contacts `0` | Contact count is per ball for the match; manual testing verifies intended reset behavior. |
| Scoring interpretation | Every round starts each player at round score `0`; gameplay awards score; highest round score wins the round | Damage remains separate and drives knockback. Because the Q&A does not define how gameplay awards score, v1 mirrors approved damage events into nonnegative round score unless manual testing changes that rule. |
| Match winner | Most round wins across configured rounds; ties display all tied winners | No persistent results, leaderboard, or sudden death. Result screen offers return to start menu. |
| Turn order | Stable player-ID order, frozen when setup starts; disconnected players removed before the next turn | No-input players consume the full timer. |
| Command boundary | Drain commands received before each tick cutoff; order by server receive ordinal then client sequence | Late/duplicate/stale commands are rejected, never applied partially. |
| Numeric representation | Python `float` for positions/velocities, integer ticks and scores, serialized finite decimals | Reject NaN/infinity/non-finite values; deterministic ordering avoids random behavior. |
| Protocol | JSON `version: 1`; `hello` first; max decoded message 16 KiB; gameplay `seq` strictly increasing | Error codes are machine-readable; rejected commands return `command_rejected` when possible. |
| LAN hosting | Bind `0.0.0.0:8765`; fallback ports `8766`–`8775`; six-character uppercase join code | Host shares `http://<lan-ip>:<port>/`; client derives `/ws`. |
| Static serving | Same Python process serves `client/` and WebSockets | Same-origin LAN URL; loopback permitted for development. |
| Snapshots | 30 Hz authoritative snapshots; immediate lifecycle/result events | 15 Hz is the only permitted manual-tuning alternative. |
| Non-host disconnect | Stop accepting commands immediately; finish active turn if applicable, then remove from scheduling; otherwise remove immediately | If no active players remain, emit an abandoned-session result. |
| Command log | `tick`, receive ordinal, connection/player ID, client seq, type, accepted/rejected code | No replay/state hash requirement in v1. |

## Scoring clarification and safe v1 interpretation

The approved clarification says that starting points are zero, score determines the round winner, and longer games count round winners. Earlier material described damage, remaining points, and knockback together, which is internally ambiguous. To avoid blocking implementation:

- `damage` is a separate combat quantity and never becomes negative.
- `round_score` starts at zero and is the only value used to select the round winner.
- A valid damage event awards the corresponding positive score to the attacking/source player, using the same 100/50/25 contact weighting as the damage event unless manual testing identifies a mismatch.
- Round score resets at the start of every round.
- `round_wins` persists only in memory until match result, then is discarded.
- The Engineer must expose these values separately in state and snapshots so manual testing can change the scoring adapter without rewriting physics.
