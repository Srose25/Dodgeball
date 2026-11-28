"""SP-7 server/lobby tests that avoid sockets and browser dependencies."""

import asyncio
from pathlib import Path
import unittest

from server.lobby import LobbyRuntime, PlayerSession, QueuedCommand, generate_join_code
from server.transport import GameServer, static_process_request
from simulation.commands import CommandType


class LobbyTests(unittest.TestCase):
    """Verify lobby admission and fixed-tick command synchronization."""

    def test_join_codes_are_six_character_uppercase_values(self) -> None:
        """Generated LAN codes satisfy the approved shape."""

        code = generate_join_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isupper())
        self.assertTrue(code.isalnum())

    def test_lobby_caps_at_four_players(self) -> None:
        """The fifth player is rejected before simulation mutation."""

        lobby = LobbyRuntime("ABC234")
        for index in range(4):
            session = PlayerSession(f"c{index}", f"p{index + 1}", f"client-{index}")
            lobby.add_session(session, ("red", "blue", "green", "yellow")[index])
        with self.assertRaisesRegex(ValueError, "CAPACITY_FULL"):
            lobby.add_session(PlayerSession("c4", "p5", "client-4"), "white")
        self.assertEqual(len(lobby.simulation.state.players), 4)

    def test_queued_gameplay_uses_server_receive_order(self) -> None:
        """Queued intents are applied through Simulation in deterministic order."""

        lobby = LobbyRuntime("ABC234")
        host = PlayerSession("c1", "p1", "host", is_host=True)
        guest = PlayerSession("c2", "p2", "guest")
        lobby.add_session(host, "red")
        lobby.add_session(guest, "blue")
        lobby.simulation.step(
            [
                __import__("simulation.commands", fromlist=["Command"]).Command(
                    CommandType.START_SETUP, 0, 0, "p1"
                )
            ]
        )
        lobby.simulation.configure_match(requester_id="p1")
        lobby.simulation.step(
            [
                __import__("simulation.commands", fromlist=["Command"]).Command(
                    CommandType.START_MATCH, 0, 0, "p1"
                )
            ]
        )
        lobby.enqueue(QueuedCommand(2, host, {"type": "move_start", "seq": 2, "direction": "right"}))
        lobby.enqueue(QueuedCommand(1, host, {"type": "move_stop", "seq": 1, "direction": "right"}))
        lobby.tick_once()
        self.assertEqual(lobby.simulation.state.last_command_results[0].code, "accepted")
        self.assertEqual(lobby.simulation.state.last_command_results[1].code, "accepted")

    def test_tick_task_starts_and_stops(self) -> None:
        """The lobby runtime owns a cancellable fixed-rate task."""

        async def scenario() -> None:
            lobby = LobbyRuntime("ABC234")
            await lobby.start()
            await asyncio.sleep(0.01)
            self.assertIsNotNone(lobby._tick_task)
            await lobby.stop()
            self.assertIsNone(lobby._tick_task)

        asyncio.run(scenario())

    def test_static_paths_and_ws_passthrough(self) -> None:
        """Static files are served while /ws remains available for upgrading."""

        async def scenario() -> None:
            root = Path(__file__).parents[2] / "client"
            index = await static_process_request("/", object(), root)
            websocket = await static_process_request("/ws", object(), root)
            missing = await static_process_request("/missing.file", object(), root)
            self.assertIsNotNone(index)
            self.assertIsNone(websocket)
            self.assertIsNotNone(missing)
            if isinstance(index, tuple):
                self.assertEqual(index[0], 200)
                self.assertIn(b"Dodgeball LAN", index[2])
                self.assertEqual(missing[0], 404)
            else:
                self.assertEqual(index.status_code, 200)
                self.assertEqual(missing.status_code, 404)

        asyncio.run(scenario())

    def test_legacy_and_modern_request_shapes_route_ws(self) -> None:
        """Both supported websockets callback shapes preserve the upgrade path."""

        class Request:
            path = "/ws?version=1"

        async def scenario() -> None:
            root = Path(__file__).parents[2] / "client"
            self.assertIsNone(await static_process_request("/ws?version=1", object(), root))
            self.assertIsNone(await static_process_request(object(), Request(), root))

        asyncio.run(scenario())

    def test_create_and_join_send_one_definitive_welcome_each(self) -> None:
        """Lobby actions, not hello, establish the definitive player identity."""

        async def scenario() -> None:
            server = GameServer()
            host_messages: list[dict] = []
            guest_messages: list[dict] = []
            host = PlayerSession("c1", "temp", "host", send=host_messages.append)
            guest = PlayerSession("c2", "temp", "guest", send=guest_messages.append)
            host.send = async_send(host_messages)
            guest.send = async_send(guest_messages)
            await server.create_lobby(host, {"request_id": "create-1"})
            code = next(iter(server.lobbies))
            await server.join_lobby(guest, {"request_id": "join-1", "join_code": code})
            self.assertEqual([message["type"] for message in host_messages].count("welcome"), 1)
            self.assertEqual([message["type"] for message in guest_messages].count("welcome"), 1)
            host_state = next(message for message in host_messages if message["type"] == "lobby_state")
            self.assertEqual(host_state["phase"], "lobby")
            self.assertEqual(host_state["player_count"], 2)
            self.assertEqual(host_state["max_players"], 4)
            self.assertFalse(host_state["can_start"])
            self.assertEqual(host_state["configured_rounds"], 1)
            self.assertEqual(host_state["turn_seconds"], 30)
            await server.disconnect(host)
            await server.disconnect(guest)

    def test_pre_match_gameplay_is_rejected_and_ready_start_enters_active_turn(self) -> None:
        """Gameplay remains blocked until host setup and all players are ready."""

        async def scenario() -> None:
            server = GameServer()
            host_messages: list[dict] = []
            guest_messages: list[dict] = []
            host = PlayerSession("c1", "p1", "host", is_host=True, send=async_send(host_messages))
            guest = PlayerSession("c2", "p2", "guest", send=async_send(guest_messages))
            await server.create_lobby(host, {"request_id": "create-1"})
            code = next(iter(server.lobbies))
            await server.join_lobby(guest, {"request_id": "join-1", "join_code": code})
            lobby = server.lobbies[code]

            await server.handle_message(host, {"version": 1, "type": "move_start", "seq": 1, "direction": "right"})
            lobby.tick_once()
            await asyncio.sleep(0)
            rejection = next(message for message in reversed(host_messages) if message["type"] == "command_rejected")
            self.assertEqual(rejection["code"], "OUT_OF_TURN")
            self.assertEqual(lobby.simulation.state.phase.value, "lobby")

            await server.host_config(host, {"request_id": "config-1", "rounds": 1, "turn_seconds": 30})
            await server.ready(host, {"request_id": "ready-1", "ready": True})
            await server.ready(guest, {"request_id": "ready-2", "ready": True})
            await server.start_match(host, {"request_id": "start-1"})
            self.assertEqual(lobby.simulation.state.phase.value, "active_turn")
            self.assertEqual(lobby.simulation.state.turn.active_player_id, "p1")
            self.assertEqual(host_messages[-1]["type"], "state_snapshot")
            await server.disconnect(host)
            await server.disconnect(guest)

        asyncio.run(scenario())

    def test_handler_runs_hello_create_lobby_flow(self) -> None:
        """The transport accepts hello, then creates a lobby without duplicate welcomes."""

        class FakeWebSocket:
            def __init__(self) -> None:
                self.sent: list[dict] = []
                self.incoming = [
                    '{"version":1,"type":"hello","request_id":"hello-1","client_name":"Host"}',
                    '{"version":1,"type":"create_lobby","request_id":"create-1"}',
                ]

            async def recv(self):
                return self.incoming.pop(0)

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.incoming:
                    return self.incoming.pop(0)
                raise StopAsyncIteration

            async def send(self, payload: str) -> None:
                import json

                self.sent.append(json.loads(payload))

        async def scenario() -> None:
            server = GameServer()
            websocket = FakeWebSocket()
            await server.handler(websocket)
            self.assertEqual([message["type"] for message in websocket.sent].count("welcome"), 1)
            self.assertIn("lobby_state", [message["type"] for message in websocket.sent])

        asyncio.run(scenario())


def async_send(messages: list[dict]):
    """Return an async test sender matching a WebSocket session callback."""

    async def send(message: dict) -> None:
        messages.append(message)

    return send


if __name__ == "__main__":
    unittest.main()
