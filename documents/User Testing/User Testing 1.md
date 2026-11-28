# User testing 1.

| SP-8 Check | Answer |
|------------|--------|
|1. Create a lobby, copy the six-character code, and join from a second Chrome window using a different name.| `I was unable to create the server, after running "py -m server.main. Both computers kept reading the same "disconnected" status in the top right.`|
|2. Confirm the roster and readiness states update. On the host, apply rounds and turn seconds; verify non-host clients do not show host configuration controls.| `Unable to confirm the roster, readiness status, or apply rounds and other settings.`|
|3. Mark every connected player ready and start the match from the host. Confirm the canvas shows the boxed stage, player colors, ball, damage/score lines, centered timer, active-player outline, and round number.| `Unable to start game`|
|4. During the active turn, use A/D and Left/Right Arrow to send movement intents and E once to send attack. Try input out of turn and after timeout; the server should reject it without client-side position mutation.| `Unable to begin game`|
|5. Resize Chrome. The canvas may resize visually, but logical motion and server snapshots must remain unchanged.| `Unable to test resizing.`|
|6. Complete a match and verify winner/tie text and scores. Use Return to setup to leave the terminal screen.| `Unable to begin game.`|
|7. Close the host browser or stop the server. Remaining clients should show the host-disconnected terminal screen.| `Unable to test "host disconnected" errors.`|

## Other notes.
1. I noticed that styles.css was being linked to as "/styles.css" in the index.html file, despite it being in the main client folder with the rest of the front end code. I fixed that bug and was able to get it to display properly.
2. Styles.css is completely unreadable. This is unacceptable. Please go through the styles sheet, and make sure each selector gets it's own line. That is only a start however. Make sure that each attribute within a selector gets its own line as well. Readable code is top priority here.
3. When running the server with `py -m server.main`, the terminal showed me this:
```
Dodgeball LAN server: http://0.0.0.0:8765/
WebSocket endpoint: ws://0.0.0.0:8765/ws
```
Which looks to be running properly, but again, according to my testing I was not able to even create a lobby.

### Instructions.

Spin up our three agents to examine the codebase to figure out why the website is showing the "disconnected" status. Once the agents have found a solid reason behind the server issue, have them systematically make fixes to the project. Make sure that each of them are keeping each other in check with their given expertise. Have one subagent fix the styles.css formatting issue. Once they are done working, add a section at the end of this file that tells me what the problem was, and how the agents went about fixing it so I can run SP-8's manual checks again.


## Progress report.

### SP-8 repair findings and changes

The three agents found that the disconnected status was caused by a combination of environment, address, and diagnostics problems:

1. The `websockets` package was not available to the same `py` interpreter used to launch the server. The project now reports a clear installation instruction, and the dependency remains declared in `requirements.txt`.
2. `0.0.0.0` was printed as though it were a browser address. It is only a bind-all address. The server now prints separate bind, localhost, and detected LAN URLs. Chrome clients must open the usable LAN URL, such as `http://192.168.x.x:8765/`, never `http://0.0.0.0:8765/`.
3. The transport previously swallowed all exceptions with `except Exception: pass`, turning handshake or routing failures into an unexplained “Disconnected” status. The server now logs connection IDs and unexpected errors and returns structured protocol errors when possible.
4. The server sent a provisional welcome and then a second identity-bearing welcome. The handshake is now documented and tested as `hello → create_lobby/join_lobby → welcome → lobby_state`, with one definitive welcome.
5. Message validation previously checked mostly the common envelope. It now validates required fields and types for hello, lobby, setup, and gameplay messages, rejecting malformed input without mutating state.
6. The agents added regression coverage for static files, `/ws` passthrough, protocol compatibility, hello/create/join flow, duplicate welcomes, malformed messages, and client assets.
7. `client/styles.css` was reformatted so selectors and declarations are readable on separate lines without changing the intended styling.

The Architect reviewed the repairs and found no remaining implementation correction. The remaining requirement is live verification: install the dependency with the same interpreter used to launch the server, open the printed LAN URL, confirm Chrome shows `GET /ws → 101 Switching Protocols`, and rerun the SP-8 checklist using [QA LAN Static Regression Checklist.md](QA%20LAN%20Static%20Regression%20Checklist.md).

Recommended commands:

```powershell
py -m pip install -r requirements.txt
py -c "import websockets; print(websockets.__version__)"
py -m server.main
```

Automated verification after the repairs: **52 tests passed** and compilation passed. The live LAN handshake could not be verified in the agent environment because `websockets` was unavailable to its active interpreter.


