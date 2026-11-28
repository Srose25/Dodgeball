"""U2-QA-001 regression coverage for lobby/setup and match-start behavior."""

import asyncio
import unittest

from server.lobby import PlayerSession
from server.transport import GameServer
from simulation.phases import GamePhase


def async_messages(messages: list[dict]):
    """Return an async sender that records protocol messages."""

    async def send(message: dict) -> None:
        messages.append(message)

    return send


class U2LobbySetupTests(unittest.TestCase):
    """Verify the authoritative setup gate before browser gameplay begins."""

    async def make_lobby(self) -> tuple[GameServer, PlayerSession, PlayerSession, str, list[dict], list[dict]]:
        """Create a host and guest session through the transport boundary."""

        server = GameServer()
        host_messages: list[dict] = []
        guest_messages: list[dict] = []
        host = PlayerSession("c1", "temp", "Host", send=async_messages(host_messages))
        guest = PlayerSession("c2", "temp", "Guest", send=async_messages(guest_messages))
        await server.create_lobby(host, {"request_id": "create-1"})
        code = next(iter(server.lobbies))
        await server.join_lobby(guest, {"request_id": "join-1", "join_code": code})
        return server, host, guest, code, host_messages, guest_messages

    def test_create_and_join_remain_in_lobby_setup_with_shared_roster(self) -> None:
        """U2-QA-001: create/join never becomes gameplay and roster reaches both clients."""

        async def scenario() -> None:
            server, host, guest, _code, host_messages, guest_messages = await self.make_lobby()
            lobby = host.lobby
            self.assertIsNotNone(lobby)
            self.assertEqual(lobby.simulation.state.phase, GamePhase.LOBBY)
            self.assertEqual(len(lobby.sessions), 2)
            for messages in (host_messages, guest_messages):
                states = [message for message in messages if message["type"] == "lobby_state"]
                self.assertTrue(states)
                self.assertEqual(len(states[-1]["players"]), 2)
            await server.disconnect(host)
            await server.disconnect(guest)

        asyncio.run(scenario())

    def test_lobby_state_exposes_u2_setup_status_and_configuration(self) -> None:
        """U2-QA-001: setup clients need phase, count, configuration, and readiness data."""

        async def scenario() -> None:
            server, host, guest, _code, _host_messages, _guest_messages = await self.make_lobby()
            state = server.lobby_state(host.lobby)
            self.assertEqual(state["phase"], "lobby")
            self.assertEqual(state["connected_count"], 2)
            self.assertEqual(state["max_players"], 4)
            self.assertIn("configured_rounds", state)
            self.assertIn("turn_seconds", state)
            self.assertIn("all_ready", state)
            await server.disconnect(host)
            await server.disconnect(guest)

        asyncio.run(scenario())

    def test_ready_and_host_configuration_propagate_before_start(self) -> None:
        """U2-QA-001: readiness and host configuration are visible before gameplay."""

        async def scenario() -> None:
            server, host, guest, _code, host_messages, guest_messages = await self.make_lobby()
            await server.host_config(host, {"request_id": "config-1", "rounds": 3, "turn_seconds": 45})
            await server.ready(guest, {"request_id": "ready-1", "ready": True})
            self.assertEqual(host.lobby.simulation.state.phase, GamePhase.SETUP)
            self.assertEqual(host.lobby.simulation.state.configured_rounds, 3)
            self.assertEqual(host.lobby.simulation.state.turn_duration_seconds, 45)
            for messages in (host_messages, guest_messages):
                state = [message for message in messages if message["type"] == "lobby_state"][-1]
                self.assertTrue(state["players"][-1]["ready"])
                self.assertEqual(state["configured_rounds"], 3)
                self.assertEqual(state["turn_seconds"], 45)
            await server.disconnect(host)
            await server.disconnect(guest)

        asyncio.run(scenario())

    def test_pre_match_gameplay_commands_are_rejected_without_mutation(self) -> None:
        """U2-QA-001: movement and attack cannot act during lobby/setup."""

        async def scenario() -> None:
            server, host, guest, _code, _host_messages, _guest_messages = await self.make_lobby()
            lobby = host.lobby
            lobby.simulation.state.players["p1"].position_x = 400.0
            lobby.simulation.state.players["p2"].position_x = 880.0
            before = lobby.simulation.snapshot()
            await server.handle_message(host, {"version": 1, "type": "move_start", "seq": 1, "direction": "right"})
            await server.handle_message(host, {"version": 1, "type": "attack", "seq": 2})
            lobby.tick_once()
            after = lobby.simulation.snapshot()
            self.assertEqual(after.phase, GamePhase.LOBBY)
            self.assertEqual(after.player_positions_x, before.player_positions_x)
            self.assertTrue(all(not result.accepted for result in lobby.simulation.state.last_command_results))
            await server.disconnect(host)
            await server.disconnect(guest)

        asyncio.run(scenario())

    def test_start_is_blocked_until_ready_then_enters_active_turn(self) -> None:
        """U2-QA-001: invalid start is rejected; valid ready start enters gameplay."""

        async def scenario() -> None:
            server, host, guest, _code, host_messages, _guest_messages = await self.make_lobby()
            await server.host_config(host, {"request_id": "config-1", "rounds": 1, "turn_seconds": 30})
            await server.start_match(host, {"request_id": "start-1"})
            self.assertEqual(host_messages[-1]["type"], "command_rejected")
            self.assertEqual(host.lobby.simulation.state.phase, GamePhase.SETUP)
            await server.ready(host, {"request_id": "ready-host", "ready": True})
            await server.ready(guest, {"request_id": "ready-guest", "ready": True})
            await server.start_match(host, {"request_id": "start-2"})
            self.assertEqual(host.lobby.simulation.state.phase, GamePhase.ACTIVE_TURN)
            self.assertTrue(any(message["type"] == "state_snapshot" for message in host_messages))
            await server.disconnect(host)
            await server.disconnect(guest)

        asyncio.run(scenario())

    def test_late_join_is_rejected_after_match_start(self) -> None:
        """U2-QA-001: a new player cannot bypass setup after gameplay begins."""

        async def scenario() -> None:
            server, host, guest, code, _host_messages, _guest_messages = await self.make_lobby()
            await server.host_config(host, {"request_id": "config-1", "rounds": 1, "turn_seconds": 30})
            await server.ready(host, {"request_id": "ready-host", "ready": True})
            await server.ready(guest, {"request_id": "ready-guest", "ready": True})
            await server.start_match(host, {"request_id": "start-1"})
            late_messages: list[dict] = []
            late = PlayerSession("c3", "temp", "Late", send=async_messages(late_messages))
            await server.join_lobby(late, {"request_id": "join-late", "join_code": code})
            self.assertEqual(late_messages[-1]["type"], "command_rejected")
            self.assertEqual(late_messages[-1]["code"], "LATE_JOIN")
            await server.disconnect(host)
            await server.disconnect(guest)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
