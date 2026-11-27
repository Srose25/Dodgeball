# SP-8 Browser Client Manual Test Guide

## Launch

From the project root, use the active Python 3.12 environment with the dependencies installed:

```powershell
python -m pip install -r requirements.txt
python -m server.main
```

Open the printed `http://<host>:<port>/` URL in Chrome on the host and on LAN clients. The server binds `0.0.0.0` and chooses the first available port from 8765 through 8775 when no `--port` is supplied. The browser derives its WebSocket endpoint from the page origin.

## SP-8 checks

1. Create a lobby, copy the six-character code, and join from a second Chrome window using a different name.
2. Confirm the roster and readiness states update. On the host, apply rounds and turn seconds; verify non-host clients do not show host configuration controls.
3. Mark every connected player ready and start the match from the host. Confirm the canvas shows the boxed stage, player colors, ball, damage/score lines, centered timer, active-player outline, and round number.
4. During the active turn, use A/D and Left/Right Arrow to send movement intents and E once to send attack. Try input out of turn and after timeout; the server should reject it without client-side position mutation.
5. Resize Chrome. The canvas may resize visually, but logical motion and server snapshots must remain unchanged.
6. Complete a match and verify winner/tie text and scores. Use Return to setup to leave the terminal screen.
7. Close the host browser or stop the server. Remaining clients should show the host-disconnected terminal screen.

## Automated checks

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q simulation server client shared tests
python -m simulation
```

The browser asset checks are static because the test suite does not require Chrome or a live LAN socket.
