# Architect Task Set

## Scope

Define the project structure, interfaces, state ownership, browser integration boundary, readability conventions, and networking proposal. Do not implement gameplay code.

## Tasks

### AR-001 — Convert approved requirements into architectural decisions

- Review the answered `documents/User Q&A.md`.
- Record decisions affecting structure, rendering, game flow, readability, and networking.
- Mark unresolved implementation blockers; do not silently assume answers.

### AR-002 — Define repository and module structure

- Propose the Python server, browser client, shared protocol, configuration, tests, and documentation layout.
- Assign ownership of each responsibility and identify application entry points.
- Provide structural placeholders and TODOs only.

### AR-003 — Define core interfaces and data boundaries

- Specify conceptual interfaces for players, dodgeballs, attacks, stages, turns, rounds, matches, commands, and snapshots.
- Document required fields, ownership, mutation boundaries, and separation of domain, transport, rendering, and input concerns.

### AR-004 — Design game flow and state ownership

- Define lobby, setup, turn, collision resolution, round, and match lifecycle states.
- Specify authoritative ownership of positions, collisions, scores, turn order, and win conditions.
- Document host permissions, invalid transitions, readiness, inactive players, and disconnect behavior after approval.

### AR-005 — Specify browser and Pygame integration

- Compare the approved display options and document the selected boundary.
- Define whether the browser receives frames, structured snapshots, or both.
- Define validated browser commands and required HTML, canvas, JavaScript, and Python interfaces.

### AR-006 — Evaluate networking options with the Engineer

- Compare browser compatibility, ordering, latency, connection lifecycle, testing support, and four-player suitability.
- Recommend one transport/library and document rejected alternatives.
- Do not finalize the choice without unanimous Architect–Engineer consensus.

### AR-007 — Draft the networking proposal

- Specify server/client responsibilities, message categories, validation, connection lifecycle, synchronization, and errors.
- Mark the proposal as requiring user approval before networking implementation.

### AR-008 — Establish readability conventions

- Define naming, type hints, docstrings, comments for non-obvious rules, public-interface documentation, and acceptable function/class size.

### AR-009 — Define incremental implementation boundaries

- Break the architecture into milestones with dependencies and acceptance criteria.
- Coordinate milestones with `documents/Engineer Stopping Points.md` and identify those requiring manual testing.

### AR-010 — Perform architecture handoff

- Deliver the approved structure, interfaces, state flow, browser notes, conventions, and networking proposal.
- List blockers and confirm that no user-approved decision was silently assumed.
