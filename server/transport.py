"""WebSocket transport and same-process static-file serving for SP-7."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
import uuid
from typing import Any

from shared.protocol import MAX_MESSAGE_BYTES, validate_message

from .lobby import (
    LobbyRuntime,
    PlayerSession,
    QueuedCommand,
    command_rejected_message,
    generate_join_code,
)

try:
    from websockets.asyncio.server import ServerConnection, Server, serve
    from websockets.http11 import Headers, Response
except ImportError:  # pragma: no cover - compatibility with older websockets releases.
    try:
        from websockets.server import WebSocketServerProtocol as ServerConnection
        from websockets.server import serve
        Server = Any
        Headers = None
        Response = None
    except ImportError:  # pragma: no cover - lets protocol/static tests run without extras installed.
        ServerConnection = Any
        serve = None
        Server = Any
        Headers = None
        Response = None

try:
    from websockets.exceptions import ConnectionClosed
except ImportError:  # pragma: no cover - only reached without the optional runtime dependency.
    class ConnectionClosed(Exception):
        """Fallback marker used when importing the server without websockets installed."""


LOGGER = logging.getLogger(__name__)


COLORS = ("red", "blue", "green", "yellow")


class GameServer:
    """Manage LAN lobbies and WebSocket connections without game-rule duplication."""

    def __init__(self, client_root: Path | None = None) -> None:
        """Create a server with no active lobbies."""

        self.lobbies: dict[str, LobbyRuntime] = {}
        self.sessions: dict[str, PlayerSession] = {}
        self.receive_ordinal = 0
        self.client_root = client_root or Path(__file__).parents[1] / "client"

    async def handler(self, websocket: ServerConnection) -> None:
        """Handle one client connection from hello through disconnect cleanup."""

        connection_id = uuid.uuid4().hex[:12]
        session = PlayerSession(connection_id, connection_id, "unknown")
        session.send = lambda message: websocket.send(json.dumps(message, separators=(",", ":")))
        self.sessions[connection_id] = session
        try:
            first = await websocket.recv()
            try:
                message = self.decode(first)
            except (ValueError, UnicodeError, json.JSONDecodeError) as error:
                await self.send_error(session, "MALFORMED", str(error))
                return
            check = validate_message(message, first_message=True)
            if not check.accepted or message.get("type") != "hello":
                await session.send(command_rejected_message(check.code, check.message))
                return
            session.client_name = message["client_name"]
            async for raw in websocket:
                try:
                    decoded = self.decode(raw)
                except (ValueError, UnicodeError, json.JSONDecodeError) as error:
                    await self.send_error(session, "MALFORMED", str(error))
                    continue
                await self.handle_message(session, decoded)
        except ConnectionClosed:
            LOGGER.info("connection %s closed normally", connection_id)
        except Exception:
            LOGGER.exception("unexpected transport error for connection %s", connection_id)
        finally:
            await self.disconnect(session)

    @staticmethod
    async def send_error(session: PlayerSession, code: str, message: str) -> None:
        """Send a structured non-mutating transport error when possible."""

        if session.send is not None and session.connected:
            try:
                await session.send({"version": 1, "type": "error", "code": code, "message": message})
            except Exception:
                LOGGER.debug("unable to send error for connection %s", session.connection_id, exc_info=True)

    @staticmethod
    def decode(raw: str | bytes) -> dict[str, Any]:
        """Decode one bounded UTF-8 JSON object or raise a protocol error."""

        encoded = raw if isinstance(raw, bytes) else raw.encode("utf-8")
        if len(encoded) > MAX_MESSAGE_BYTES:
            raise ValueError("TOO_LARGE")
        message = json.loads(encoded.decode("utf-8"))
        if not isinstance(message, dict):
            raise ValueError("MALFORMED")
        return message

    async def handle_message(self, session: PlayerSession, message: dict[str, Any]) -> None:
        """Validate and route one client message to lobby control or tick intake."""

        last_seq = session.last_gameplay_seq
        check = validate_message(message, last_gameplay_seq=last_seq)
        if not check.accepted:
            await session.send(command_rejected_message(check.code, check.message))
            return
        message_type = message["type"]
        if message_type in {"move_start", "move_stop", "attack"}:
            session.last_gameplay_seq = message["seq"]
            if session.lobby is None:
                await session.send(command_rejected_message("BAD_PHASE", "join a lobby first", seq=message["seq"]))
                return
            self.receive_ordinal += 1
            session.lobby.enqueue(QueuedCommand(self.receive_ordinal, session, message))
            return
        if message_type == "create_lobby":
            await self.create_lobby(session, message)
        elif message_type == "join_lobby":
            await self.join_lobby(session, message)
        elif message_type == "ready":
            await self.ready(session, message)
        elif message_type == "host_config":
            await self.host_config(session, message)
        elif message_type == "start_match":
            await self.start_match(session, message)
        elif message_type == "leave":
            await self.disconnect(session)
        else:
            await session.send(command_rejected_message("UNKNOWN_REQUEST", "unsupported message type"))

    async def create_lobby(self, session: PlayerSession, message: dict[str, Any]) -> None:
        """Create a lobby and make the requesting connection its host."""

        if session.lobby is not None:
            await session.send(command_rejected_message("BAD_PHASE", "already joined a lobby", request_id=message.get("request_id")))
            return
        join_code = self.new_join_code()
        lobby = LobbyRuntime(join_code)
        session.is_host = True
        session.player_id = "p1"
        lobby.add_session(session, COLORS[0])
        session.lobby = lobby
        self.lobbies[join_code] = lobby
        await lobby.start()
        await session.send(self.welcome_for(session, message["request_id"]))
        await lobby.broadcast(self.lobby_state(lobby))

    async def join_lobby(self, session: PlayerSession, message: dict[str, Any]) -> None:
        """Join an existing lobby by its six-character code."""

        lobby = self.lobbies.get(message.get("join_code", ""))
        if lobby is None:
            await session.send(command_rejected_message("INVALID_VALUE", "unknown join code", request_id=message.get("request_id")))
            return
        if session.lobby is not None:
            await session.send(command_rejected_message("BAD_PHASE", "already joined a lobby", request_id=message.get("request_id")))
            return
        session.player_id = f"p{len(lobby.sessions) + 1}"
        try:
            lobby.add_session(session, COLORS[len(lobby.sessions)])
        except ValueError as error:
            await session.send(command_rejected_message(str(error), str(error), request_id=message.get("request_id")))
            return
        session.lobby = lobby
        await session.send(self.welcome_for(session, message["request_id"]))
        await lobby.broadcast(self.lobby_state(lobby))

    async def ready(self, session: PlayerSession, message: dict[str, Any]) -> None:
        """Set readiness in setup without changing simulation authority."""

        if session.lobby is None or session.lobby.simulation.state.phase.value != "setup":
            await session.send(command_rejected_message("BAD_PHASE", "ready is only valid in setup", request_id=message.get("request_id")))
            return
        session.ready = bool(message["ready"])
        session.lobby.simulation.state.players[session.player_id].ready = session.ready
        await session.lobby.broadcast(self.lobby_state(session.lobby))

    async def host_config(self, session: PlayerSession, message: dict[str, Any]) -> None:
        """Apply host-only setup through the existing Simulation lifecycle."""

        lobby = session.lobby
        if lobby is None or not session.is_host:
            await session.send(command_rejected_message("NOT_HOST", "only the host may configure", request_id=message.get("request_id")))
            return
        try:
            if lobby.simulation.state.phase.value == "lobby":
                lobby.simulation.step([self.lifecycle_command(session, "start_setup")])
            lobby.simulation.configure_match(
                rounds=message["rounds"],
                turn_seconds=message["turn_seconds"],
                requester_id=session.player_id,
            )
        except (ValueError, PermissionError) as error:
            await session.send(command_rejected_message("INVALID_VALUE", str(error), request_id=message.get("request_id")))
            return
        await lobby.broadcast(self.lobby_state(lobby))

    async def start_match(self, session: PlayerSession, message: dict[str, Any]) -> None:
        """Start only when the host requests it and every player is ready."""

        lobby = session.lobby
        if lobby is None or not session.is_host:
            await session.send(command_rejected_message("NOT_HOST", "only the host may start", request_id=message.get("request_id")))
            return
        if not all(player.ready for player in lobby.sessions.values()):
            await session.send(command_rejected_message("BAD_PHASE", "all players must be ready", request_id=message.get("request_id")))
            return
        lobby.simulation.step([self.lifecycle_command(session, "start_match")])
        await lobby.broadcast(lobby.snapshot_message())

    @staticmethod
    def lifecycle_command(session: PlayerSession, command_type: str):
        """Build an internal lifecycle command for the authoritative Simulation."""

        return __import__("simulation.commands", fromlist=["Command"]).Command(
            __import__("simulation.commands", fromlist=["CommandType"]).CommandType(command_type),
            0,
            0,
            session.player_id,
        )

    async def disconnect(self, session: PlayerSession) -> None:
        """Apply host-terminal or non-host turn-removal policy."""

        if not session.connected:
            return
        session.connected = False
        lobby = session.lobby
        if lobby is None:
            self.sessions.pop(session.connection_id, None)
            return
        if session.is_host:
            lobby.simulation.step([self.lifecycle_command(session, "host_disconnect")])
            await lobby.broadcast({"version": 1, "type": "host_disconnected", "reason": "host_disconnected"})
            await lobby.stop()
        else:
            player = lobby.simulation.state.players.get(session.player_id)
            if player is not None:
                player.connected = False
            if lobby.simulation.state.turn.active_player_id != session.player_id:
                lobby.sessions.pop(session.connection_id, None)

    @staticmethod
    def welcome_for(session: PlayerSession, request_id: str) -> dict[str, Any]:
        """Build an identity-bearing welcome event."""

        return {
            "version": 1,
            "type": "welcome",
            "request_id": request_id,
            "connection_id": session.connection_id,
            "player_id": session.player_id,
            "is_host": session.is_host,
        }

    @staticmethod
    def lobby_state(lobby: LobbyRuntime) -> dict[str, Any]:
        """Serialize lobby roster and readiness."""

        state = lobby.simulation.state
        players = [
            {"id": session.player_id, "name": session.client_name, "color": state.players[session.player_id].color, "ready": session.ready}
            for session in lobby.sessions.values()
        ]
        all_ready = bool(players) and all(player["ready"] for player in players)
        return {
            "version": 1,
            "type": "lobby_state",
            "join_code": lobby.join_code,
            "phase": state.phase.value,
            "host_id": state.host_player_id or "",
            "players": players,
            "player_count": len(players),
            "connected_count": len(players),
            "max_players": state.config.max_players,
            "configured_rounds": state.configured_rounds,
            "turn_seconds": state.turn_duration_seconds,
            "all_ready": all_ready,
            "can_start": state.phase.value == "setup" and all_ready,
        }

    def new_join_code(self) -> str:
        """Return a unique join code for this server process."""

        code = generate_join_code()
        while code in self.lobbies:
            code = generate_join_code()
        return code


async def static_process_request(connection: Any, request: Any, client_root: Path):
    """Serve minimal client files through the same WebSocket process."""

    def http_response(status: int, headers: list[tuple[str, str]], body: bytes):
        """Return the response shape expected by the installed websockets API."""

        if Response is None or Headers is None:
            return status, headers, body
        response_headers = Headers()
        for name, value in headers:
            response_headers[name] = value
        reason = {200: "OK", 403: "Forbidden", 404: "Not Found"}.get(status, "Error")
        return Response(status, reason, response_headers, body)

    # websockets >=14 passes (connection, Request); websockets 13's legacy
    # server passes (path, request_headers). Support both explicitly.
    path = getattr(request, "path", connection if isinstance(connection, str) else "/")
    relative = path.split("?", 1)[0].lstrip("/") or "index.html"
    if relative == "ws":
        return None
    candidate = (client_root / relative).resolve()
    if client_root.resolve() not in candidate.parents and candidate != client_root.resolve():
        return http_response(403, [], b"Forbidden")
    if not candidate.is_file():
        return http_response(404, [], b"Not found")
    content_types = {
        ".html": "text/html; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
    }
    content_type = content_types.get(candidate.suffix, "application/octet-stream")
    return http_response(200, [("Content-Type", content_type)], candidate.read_bytes())
