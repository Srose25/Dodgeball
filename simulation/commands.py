"""Typed local command contracts and deterministic command intake."""

from dataclasses import dataclass
from enum import StrEnum


class CommandType(StrEnum):
    """Commands understood by the local lifecycle and movement shell."""

    START_SETUP = "start_setup"
    START_MATCH = "start_match"
    MOVE_START = "move_start"
    MOVE_STOP = "move_stop"
    ATTACK = "attack"
    CLOSE = "close"
    HOST_DISCONNECT = "host_disconnect"


class MoveDirection(StrEnum):
    """Horizontal movement intents accepted by the simulation."""

    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class Command:
    """A deterministic local intent with transport-like ordering metadata."""

    command_type: CommandType
    receive_ordinal: int
    client_sequence: int
    player_id: str | None = None
    direction: MoveDirection | None = None


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result of handling one command, including non-mutating rejection detail."""

    accepted: bool
    code: str
    message: str


def order_commands(commands: list[Command]) -> list[Command]:
    """Return commands in stable server-receive then client-sequence order."""

    return sorted(
        commands,
        key=lambda command: (command.receive_ordinal, command.client_sequence),
    )


def direction_for_key(key: str) -> MoveDirection | None:
    """Map an A/D or arrow key name to a horizontal movement direction."""

    return {
        "a": MoveDirection.LEFT,
        "arrowleft": MoveDirection.LEFT,
        "d": MoveDirection.RIGHT,
        "arrowright": MoveDirection.RIGHT,
    }.get(key.lower())


def movement_command(
    key: str,
    pressed: bool,
    receive_ordinal: int,
    client_sequence: int,
    player_id: str,
) -> Command | None:
    """Create a movement intent for a recognized key, or return ``None``."""

    direction = direction_for_key(key)
    if direction is None:
        return None
    command_type = CommandType.MOVE_START if pressed else CommandType.MOVE_STOP
    return Command(command_type, receive_ordinal, client_sequence, player_id, direction)


def attack_command(receive_ordinal: int, client_sequence: int, player_id: str) -> Command:
    """Create the discrete E-key attack intent."""

    return Command(CommandType.ATTACK, receive_ordinal, client_sequence, player_id)
