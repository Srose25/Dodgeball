# Engineer Stopping Points

Status: Approved implementation workflow. User approval is recorded in `documents/Architect-Engineer Approval Q&A.md`; provisional details are recorded in `documents/Implementation Decisions.md`.

## SP-0 — Requirements and architecture gate

Acceptance criteria:

- The user approves this stopping-point plan and the Engineer Proposal.
- The Architect provides the coordinate system, canvas scaling rule, hitbox ownership, module interfaces, and state-machine transition contract.
- Starting points, score aggregation, tie behavior, non-host disconnect behavior, and inactive-turn semantics are recorded in `documents/Implementation Decisions.md`.

Manual review:

1. Read the proposal and identify any rule that is not intended.
2. Confirm that browser rendering is display-only and Python owns simulation state.
3. Approve or amend the unresolved decisions in writing.

Stop condition: implementation may begin; pause at each later stopping point for manual review.

## SP-1 — Deterministic local simulation shell

Acceptance criteria:

- A 60 Hz fixed-tick simulation can be advanced without a browser, Pygame window, or network.
- Configuration is centralized.
- State contracts and transitions are documented and invalid transitions are rejected deterministically.
- Unit tests can replay identical initial state and commands to identical state.

Manual review:

1. Run a no-input simulation and verify tick/revision progression.
2. Replay the same command sequence twice and compare state/results.
3. Try malformed and out-of-state commands and verify no partial mutation.

Stop condition: wait for user approval before controls and turn flow.

## SP-2 — Local continuous movement and four-player turns

Acceptance criteria:

- A/D and arrow keys produce continuous left/right intent.
- One active player at a time receives movement and can move during their timed turn.
- E is not yet gameplay-complete unless the attack slice is included; at most one accepted attack is recorded per turn.
- Turn presets are 30, 45, 60, and 120 seconds; timeout advances the fixed turn order.
- Up to four players receive one turn each per round; a no-input turn still expires and advances.

Manual review:

1. Hold each left/right key and verify continuous movement in both directions.
2. Release the key and verify the approved stop behavior.
3. Attempt movement and attack out of turn and verify rejection/no mutation.
4. Press E repeatedly and verify one accepted attack for that turn.
5. Verify timeout and four-player turn order.

Stop condition: wait for user approval before collision foundations.

## SP-3 — Stage boundaries and deterministic collision foundations

Acceptance criteria:

- Player and ball bodies remain inside the boxed stage.
- Boundary collisions bounce with approved coefficients.
- Grazing, overlap, high-speed, simultaneous, and invalid-dimension cases have unit coverage.
- Identical inputs produce identical outcomes at 60 Hz.

Manual review:

1. Drive a player and ball into every boundary.
2. Test grazing and overlapping bodies.
3. Exercise simultaneous and high-speed contacts.
4. Confirm resizing the browser/canvas does not alter simulation coordinates.

Stop condition: wait for user approval before damage/knockback.

## SP-4 — Attack, damage, knockback, and bouncing-ball interactions

Acceptance criteria:

- The approved expanded circular hitbox can affect every valid target inside it.
- First/second/third bouncing-ball hits apply 100%/50%/25% of the approved hit value; later hits apply zero.
- Victim points never become negative.
- Knockback increases from accumulated damage using the approved formula.
- Duplicate overlap/contact events do not repeatedly deduct without an approved contact transition.

Manual review:

1. Attack one neighboring target and a multi-target hitbox case.
2. Verify one E attack per turn.
3. Verify three diminishing bouncing-ball contacts and a fourth no-damage contact.
4. Verify boundary bounce after knockback and no stage escape.
5. Verify damage/score and duplicate-event behavior.

Stop condition: wait for user approval before round/match scoring.

## SP-5 — Round scoring and match completion

Acceptance criteria:

- Each configured round schedules one turn per active player.
- Round results freeze before the next round.
- Final-round completion enters match-result state and displays the winning color.
- Approved tie behavior and rematch/setup behavior are deterministic.

Manual review:

1. Run a one-round match and verify every active player turn.
2. Run multiple rounds and verify accumulation.
3. Force a tie and verify the approved result.
4. Verify final-round termination and winner display.

Stop condition: wait for user approval before networking.

## SP-6 — Networking design gate (no code)

Acceptance criteria:

- Architect and Engineer use the approved transport/library, topology, schema, snapshot rate, command semantics, connection policy, packaging, and determinism boundary.
- The final networking proposal and implementation decisions are recorded before transport work.
- LAN host-disconnect behavior and four-player admission are written as testable acceptance criteria.

Manual review:

1. Review the final protocol examples and rejection cases.
2. Confirm no networking implementation has started before approval.

Stop condition: hard gate; transport remains deferred until SP-1 through SP-5 are complete and the recorded contracts are implemented.

## SP-7 — LAN implementation and multi-client synchronization

Acceptance criteria:

- A host can create a LAN session and up to four browser clients can join.
- Only server-validated intents change state.
- Snapshots remain ordered and clients render the same authoritative state.
- Malformed, duplicate, stale, out-of-turn, and over-capacity requests are handled safely.
- Host disconnect ends the game for all clients with the approved terminal reason.

Manual review:

1. Connect one, two, and four clients on the LAN.
2. Exercise movement, attack, turn, round, and match flow concurrently.
3. Send invalid/duplicate/stale commands.
4. Disconnect the host and verify every client receives the terminal result.
5. Record limitations if four physical machines are unavailable; this test is valuable but not sprint-fatal per the Q&A.

Stop condition: wait for user approval before browser integration polish.

## SP-8 — Browser HUD and end-to-end handoff

Acceptance criteria:

- Chrome desktop lobby supports server code creation/join flow.
- Canvas displays the authoritative stage without mutating simulation state.
- HUD shows color-matched damage/score lines, centered turn timer, round number, and simple winner color.
- Keyboard controls work without mouse input.
- Resize does not alter gameplay coordinates.

Manual review:

1. Test lobby create/join flow.
2. Test keyboard-only controls.
3. Verify HUD during active turn, round result, and match result.
4. Resize the window and verify simulation behavior is unchanged.

Stop condition: wait for user acceptance and handoff to QA.

## Change-control rule

If the user changes an approved acceptance criterion, record the old and new wording, affected stopping points, and the new approval date here before implementation resumes. The Engineer stops at the current gate until that approval is explicit.

