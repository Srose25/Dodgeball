"""SP-7 server/lobby tests that avoid sockets and browser dependencies."""

import asyncio
import unittest

from server.lobby import LobbyRuntime, PlayerSession, QueuedCommand, generate_join_code
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


if __name__ == "__main__":
    unittest.main()
