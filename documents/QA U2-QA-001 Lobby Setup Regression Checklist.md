# QA U2-QA-001 — Lobby and Setup Regression Checklist

Use this checklist with `tasks/U2-SP8-lobby-setup-repair-task-set.md`. It is intentionally limited to QA coverage; it does not authorize changes to the server or browser implementation.

## Automated regression coverage

Run from the project root:

```powershell
py -m unittest discover -s tests -p "test_*.py" -v
```

The U2-QA-001 tests cover:

- host creation and guest join;
- shared roster and player count;
- lobby/setup phase visibility contract;
- host configuration propagation;
- ready/unready propagation;
- host-only start gating;
- pre-match movement and attack rejection without state mutation;
- valid transition into `ACTIVE_TURN`;
- late-join rejection after match start.

Client contract failures should be treated as defects, not waived because server-side rejection tests pass.

## Manual LAN retest

### Preparation

- [x] Install dependencies with the same interpreter used to run the server.
- [x] Start with `py -m server.main`.
- [x] Record the actual LAN URL, not `0.0.0.0`.
- [ ] Use one host Chrome session and one guest Chrome session on a second computer or LAN-reachable browser.
- [ ] Capture the server terminal and browser DevTools Console/Network panels.

### Host create flow

- [ ] Initial page shows the lobby screen and a connected status.
- [ ] Clicking **Create lobby** keeps the browser on lobby/setup.
- [ ] No canvas, gameplay timer, movement hint, or attack error appears before match start.
- [ ] Setup shows the six-character join code.
- [ ] Setup shows connected count, maximum capacity, roster, player IDs/colors, and readiness.
- [ ] Host sees round-count and turn-time controls.
- [ ] Host sees the Start Match control and its readiness prerequisite.

### Guest join and roster propagation

- [ ] Guest opens the host's usable LAN URL.
- [ ] Guest joins using the displayed code.
- [ ] Host roster updates without refresh.
- [ ] Guest sees the same roster and connected count.
- [ ] Host and guest receive the same join code and setup phase.
- [ ] An invalid or late join code produces a visible structured error.

### Host and guest permissions

- [ ] Guest does not see usable host configuration controls, or they are disabled.
- [ ] Guest cannot change rounds or turn duration through the UI.
- [ ] Guest cannot start the match.
- [ ] Direct unauthorized setup requests produce a visible rejection and do not mutate state.

### Configuration and readiness

- [ ] Host selects a round count and turn duration.
- [ ] Guest sees the selected values before match start.
- [ ] Guest toggles Ready; host sees the updated readiness immediately.
- [ ] Host toggles Ready; guest sees the updated readiness immediately.
- [ ] Start is blocked while any required player is unready, with an understandable explanation.
- [ ] No setup change starts gameplay by itself.

### Pre-match command safety

- [ ] Before Start Match, attempt movement with A/D and arrow keys.
- [ ] Before Start Match, attempt attack with E.
- [ ] No gameplay command is sent by the browser before `ACTIVE_TURN`.
- [ ] If a pre-match command is injected through DevTools, the server rejects it.
- [ ] Rejected commands do not move players, change damage, consume an attack, or change phase.

### Valid match start

- [ ] Mark all required players ready.
- [ ] Host starts the match.
- [ ] Both clients transition from setup to the game screen only after an authoritative active-game snapshot/event.
- [ ] The stage, player colors, ball, round number, timer, and active-player indicator are visible.
- [ ] The active player can move and attack; inactive players cannot.
- [ ] A player joining after match start is rejected and does not alter the roster.

## Evidence to record

- [ ] Server URL and bind address.
- [ ] Browser URL used by each client.
- [ ] Player names and assigned IDs/colors.
- [ ] Join code.
- [ ] WebSocket `/ws` status and close reason, if any.
- [ ] First protocol messages: `hello`, `create_lobby`/`join_lobby`, `welcome`, `lobby_state`.
- [ ] Representative `lobby_state` fields: phase, roster, count, readiness, rounds, turn duration.
- [ ] Any `command_rejected` code/message.
- [ ] Screenshots of host setup, guest setup, blocked start, and active match.

## Pass criteria

- [ ] No blocker or high-severity lobby/setup defect remains.
- [ ] Both clients remain in setup until valid match start.
- [ ] Host/guest permissions and readiness/configuration propagation are correct.
- [ ] No gameplay input is accepted before `ACTIVE_TURN`.
- [ ] A valid ready match reaches active gameplay on both clients.
