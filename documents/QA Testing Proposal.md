# QA Testing Proposal — First Version

## 1. Purpose

This proposal defines the QA approach for the first playable version of the dodgeball game. It converts the approved user answers into a practical acceptance checklist covering:

- Required automated unit tests
- Manual Chrome desktop verification
- Deterministic physics, collision, and boundary behavior
- Turns, timers, rounds, scoring, and winner selection
- Host-disconnect behavior
- Best-effort four-player verification

No production game code is included in this proposal.

## 2. Approved QA scope

| Area | First-version decision |
|---|---|
| Browser | Current desktop Chrome only |
| Other browsers | Out of scope |
| Mobile/tablet | Out of scope |
| Automated testing | Unit testing is the required automated layer |
| Manual testing | Required for Chrome desktop gameplay and UI |
| Simulation | Deterministic 2D physics at 60 FPS |
| Authority | Server/host owns positions, collisions, scores, turns, rounds, and win conditions |
| Input | Keyboard: A/D or arrow keys for movement; E for attack |
| Players | Up to four active players |
| Networking | LAN support is relevant; full online-play validation is not required for this first version |
| Host disconnect | The game should end when the host disconnects |
| Four-player test | Best effort; failure to run four machines does not determine sprint success |
| CI | Not required for this version |
| Accessibility standard | No WCAG conformance target for this version |

## 3. Test layers

### 3.1 Required automated layer: unit tests

Unit tests should cover deterministic game-domain behavior without requiring a browser, live network, or four-player session.

The unit-test suite should cover:

- Game-state and state-machine transitions
- Player movement and input validation
- Attack eligibility and one-attack-per-turn enforcement
- Turn timers and expired/inactive turns
- Round and match transitions
- Collision and hitbox calculations
- Boundary containment and bounce behavior
- Damage and score calculations
- Tie and winner selection
- Host-authority checks
- Malformed, missing, invalid, negative, oversized, or non-finite values
- Repeated runs with identical initial state and inputs

The project should document the selected Python test runner and provide one local command for running the unit suite. The exact runner may be selected with the Architect and Engineer after the implementation structure is known.

### 3.2 Required manual layer: Chrome desktop checks

Manual checks should be performed in desktop Chrome using the actual browser client and game flow.

Manual verification should cover:

- Lobby creation and join-by-code flow
- Host-only match setup and round-count selection
- Timer-preset selection: 30 seconds, 45 seconds, 1 minute, and 2 minutes
- Keyboard movement using A/D and arrow keys
- Attack using E
- Gameplay HUD:
  - Player-colored indicators
  - Damage values
  - Turn timer
  - Round counter
- Canvas presentation and basic-shape visibility
- Resize behavior, if resizing is supported
- Error display when the host disconnects
- Game-over screen displaying the winning player color
- Basic usability without relying on a mouse for core gameplay

## 4. Deterministic physics and collision plan

All physics tests should use fixed initial state, fixed inputs, fixed simulation ticks, and a controlled clock. Running the same case repeatedly must produce the same positions, velocities, collision results, damage, and state transitions.

The Architect and Engineer must document the coordinate system, stage dimensions, hitbox ownership, collision ordering, and invalid-input behavior before final test implementation.

### Required deterministic cases

1. **Boundary containment**
   - Player begins near each stage edge.
   - Player attempts to move beyond the left and right boundaries.
   - Ball approaches each boundary.
   - Objects remain within the boxed stage.

2. **Boundary bounce**
   - Ball contacts the left, right, top, and bottom boundaries.
   - Ball contacts each stage corner.
   - Reflection and resulting velocity are consistent.

3. **Grazing contact**
   - Objects touch at the edge of their circular hitboxes.
   - Test both just-inside and just-outside contact.
   - Confirm the selected contact threshold is consistent.

4. **Overlap**
   - Objects begin partially overlapped.
   - Objects begin fully overlapped where valid.
   - Verify deterministic separation or resolution without NaN values, infinite loops, or object escape.

5. **High-speed movement**
   - Ball or player moves far enough in one tick to risk passing through another object or boundary.
   - Verify the approved anti-tunneling behavior.

6. **Simultaneous collisions**
   - Ball contacts multiple players in one resolution window.
   - Ball contacts a player and stage boundary together.
   - Multiple balls or players contact the same location.
   - Confirm deterministic ordering and damage results.

7. **Hitbox dimensions**
   - Verify the dodgeball hitbox is the approved slightly enlarged circular shape.
   - Confirm visual/basic-shape alignment with the logical hitbox.
   - Verify invalid or negative dimensions are rejected or normalized according to the Engineer's rule.

8. **Repeatability**
   - Replay each fixture multiple times.
   - Compare positions, velocities, collision participants, and resulting state.

## 5. Turn, timer, round, and scoring plan

### Turn behavior

Unit tests should verify:

- Each player receives one turn per round.
- A player may move continuously during their turn.
- A player may attack at most once per turn.
- Legal movement and attack inputs are accepted only for the active player.
- Invalid, stale, duplicate, or out-of-turn commands do not change authoritative state.
- A timer expiration ends the active turn.
- An inactive player is passed over according to the approved turn-transition rule.
- A round ends after every eligible player has completed or been passed over for one turn.
- Repeated rounds do not leak turn, timer, or attack state.

### Timer presets

Verify the four approved presets:

- 30 seconds
- 45 seconds
- 1 minute
- 2 minutes

The test should confirm that the selected value is applied to each turn and that the displayed countdown reaches the correct transition point.

### Damage and scoring

The following rules should be directly represented in unit tests:

