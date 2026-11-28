# User Testing 2 — Lobby and Setup Repair Task Set

## Scope

Repair the SP-8 lobby-to-match flow exposed by `documents/User Testing/User Testing 2.md`. Creating or joining a lobby must keep all clients on an authoritative roster/setup screen until the host successfully starts a configured, ready match.

## Agreed diagnosis

The server remains in `LOBBY` after `create_lobby`, but its tick loop broadcasts snapshots. The client currently routes every non-result snapshot to the gameplay screen, so lobby snapshots hide the join code and setup controls. Movement and attack errors are correct server rejection of commands sent before `ACTIVE_TURN`; the misleading browser screen makes them appear to be gameplay failures.

## Tasks

### U2-AR-001 — Define phase-to-screen contract

- Document the authoritative mapping: `LOBBY`/`SETUP` → setup screen; active gameplay phases → game screen; `MATCH_RESULT` → result screen; host disconnect → terminal error screen.
- Preserve Python ownership of phase, state, scores, positions, and transitions.
- Define that creating or joining a lobby never starts gameplay.

### U2-EN-001 — Keep lobby and setup state visible

- Extend `lobby_state` with phase, configured rounds, turn duration, maximum players, and start/readiness status.
- Keep the server’s authoritative lobby/setup state separate from gameplay rendering.
- Reject late joins and invalid setup transitions with visible structured errors.

### U2-EN-002 — Gate gameplay on authoritative active phase

- Route client screens from authoritative phase data.
- Do not show the canvas, movement hints, or attack controls during `LOBBY` or `SETUP`.
- Send movement/attack commands only during `ACTIVE_TURN`; retain server-side rejection as defense-in-depth.

### U2-EN-003 — Preserve and clarify setup controls

- Show the six-character join code, connected count, roster, player IDs/colors, readiness, host identity, round selector, turn-time selector, and start prerequisites.
- Keep host-only configuration/start controls hidden or disabled for guests.
- Keep both clients on setup until a valid `start_match` transition occurs.

### U2-QA-001 — Add regression coverage

- Cover host create, guest join, roster broadcast, readiness, host configuration, invalid/late join, and pre-match command rejection.
- Verify no gameplay snapshot or gameplay screen appears before match start.
- Verify active gameplay begins only after all required readiness/start conditions pass.
- Add manual retest steps for one host plus one guest using the real LAN URL.

## Acceptance criteria

- Creating a lobby does not start gameplay or hide setup controls.
- A second client can join with the displayed code and both clients see the same roster/count.
- Round count and turn-time controls are visible to the host before match start.
- Guests see the selected configuration but cannot change it or start the match.
- Ready/unready updates propagate to all clients.
- Start is blocked with a visible explanation until required setup conditions pass.
- No movement or attack input is sent or accepted as gameplay before `ACTIVE_TURN`.
- The game screen appears only after an authoritative active-game snapshot.
- Existing simulation, protocol, and SP-8 tests continue to pass.
