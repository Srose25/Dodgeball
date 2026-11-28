# User Testing 2
## User Story

I am trying to use the website but it is currently not working. I am able to create a lobby now, if I click on the specific link created when I run `py -m server.main`, but I will be unable to get another player connected. Additionally, when I use the website and create a lobby, meaning I specifically hit the "create lobby", the website will immediately take me to a page that looks like the game is starting. I see the player 1 red ball, the timer at the center of the screen, and error messages whenever I try to move or attack. I don't understand why creating a lobby immediately starts the game. There should be an intermediary page to show how many players are connecting / connected so we can troubleshoot the connection process. It's not even an option to pick the amound of rounds or turn time. Lastly, it's unclear whether or not the game is starting after pressing "create lobby", but if it is there is no stage that is being created and it isn't possible to move or attack.

## Progress report.

### Coordinator repair report

The Architect, Engineer, and QA agents agreed that the server was not actually starting the match when **Create lobby** was clicked. The primary defect was client-side phase routing: the server remained in `LOBBY`, but the browser treated every non-result snapshot as gameplay and switched away from the roster/setup screen. That hid the join code, roster, readiness controls, round/turn configuration, and host start controls. Movement and attack errors were correct server rejection of commands before `ACTIVE_TURN`; the browser was presenting gameplay too early.

The agreed repair was documented in [U2-SP8-lobby-setup-repair-task-set.md](../../tasks/U2-SP8-lobby-setup-repair-task-set.md) before implementation.

### Changes made

- Client screen routing now follows authoritative phases: `LOBBY`/`SETUP` stay on setup, `ACTIVE_TURN` enters gameplay, and result/disconnect phases use terminal screens.
- Lobby/setup gameplay snapshots are no longer broadcast as active gameplay frames.
- `lobby_state` now includes phase, connected count, capacity, configured rounds, turn duration, readiness, and `can_start`.
- Setup retains the six-character join code, roster, player colors/IDs, host identity, readiness, configuration, and start status.
- Host-only configuration and match-start controls remain unavailable to guests.
- Movement and attack input are gated by both authoritative `ACTIVE_TURN` and the gameplay screen.
- Regression tests cover host creation, guest joining, roster synchronization, readiness, configuration, late joins, pre-match command safety, and valid match start.
- The protocol documentation now matches the expanded `lobby_state` schema.

### Verification

- Full automated suite: **62 tests passed**.
- Compilation check: passed.
- Architect review: signed off on the U2 repair.
- Live two-computer Chrome/LAN verification: still required.

### Questions for the next user test

1. After clicking **Create lobby**, does the browser remain on setup instead of showing the game canvas?
2. Is the six-character join code visible and easy to copy or type on a second computer?
3. Does setup show the correct connected count, roster, player IDs/colors, and host identity?
4. Can a second Chrome client join using the host's actual LAN URL and displayed code?
5. Do both clients see the same roster and readiness changes without refreshing?
6. Are round-count and turn-time controls visible to the host before match start?
7. Are those controls hidden or disabled for the guest?
8. Does setup explain why **Start Match** is unavailable when a player is not ready?
9. After all required players are ready, does the host start the match and only then reveal the stage, timer, HUD, and gameplay controls?
10. Before match start, do movement and attack attempts remain disabled/rejected without changing state?
11. During the active turn, do movement and attack inputs work for the active player and remain rejected for other players?
12. If any step fails, what exact URL was used, what did Chrome's Network panel show for `/ws`, and what error appeared in the server terminal or browser console?

Use [QA U2-QA-001 Lobby Setup Regression Checklist.md](QA%20U2-QA-001%20Lobby%20Setup%20Regression%20Checklist.md) to capture the results.
