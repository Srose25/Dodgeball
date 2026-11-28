# QA LAN and Static Regression Checklist

This checklist supports SP-8 diagnosis without changing server implementation.

## Launch and address verification

- [ ] Install dependencies with the same interpreter used to launch the server:
  `py -m pip install -r requirements.txt`
- [ ] Confirm the dependency is visible to that interpreter:
  `py -m pip show websockets`
- [ ] Start the server with `py -m server.main`.
- [ ] Record the server startup output and selected port.
- [ ] Determine the host computer's actual LAN IPv4 address.
- [ ] Share `http://<LAN-IP>:<port>/` with other computers.
- [ ] Never ask clients to browse to `http://0.0.0.0:<port>/`; that is only a bind address.
- [ ] Capture firewall prompts, server exceptions, and connection/disconnection log lines.

## Chrome static asset checks

In Chrome DevTools, open Network, enable Preserve log, then reload the LAN URL.

- [ ] `GET /` returns `200` and `text/html`.
- [ ] `GET /client.js` returns `200` and a JavaScript content type.
- [ ] `GET /styles.css` returns `200` and `text/css`.
- [ ] No static asset request returns `404`, `403`, or a Python traceback.
- [ ] The console has no module, MIME, or JavaScript parse errors.
- [ ] The page displays the lobby controls and the top-right connection status.

## WebSocket handshake and lobby flow

With DevTools Network filtered to WS:

- [ ] A WebSocket request is made to `ws://<LAN-IP>:<port>/ws`.
- [ ] The WebSocket handshake status is `101 Switching Protocols`.
- [ ] The first client message is versioned `hello` with `request_id` and `client_name`.
- [ ] The server replies with `welcome` containing player and connection identity.
- [ ] Clicking Create lobby sends `create_lobby` after the handshake.
- [ ] The server replies with a host `welcome` and `lobby_state`.
- [ ] `lobby_state` contains a six-character join code and the host roster entry.
- [ ] A second Chrome window/client connects to the same LAN IP and sends `hello`.
- [ ] The second client sends `join_lobby` with the copied code.
- [ ] Both clients receive an updated `lobby_state` containing both players.
- [ ] Invalid join codes produce a visible rejection without closing the WebSocket.

## Evidence to capture

For failures, save:

- The exact LAN URL used; redact public addresses if necessary.
- Chrome Network rows for `/`, `/client.js`, `/styles.css`, and `/ws`.
- The WebSocket Messages panel showing `hello`, `create_lobby`, `welcome`, and `lobby_state`.
- Browser console errors.
- Server startup output and the surrounding server log lines.
- Player count, browser version, operating system, and whether the client was host or guest.

## Expected initial message sequence

```text
GET /
GET /client.js
GET /styles.css
WebSocket CONNECT /ws -> 101 Switching Protocols
hello
create_lobby or join_lobby
welcome
lobby_state
```
