# QA Task Set

## Scope

Create and run tests for the game systems, review implementation quality, verify the web frontend, and confirm that the completed project satisfies the approved requirements. QA must avoid production-code bloat and must not begin final validation until the relevant answers in `documents/User Q&A.md` and the Architect/Engineer interfaces are approved.

## Dependencies

- The user must answer the QA questions in `documents/User Q&A.md`, especially the browser/platform matrix, accessibility target, network topology, input model, collision semantics, test frameworks, and CI gates.
- The Architect must publish the frontend/game structure, coordinate system, canvas scaling, and hitbox ownership.
- The Engineer must define the simulation tick, movement/collision ordering, scoring rules, invalid-input behavior, and authoritative state boundary.
- Architect and Engineer must agree on the networking library and protocol before QA finalizes network integration tests; the plan requires user approval before networking implementation.
- The project must identify its Python and browser test runners, dependency installation method, and CI provider before CI tasks can be executed.

## Tasks

### QA-001 — Establish the QA contract

- Convert approved Q&A answers into a requirements checklist and trace every requirement to one or more tests.
- Record supported browsers, operating systems, viewport classes, input methods, Python version, and network assumptions.
- Define severity levels, reproducibility information, and evidence required for pass/failure.
- **Exit criteria:** The approved QA matrix and acceptance checklist have no unresolved implementation-affecting entries.

### QA-002 — Define test architecture and fixtures

- Select lightweight unit, integration, frontend, accessibility, and end-to-end test layers matching the implementation stack.
- Create reusable fixtures/fakes for players, stages, balls, turns, scores, malformed messages, and controlled time/ticks.
- Keep test helpers isolated from production runtime paths.
- **Exit criteria:** A documented local test command and fixture strategy run without requiring a live four-player session.

### QA-003 — Validate domain types and defensive behavior

- Test valid and invalid types, missing fields, null-like values, non-finite numbers, negative/oversized values, and malformed network payloads.
- Verify rejected or normalized inputs do not crash the game loop or create inconsistent state.
- Review exception handling for clear diagnostics and no broad silent catches.
- **Exit criteria:** Type and invalid-input tests pass with explicit expected behavior for every rejected or normalized input.

### QA-004 — Test collision, hitbox, and boundary rules

- Cover player-player, player-ball, ball-stage, and stage-corner collisions, including grazing contact, overlap, high-speed movement, and simultaneous contacts.
- Verify confined-stage behavior prevents tunneling and keeps objects within approved bounds.
- Check hitbox dimensions and offsets against the basic-shape test presentation.
- **Exit criteria:** Deterministic collision and boundary tests cover all approved edge cases at supported simulation rates.

### QA-005 — Verify turn, scoring, and round transitions

- Test legal and illegal action order, one action per turn, end-of-turn transitions, round counting, score deltas, ties, and winner selection.
- Include four-player scenarios and repeated rounds to detect state leakage.
- **Exit criteria:** State-machine tests show consistent displayed state, authoritative state, and score history.

### QA-006 — Verify frontend presentation and responsive behavior

- Check lobby, host setup, gameplay HUD, turn indicator, score display, error/disconnect state, and game-over state.
- Test canvas scaling, resize, aspect ratio, clipping, z-order, readable text, hitbox alignment, and minimum viewport behavior.
- Verify basic testing shapes remain distinguishable without final art assets.
- **Exit criteria:** The presentation checklist passes on every approved browser/platform without critical layout or interaction issues.

### QA-007 — Verify accessibility and input paths

- Test keyboard-only operation, focus order, focus visibility, labels, status messages, contrast, color-independent feedback, and reduced-motion behavior.
- Run automated accessibility checks and manually verify canvas interactions that automation cannot interpret.
- Test approved touch/gamepad paths when included in scope.
- **Exit criteria:** Mandatory accessibility checks pass at the approved conformance level, with documented exceptions explicitly approved by the user.

### QA-008 — Exercise multiplayer and failure scenarios

- Test two- through four-player sessions for turn synchronization, duplicate/out-of-order messages, latency, packet-loss simulation, disconnect/reconnect, late join, and host departure as applicable.
- Verify invalid or stale actions cannot alter authoritative scores or bypass turn ownership.
- Capture logs and state snapshots sufficient to reproduce failures.
- **Exit criteria:** Approved network acceptance scenarios pass within agreed latency and recovery limits.

### QA-009 — Add CI quality gates and test reporting

- Configure the approved CI pipeline to install pinned dependencies and run formatting/lint/type checks, automated tests, accessibility checks, and browser smoke tests as applicable.
- Publish failure logs, coverage, screenshots/videos, and test reports where useful.
- Confirm deterministic results across repeated runs and document quarantined or non-blocking checks.
- **Exit criteria:** A clean pull-request run proves required gates execute, and an intentional failing test blocks the build.

### QA-010 — Release acceptance and regression sign-off

- Execute the full traceability checklist on a release candidate, including supported environments and a four-player smoke session.
- Review performance for stutters, excessive test/runtime overhead, and frontend responsiveness under approved load.
- File defects with reproduction steps, expected/actual behavior, severity, environment, and evidence; retest fixes and run regression coverage.
- **Exit criteria:** Every acceptance criterion passes or has an explicit user-approved disposition, and QA publishes a final sign-off report.
