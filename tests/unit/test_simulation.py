"""Focused SP-1 and SP-2 tests for deterministic local simulation behavior."""

import math
import unittest

from simulation.commands import (
    Command,
    CommandType,
    MoveDirection,
    attack_command,
    direction_for_key,
    movement_command,
)
from simulation.config import SimulationConfig
from simulation.engine import Simulation
from simulation.phases import GamePhase, InvalidPhaseTransition, PhaseMachine
from simulation.physics import Vec2


class SimulationTests(unittest.TestCase):
    """Verify local lifecycle, movement, and timed-turn acceptance criteria."""

    def _active_simulation(
        self,
        player_ids: tuple[str, ...] = ("p1", "p2"),
        rounds: int = 1,
    ) -> Simulation:
        """Create a local simulation with players and the first active turn."""

        simulation = Simulation()
        for index, player_id in enumerate(player_ids):
            simulation.add_player(player_id, f"color-{index}")
        host_player_id = player_ids[0]
        simulation.step([Command(CommandType.START_SETUP, 1, 1, host_player_id)])
        simulation.configure_match(
            rounds=rounds, turn_seconds=30, requester_id=host_player_id
        )
        simulation.step([Command(CommandType.START_MATCH, 2, 2, host_player_id)])
        return simulation

    def test_fixed_step_advances_tick_and_revision(self) -> None:
        """Each call advances exactly one deterministic simulation tick."""

        simulation = Simulation()
        self.assertEqual((simulation.state.tick, simulation.state.revision), (0, 0))
        simulation.step()
        self.assertEqual((simulation.state.tick, simulation.state.revision), (1, 1))

    def test_replay_is_identical(self) -> None:
        """The same initial state and command sequence produce equal snapshots."""

        first = self._active_simulation()
        second = self._active_simulation()
        commands = [
            Command(CommandType.MOVE_START, 3, 3, "p1", MoveDirection.RIGHT),
            Command(CommandType.MOVE_STOP, 4, 4, "p1", MoveDirection.RIGHT),
        ]
        first_results = [first.step(commands[:1]), first.step(commands[1:])]
        second_results = [second.step(commands[:1]), second.step(commands[1:])]
        self.assertEqual(first_results, second_results)

    def test_commands_are_ordered_by_receive_then_sequence(self) -> None:
        """Input order cannot override the server ordering contract."""

        simulation = Simulation()
        simulation.add_player("p1", "red")
        snapshot = simulation.step(
            [
                Command(CommandType.START_MATCH, 1, 1, "p1"),
                Command(CommandType.START_SETUP, 2, 2, "p1"),
            ]
        )
        self.assertEqual(snapshot.phase, GamePhase.SETUP)
        self.assertEqual(simulation.state.last_command_results[0].code, "no_players")

    def test_invalid_transition_does_not_mutate(self) -> None:
        """Rejected transitions leave the phase unchanged."""

        machine = PhaseMachine()
        with self.assertRaises(InvalidPhaseTransition):
            machine.transition(GamePhase.ACTIVE_TURN)
        self.assertEqual(machine.current, GamePhase.LOBBY)

    def test_stale_gameplay_command_does_not_mutate(self) -> None:
        """A duplicate gameplay sequence is rejected without movement mutation."""

        simulation = Simulation()
        simulation.add_player("local", "red")
        simulation.step([Command(CommandType.START_SETUP, 1, 4, "local")])
        simulation.step([Command(CommandType.START_MATCH, 2, 4, "local")])
        simulation.step([Command(CommandType.MOVE_START, 3, 1, "local", MoveDirection.RIGHT)])
        simulation.step([Command(CommandType.MOVE_STOP, 4, 2, "local", MoveDirection.RIGHT)])
        before = simulation.snapshot()
        simulation.step([Command(CommandType.MOVE_START, 5, 1, "local", MoveDirection.RIGHT)])
        self.assertEqual(simulation.state.last_command_results[0].code, "stale_sequence")
        self.assertEqual(simulation.snapshot().player_positions_x, before.player_positions_x)

    def test_malformed_command_does_not_mutate(self) -> None:
        """Negative command metadata is rejected without a phase change."""

        simulation = Simulation()
        before = simulation.snapshot()
        simulation.step([Command(CommandType.START_SETUP, -1, 0, "local")])
        self.assertEqual(simulation.state.last_command_results[0].code, "invalid_metadata")
        self.assertEqual(simulation.snapshot().phase, before.phase)

    def test_config_is_centralized(self) -> None:
        """The stage and tick contract come from the supplied configuration."""

        config = SimulationConfig(stage_width=1000.0, stage_height=500.0, tick_rate=60)
        snapshot = Simulation(config).snapshot()
        self.assertEqual((snapshot.stage_width, snapshot.stage_height), (1000.0, 500.0))

    def test_config_rejects_invalid_tick_rate_and_dimensions(self) -> None:
        """Zero, negative, non-finite, and non-integral settings fail early."""

        invalid_configs = (
            {"tick_rate": 0},
            {"tick_rate": -60},
            {"tick_rate": 60.5},
            {"stage_width": 0},
            {"stage_height": -1},
            {"stage_width": math.inf},
            {"stage_height": math.nan},
        )
        for overrides in invalid_configs:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    SimulationConfig(**overrides)

    def test_malformed_command_entries_do_not_mutate_state(self) -> None:
        """None and wrong-shaped entries are rejected without partial mutation."""

        simulation = Simulation()
        before = simulation.snapshot()
        result = simulation.step([None, {"command_type": "start_setup"}])  # type: ignore[list-item]
        self.assertTrue(all(not item.accepted for item in simulation.state.last_command_results))
        self.assertEqual(simulation.snapshot().phase, before.phase)
        self.assertEqual(result.phase, GamePhase.LOBBY)

    def test_malformed_command_batch_does_not_raise(self) -> None:
        """A malformed batch container returns a rejection instead of raising."""

        simulation = Simulation()
        simulation.step(None)  # type: ignore[arg-type]
        self.assertEqual(simulation.state.last_command_results[0].code, "malformed_batch")
        self.assertEqual(simulation.snapshot().phase, GamePhase.LOBBY)

    def test_key_mapping_and_command_factory(self) -> None:
        """A/D and arrow keys produce explicit left/right movement intents."""

        self.assertEqual(direction_for_key("a"), MoveDirection.LEFT)
        self.assertEqual(direction_for_key("ArrowRight"), MoveDirection.RIGHT)
        self.assertIsNone(direction_for_key("e"))
        command = movement_command("d", True, 1, 1, "p1")
        self.assertIsNotNone(command)
        self.assertEqual(command.direction, MoveDirection.RIGHT)
        self.assertEqual(command.command_type, CommandType.MOVE_START)

    def test_active_player_moves_continuously_and_releases(self) -> None:
        """Held movement accelerates, while releasing decelerates deterministically."""

        simulation = self._active_simulation()
        initial_x = simulation.state.players["p1"].position_x
        simulation.step([Command(CommandType.MOVE_START, 3, 3, "p1", MoveDirection.RIGHT)])
        for sequence in range(4, 10):
            simulation.step([Command(CommandType.MOVE_START, sequence, sequence, "p1", MoveDirection.RIGHT)])
        moving_player = simulation.state.players["p1"]
        self.assertGreater(moving_player.position_x, initial_x)
        self.assertGreater(moving_player.velocity_x, 0)
        speed_before_release = moving_player.velocity_x
        simulation.step([Command(CommandType.MOVE_STOP, 10, 10, "p1", MoveDirection.RIGHT)])
        self.assertLess(simulation.state.players["p1"].velocity_x, speed_before_release)

    def test_opposing_held_directions_cancel(self) -> None:
        """Holding both directions produces zero new movement acceleration."""

        simulation = self._active_simulation()
        simulation.step([Command(CommandType.MOVE_START, 3, 3, "p1", MoveDirection.RIGHT)])
        speed_before_cancel = simulation.state.players["p1"].velocity_x
        simulation.step([Command(CommandType.MOVE_START, 4, 4, "p1", MoveDirection.LEFT)])
        self.assertLess(simulation.state.players["p1"].velocity_x, speed_before_cancel)
        self.assertTrue(simulation.state.players["p1"].held_left)
        self.assertTrue(simulation.state.players["p1"].held_right)

    def test_out_of_turn_and_late_movement_are_rejected(self) -> None:
        """Only the active player may move, including at later turn boundaries."""

        simulation = self._active_simulation()
        p2_before = simulation.state.players["p2"].position_x
        simulation.step([Command(CommandType.MOVE_START, 3, 3, "p2", MoveDirection.LEFT)])
        self.assertEqual(simulation.state.last_command_results[0].code, "out_of_turn")
        self.assertEqual(simulation.state.players["p2"].position_x, p2_before)
        for _ in range(1799):
            simulation.step()
        simulation.step([Command(CommandType.MOVE_START, 1801, 1801, "p1", MoveDirection.RIGHT)])
        self.assertEqual(simulation.state.last_command_results[0].code, "out_of_turn")
        self.assertEqual(simulation.state.turn.active_player_id, "p2")

    def test_four_players_receive_fixed_order_and_no_input_expires(self) -> None:
        """Four connected players receive one full timed turn in sorted ID order."""

        simulation = self._active_simulation(("p4", "p2", "p3", "p1"))
        self.assertEqual(simulation.state.turn.order, ("p1", "p2", "p3", "p4"))
        self.assertEqual(simulation.state.turn.active_player_id, "p1")
        for expected_player in ("p2", "p3", "p4"):
            for _ in range(1800):
                simulation.step()
            self.assertEqual(simulation.state.turn.active_player_id, expected_player)

    def test_simulation_applies_player_clamp_and_ball_boundary_bounce(self) -> None:
        """The authoritative step keeps players boxed and bounces balls."""

        simulation = Simulation()
        simulation.add_player("p1", "red")
        simulation.add_player("p2", "blue")
        simulation.add_ball("ball-1", Vec2(1261.5, 360), Vec2(100, 0))
        simulation.step([Command(CommandType.START_SETUP, 1, 1, "p1")])
        simulation.configure_match(turn_seconds=30, requester_id="p1")
        player = simulation.state.players["p1"]
        player.position_x = 0.0
        simulation.step([Command(CommandType.START_MATCH, 2, 2, "p1")])
        self.assertEqual(player.position_x, simulation.state.config.player_radius)
        ball = simulation.state.balls["ball-1"]
        self.assertEqual(ball.position_x, 1262.0)
        self.assertEqual(ball.velocity_x, -85.0)

    def test_attack_is_active_player_only_and_once_per_turn(self) -> None:
        """An active player can attack once; out-of-turn and repeated attacks reject."""

        simulation = self._active_simulation()
        simulation.state.players["p1"].position_x = 600.0
        simulation.state.players["p2"].position_x = 660.0
        accepted = simulation.step([attack_command(3, 3, "p1")])
        self.assertEqual(accepted.last_attack_hits, (("p1", "p2"),))
        self.assertTrue(simulation.state.players["p1"].attack_used)
        repeated = simulation.step([attack_command(4, 4, "p1")])
        self.assertEqual(simulation.state.last_command_results[0].code, "attack_already_used")
        self.assertEqual(repeated.last_attack_hits, ())
        simulation.step([attack_command(5, 5, "p2")])
        self.assertEqual(simulation.state.last_command_results[0].code, "out_of_turn")

    def test_attack_hit_applies_knockback_and_respects_cap(self) -> None:
        """Attack knockback uses accumulated damage and is capped."""

        simulation = self._active_simulation()
        simulation.state.players["p1"].position_x = 600.0
        target = simulation.state.players["p2"]
        target.position_x = 660.0
        target.damage = 1000
        simulation.step([attack_command(3, 3, "p1")])
        self.assertLessEqual(abs(target.knockback_x), 520.0)
        self.assertGreater(target.knockback_x, 0.0)
        previous = target.position_x
        simulation.step()
        self.assertGreater(target.position_x, previous)

    def test_ball_damage_sequence_and_contact_deduplication(self) -> None:
        """One ball produces 100/50/25/0 on distinct contact episodes."""

        simulation = Simulation()
        simulation.add_player("p1", "red")
        simulation.add_player("p2", "blue")
        simulation.add_ball("ball-1", Vec2(700, 360))
        simulation.step([Command(CommandType.START_SETUP, 1, 1, "p1")])
        simulation.configure_match(turn_seconds=30, requester_id="p1")
        simulation.step([Command(CommandType.START_MATCH, 2, 2, "p1")])
        target = simulation.state.players["p2"]
        target.position_x = 700.0
        target.position_y = 360.0
        ball = simulation.state.balls["ball-1"]
        simulation.step()
        self.assertEqual(target.damage, 100)
        for expected_damage in (150, 175, 175):
            ball.position_x = 100.0
            simulation.step()
            ball.position_x = target.position_x
            ball.position_y = target.position_y
            simulation.step()
            self.assertEqual(target.damage, expected_damage)
        self.assertEqual(target.damage, 175)
        self.assertGreaterEqual(target.damage, 0)

    def test_simultaneous_ball_contacts_are_deterministic(self) -> None:
        """Two same-tick ball contacts resolve in stable ball-ID order."""

        simulation = Simulation()
        simulation.add_player("p1", "red")
        simulation.add_player("p2", "blue")
        simulation.add_ball("ball-b", Vec2(700, 360))
        simulation.add_ball("ball-a", Vec2(700, 360))
        simulation.step([Command(CommandType.START_SETUP, 1, 1, "p1")])
        simulation.configure_match(turn_seconds=30, requester_id="p1")
        simulation.step([Command(CommandType.START_MATCH, 2, 2, "p1")])
        simulation.state.players["p2"].position_x = 700.0
        simulation.state.players["p2"].position_y = 360.0
        simulation.step()
        self.assertEqual(simulation.state.players["p2"].damage, 200)
        self.assertEqual(
            simulation.state.balls["ball-a"].valid_contact_count,
            simulation.state.balls["ball-b"].valid_contact_count,
        )

    def test_overlapping_players_are_separated_without_damage(self) -> None:
        """Player separation resolves overlap while leaving damage non-negative."""

        simulation = self._active_simulation()
        simulation.state.players["p1"].position_x = 640.0
        simulation.state.players["p2"].position_x = 640.0
        simulation.step()
        first = simulation.state.players["p1"]
        second = simulation.state.players["p2"]
        distance = abs(first.position_x - second.position_x)
        self.assertGreaterEqual(distance, simulation.state.config.player_radius * 2)
        self.assertEqual(first.damage, 0)
        self.assertEqual(second.damage, 0)

    def _finish_turn_for_test(self, simulation: Simulation) -> None:
        """Advance one local turn at its deadline without waiting 30 seconds."""

        simulation.state.turn.end_tick = simulation.state.tick + 1
        simulation.step()

    def test_round_score_and_damage_reset_between_rounds(self) -> None:
        """A completed round records its winner and starts the next at zero."""

        simulation = self._active_simulation(rounds=2)
        simulation.state.players["p1"].round_score = 10
        simulation.state.players["p1"].damage = 40
        simulation.state.players["p2"].round_score = 2
        simulation.state.players["p2"].damage = 30
        self._finish_turn_for_test(simulation)
        self._finish_turn_for_test(simulation)
        self.assertEqual(simulation.state.round_winners, ("p1",))
        self.assertEqual(simulation.state.round_winner_history, (("p1",),))
        self.assertEqual(simulation.state.players["p1"].round_wins, 1)
        self.assertEqual(simulation.state.players["p1"].round_score, 0)
        self.assertEqual(simulation.state.players["p1"].damage, 0)
        self.assertEqual(simulation.state.players["p2"].round_score, 0)
        self.assertEqual(simulation.state.players["p2"].damage, 0)
        self.assertEqual(simulation.state.phase, GamePhase.ACTIVE_TURN)

    def test_multi_round_winner_aggregation_and_final_transition(self) -> None:
        """The player winning both rounds is the final match winner."""

        simulation = self._active_simulation(rounds=2)
        for first_score, second_score in ((10, 2), (8, 1)):
            simulation.state.players["p1"].round_score = first_score
            simulation.state.players["p2"].round_score = second_score
            self._finish_turn_for_test(simulation)
            self._finish_turn_for_test(simulation)
        self.assertEqual(simulation.state.phase, GamePhase.MATCH_RESULT)
        self.assertEqual(simulation.state.round_winner_history, (("p1",), ("p1",)))
        self.assertEqual(simulation.state.match_winners, ("p1",))
        self.assertEqual(simulation.state.match_result, "winner")
        self.assertEqual(simulation.snapshot().match_winners, ("p1",))

    def test_tied_rounds_display_all_tied_match_winners(self) -> None:
        """Equal round scores produce tied round and final match results."""

        simulation = self._active_simulation()
        simulation.state.players["p1"].round_score = 5
        simulation.state.players["p2"].round_score = 5
        self._finish_turn_for_test(simulation)
        self._finish_turn_for_test(simulation)
        self.assertEqual(simulation.state.round_winners, ("p1", "p2"))
        self.assertEqual(simulation.state.match_winners, ("p1", "p2"))
        self.assertEqual(simulation.state.match_result, "tie")

    def test_match_configuration_is_host_only(self) -> None:
        """A non-host cannot alter round count or turn duration."""

        simulation = Simulation()
        simulation.add_player("p1", "red")
        simulation.add_player("p2", "blue")
        simulation.step([Command(CommandType.START_SETUP, 1, 1, "p1")])
        with self.assertRaises(PermissionError):
            simulation.configure_match(rounds=3, requester_id="p2")
        simulation.configure_match(rounds=3, requester_id="p1")
        self.assertEqual(simulation.state.configured_rounds, 3)

    def test_return_to_setup_clears_match_persistence(self) -> None:
        """Returning to setup clears results, scores, wins, and match balls."""

        simulation = self._active_simulation()
        simulation.state.players["p1"].round_score = 10
        simulation.state.players["p2"].round_score = 1
        self._finish_turn_for_test(simulation)
        self._finish_turn_for_test(simulation)
        self.assertEqual(simulation.state.phase, GamePhase.MATCH_RESULT)
        simulation.return_to_setup()
        self.assertEqual(simulation.state.phase, GamePhase.SETUP)
        self.assertEqual(simulation.state.match_winners, ())
        self.assertEqual(simulation.state.round_winner_history, ())
        self.assertEqual(simulation.state.balls, {})
        self.assertTrue(all(player.round_wins == 0 for player in simulation.state.players.values()))
        self.assertTrue(all(player.damage == 0 for player in simulation.state.players.values()))


if __name__ == "__main__":
    unittest.main()
