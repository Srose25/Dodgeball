"""Run a tiny deterministic local simulation smoke check."""

from .commands import Command, CommandType, MoveDirection, attack_command
from .engine import Simulation
from .physics import Vec2


def main() -> None:
    """Run three lifecycle ticks and print their read-only summaries."""

    simulation = Simulation()
    simulation.add_player("p1", "red")
    simulation.add_player("p2", "blue")
    simulation.add_ball("ball-1", Vec2(1261.5, 360), Vec2(100, 0))
    simulation.step([Command(CommandType.START_SETUP, 1, 1, "p1")])
    simulation.configure_match(rounds=1, turn_seconds=30, requester_id="p1")
    print(simulation.step([Command(CommandType.START_MATCH, 2, 2, "p1")]))
    print(
        simulation.step(
            [Command(CommandType.MOVE_START, 3, 3, "p1", MoveDirection.RIGHT)]
        )
    )
    print(
        simulation.step(
            [Command(CommandType.MOVE_STOP, 4, 4, "p1", MoveDirection.RIGHT)]
        )
    )
    print(simulation.step([attack_command(5, 5, "p1")]))
    simulation.state.players["p1"].round_score = 10
    simulation.state.players["p2"].round_score = 2
    simulation.state.turn.end_tick = simulation.state.tick + 1
    print(simulation.step())
    simulation.state.turn.end_tick = simulation.state.tick + 1
    print(simulation.step())
    print(simulation.state.balls["ball-1"])
    simulation.return_to_setup()
    print(simulation.snapshot())


if __name__ == "__main__":
    main()
