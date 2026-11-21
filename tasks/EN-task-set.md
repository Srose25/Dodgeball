# Engineer Task Set

## Scope

Implement game systems according to the approved architecture. Do not begin game-code implementation until `documents/User Q&A.md`, the stopping points, and all blocking decisions are approved.

## Stopping-point approval workflow

1. Draft `documents/Engineer Stopping Points.md` before implementation.
2. Obtain explicit user approval of the stopping points and blocking requirements.
3. At every stopping point, stop, report completed behavior and limitations, provide manual test steps, and wait for approval.
4. Record any changed acceptance criteria in the stopping-point document and obtain approval before continuing.
5. Networking additionally requires unanimous Architect–Engineer consensus and user approval of the proposal.

## Tasks

### EN-001 — Confirm requirements and dependencies

- Review approved Q&A and identify unresolved controls, turns, scoring, timing, authority, networking, and match-end decisions.
- Confirm architecture interfaces and record blockers or assumptions.

### EN-002 — Define and obtain stopping-point approval

- Create `documents/Engineer Stopping Points.md` with manually testable increments, acceptance criteria, manual steps, and expected results.
- Include a gate before networking work and wait for explicit approval.

### EN-003 — Establish deterministic game-state contracts

- Define player, turn, round, match, collision, score, winner, valid-input, and rejected-input contracts with the Architect.
- Keep simulation testable independently of rendering and transport.

### EN-004 — Implement local input and turn sequencing

- Implement approved controls, action limits, turn order, round transitions, timeouts, and rejection of out-of-turn actions.
- Stop for manual testing of controls, turns, timeouts, and transitions.

### EN-005 — Implement movement, boundaries, and collision foundations

- Implement the approved coordinate/collision model, stage bounds, boundary bounce, and deterministic frame-rate-independent outcomes.
- Stop for manual testing of movement, boundaries, platforms, and collisions.

### EN-006 — Implement attacks, knockback, and bouncing-ball interactions

- Implement approved attack hitboxes, damage/score, knockback, repeated-contact rules, and duplicate-event prevention.
- Stop for manual testing of range, knockback, chained contacts, bounces, and scores.

### EN-007 — Implement round and match scoring

- Track approved scoring across rounds, resolve ties, end after configured rounds, and expose winner/post-match state.
- Stop for manual testing of scoring, ties, final-round termination, and winner display.

### EN-008 — Prepare authoritative simulation boundaries

- Separate client intents from authoritative changes, validate state-changing actions, and document ordering, timestamps, ticks, and duplicate-message assumptions.

### EN-009 — Deliberate and approve networking design

- Compare candidate libraries and protocols against player count, browser, deployment, latency, and reliability requirements.
- Reach unanimous Architect–Engineer consensus, write the proposal, and submit it for user approval.

### EN-010 — Implement networking incrementally

- Implement approved host/server setup, connections, synchronization, invalid/stale/duplicate messages, disconnects, and reconnection behavior.
- Stop for manual multi-client testing under approved conditions.

### EN-011 — Integrate simulation with the front end

- Expose authoritative state to the approved web/canvas path without allowing rendering to mutate it.
- Display approved turn, round, timer, score, collision, and match-completion state.
- Stop for end-to-end manual testing.

### EN-012 — Engineer handoff and QA support

- Document interfaces, transitions, assumptions, and limitations; provide deterministic scenarios to QA; fix findings and rerun relevant checks.
