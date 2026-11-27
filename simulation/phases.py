"""Lifecycle phases and deterministic transition validation."""

from enum import StrEnum


class GamePhase(StrEnum):
    """Named lifecycle phases owned by the authoritative simulation."""

    LOBBY = "lobby"
    SETUP = "setup"
    TURN_START = "turn_start"
    ACTIVE_TURN = "active_turn"
    TURN_RESULT = "turn_result"
    ROUND_RESULT = "round_result"
    MATCH_RESULT = "match_result"
    HOST_DISCONNECTED = "host_disconnected"
    CLOSED = "closed"


class InvalidPhaseTransition(ValueError):
    """Raised when a requested lifecycle transition is not legal."""


_ALLOWED_TRANSITIONS: dict[GamePhase, frozenset[GamePhase]] = {
    GamePhase.LOBBY: frozenset({GamePhase.SETUP, GamePhase.HOST_DISCONNECTED}),
    GamePhase.SETUP: frozenset({GamePhase.TURN_START, GamePhase.HOST_DISCONNECTED}),
    GamePhase.TURN_START: frozenset({GamePhase.ACTIVE_TURN, GamePhase.HOST_DISCONNECTED}),
    GamePhase.ACTIVE_TURN: frozenset(
        {GamePhase.TURN_RESULT, GamePhase.HOST_DISCONNECTED}
    ),
    GamePhase.TURN_RESULT: frozenset(
        {GamePhase.TURN_START, GamePhase.ROUND_RESULT, GamePhase.HOST_DISCONNECTED}
    ),
    GamePhase.ROUND_RESULT: frozenset(
        {GamePhase.TURN_START, GamePhase.MATCH_RESULT, GamePhase.HOST_DISCONNECTED}
    ),
    GamePhase.MATCH_RESULT: frozenset({GamePhase.SETUP, GamePhase.CLOSED}),
    GamePhase.HOST_DISCONNECTED: frozenset({GamePhase.CLOSED}),
    GamePhase.CLOSED: frozenset(),
}


class PhaseMachine:
    """Validate and record lifecycle transitions without hidden state changes."""

    def __init__(self, initial: GamePhase = GamePhase.LOBBY) -> None:
        """Create a phase machine at ``initial``."""

        self._current = initial

    @property
    def current(self) -> GamePhase:
        """Return the current lifecycle phase."""

        return self._current

    def transition(self, target: GamePhase) -> None:
        """Move to ``target`` or raise without changing the current phase."""

        if target not in _ALLOWED_TRANSITIONS[self._current]:
            raise InvalidPhaseTransition(
                f"cannot transition from {self._current.value} to {target.value}"
            )
        self._current = target