- First hit: 100% of the applicable points/damage.
- Second hit: 50%.
- Third hit: 25%.
- Hits after the first three: no additional damage.
- A player's points cannot become negative.
- Damage accumulation and round-end scoring follow the Engineer's approved implementation.
- Score values reset or persist only at the documented state transitions.
- Multiple targets in one attack receive results consistent with the approved hitbox semantics.
- Identical collisions produce identical score deltas.

### Match completion

Verify:

- Configured round count is honored.
- Host-only match settings cannot be changed mid-match.
- Final round ends the match.
- Winner is selected correctly.
- Ties follow an explicitly documented rule.
- Game-over state displays the winning player color.
- Rematch, restart, or cancellation behavior is tested only if implemented and approved.

## 6. Host disconnect and multiplayer checks

### Host disconnect

Because the user specified that a host disconnect ends the game, verify:

- A connected client detects host loss.
- The game transitions to the approved ended/error state.
- No further movement, attack, score, or turn updates are accepted.
- The UI communicates that the host disconnected.
- The client does not remain indefinitely in a playing or waiting state.
- Reconnect behavior is not required for this sprint.

### Best-effort player-count verification

Perform manual multiplayer checks in this order:

1. One-player/local baseline, if supported.
2. Two-player session.
3. Three-player session, if available.
4. Four-player session, if practical on the available machines or environment.

For each successful session, check:

- Join and ready flow
- Player identity/color assignment
- Turn order
- Timer synchronization
- Movement and attack ownership
- Score and damage display
- Round transitions
- Host disconnect behavior

Four-player verification is non-blocking when the environment cannot provide four usable clients or machines. Any limitation and attempted setup should be recorded.

Automated integration/network, latency, packet-loss, reconnect, late-join, and out-of-order-message testing are not required for this first version.

## 7. Defect reporting and evidence

Each defect should include:

- Short title
- Severity
- Browser and operating-system details
- Player count
- Initial state or fixture identifier
- Exact reproduction steps
- Expected result
- Actual result
- Relevant logs or state snapshots
- Screenshot or video for visible issues
- Whether the issue reproduces deterministically

Suggested severity:

- **Blocker:** Prevents starting, playing, ending, or validating the match.
- **High:** Breaks authoritative state, scoring, collision containment, turns, or host-disconnect handling.
- **Medium:** Significant UI or gameplay issue with a workaround.
- **Low:** Cosmetic, wording, or minor presentation issue.

## 8. Explicitly out of scope

The following are excluded from first-version QA unless the user later approves a scope change:

- Firefox, Safari, Edge, or cross-browser compatibility
- Mobile, tablet, touch, or responsive-device support
- WCAG 2.2 AA compliance and full accessibility auditing
- Automated integration, frontend, end-to-end, smoke, or browser-test layers
- CI pipeline setup and pull-request quality gates
- Automated lint, type-check, accessibility, or performance gates
- Public matchmaking or public lobbies
- Full online-internet networking validation
- Reconnect behavior
- Late-join behavior
- Spectator slots
- More than four active players
- Latency, packet-loss, and out-of-order network simulation
- Gamepad support
- Final art assets and visual polish beyond the approved shell/HUD
- Performance benchmarking beyond observing obvious stutter or unusable responsiveness
- Production deployment validation
- Rematch behavior unless implemented and specifically approved
- Any requirement not represented in the approved Q&A or later approved Architect/Engineer interface documents

## 9. User approval checklist

The first version is ready for QA sign-off when all applicable items below pass or have an explicit user-approved disposition.

### Automated tests

- [ ] Unit-test runner and local command are documented.
- [ ] State-machine transitions are covered.
- [ ] Input validation and malformed-value behavior are covered.
- [ ] Movement, attack, timer, and turn rules are covered.
- [ ] Collision, hitbox, boundary, grazing, overlap, high-speed, and simultaneous-contact cases are covered.
- [ ] Damage, score, round, tie, and winner rules are covered.
- [ ] Repeated deterministic runs produce identical results.
- [ ] Tests do not require a live four-player session.

### Manual Chrome desktop checks

- [ ] Lobby can create and join a server using a code.
- [ ] Host can select round count and start the match.
- [ ] Timer presets work.
- [ ] A/D, arrow keys, and E perform the approved actions.
- [ ] Core gameplay works without a mouse.
- [ ] Players and balls remain inside the boxed stage.
- [ ] HUD shows player colors, damage, timer, and round number.
- [ ] Canvas/basic shapes remain readable and aligned with gameplay.
- [ ] Game-over screen shows the winning player color.
- [ ] Host disconnect ends the game and displays an appropriate state.
- [ ] Resize behavior, if present, does not change gameplay coordinates.
- [ ] Two-player verification passes.
- [ ] Three- and four-player verification is attempted when practical, with limitations documented.

### Release disposition

- [ ] No unresolved Blocker defects remain.
- [ ] No unresolved High defects remain without explicit user approval.
- [ ] Known limitations are recorded.
- [ ] User has approved any exceptions or deferred requirements.
- [ ] QA provides a final pass/fail summary.

### Proposal approval

- [x] I approve this first-version QA scope.
- [x] I approve unit tests as the required automated layer.
- [x] I approve manual Chrome desktop gameplay verification.
- [x] I approve deterministic 60 FPS physics and collision coverage.
- [x] I approve turn, timer, round, scoring, and winner coverage.
- [x] I approve host disconnect ending the game.
- [x] I approve best-effort four-player verification.
- [x] I approve the explicit out-of-scope items.
- [x] I understand that any scope or acceptance change requires renewed approval.
