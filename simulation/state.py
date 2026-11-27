"""Typed authoritative state contracts and immutable snapshots."""

from dataclasses import dataclass, field

from .commands import CommandResult, MoveDirection
from .config import SimulationConfig
from .phases import GamePhase


@dataclass(slots=True)
class StageState:
    """Fixed logical stage dimensions used by the simulation."""

    width: float
    height: float


@dataclass(slots=True)
class DodgeballState:
    """Authoritative dodgeball transform and contact epoch state."""

    ball_id: str
    position_x: float
    position_y: float
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    visible_radius: float = 14.0
    collision_radius: float = 18.0
    contact_epoch: int = 0
    valid_contact_count: int = 0


@dataclass(slots=True)
class PlayerState:
    """Authoritative player contract for local movement and future gameplay."""

    player_id: str
    color: str
    connected: bool = True
    ready: bool = False
    damage: int = 0
    round_score: int = 0
    round_wins: int = 0
    position_x: float = 0.0
    position_y: float = 0.0
    velocity_x: float = 0.0
    held_left: bool = False
    held_right: bool = False
    facing: MoveDirection = MoveDirection.RIGHT
    attack_used: bool = False
    knockback_x: float = 0.0
    knockback_y: float = 0.0


@dataclass(slots=True)
class TurnState:
    """Authoritative timed-turn contract for the active round."""

    active_player_id: str | None = None
    start_tick: int | None = None
    end_tick: int | None = None
    order: tuple[str, ...] = ()
    completed_player_ids: tuple[str, ...] = ()
    round_number: int = 1


@dataclass(slots=True)
class MatchState:
    """Mutable authoritative state owned solely by ``Simulation``."""

    config: SimulationConfig
    phase: GamePhase = GamePhase.LOBBY
    tick: int = 0
    revision: int = 0
    stage: StageState = field(init=False)
    players: dict[str, PlayerState] = field(default_factory=dict)
    turn: TurnState = field(default_factory=TurnState)
    balls: dict[str, DodgeballState] = field(default_factory=dict)
    host_player_id: str | None = None
    configured_rounds: int = 1
    turn_duration_seconds: int = 30
    last_attack_hits: tuple[tuple[str, str], ...] = ()
    round_winners: tuple[str, ...] = ()
    round_winner_history: tuple[tuple[str, ...], ...] = ()
    match_winners: tuple[str, ...] = ()
    match_result: str | None = None
    last_command_results: tuple[CommandResult, ...] = ()

    def __post_init__(self) -> None:
        """Initialize the stage from centralized configuration."""

        self.stage = StageState(self.config.stage_width, self.config.stage_height)


@dataclass(frozen=True, slots=True)
class Snapshot:
    """Read-only state summary suitable for local checks or future transport."""

    phase: GamePhase
    tick: int
    revision: int
    stage_width: float
    stage_height: float
    player_ids: tuple[str, ...]
    player_positions_x: tuple[tuple[str, float], ...]
    player_velocities_x: tuple[tuple[str, float], ...]
    active_player_id: str | None
    turn_end_tick: int | None
    round_number: int
    ball_positions: tuple[tuple[str, float, float], ...]
    player_damage: tuple[tuple[str, int], ...]
    attack_used: tuple[tuple[str, bool], ...]
    last_attack_hits: tuple[tuple[str, str], ...]
    player_round_scores: tuple[tuple[str, int], ...]
    round_winners: tuple[str, ...]
    round_winner_history: tuple[tuple[str, ...], ...]
    match_winners: tuple[str, ...]
    match_result: str | None

    @classmethod
    def from_state(cls, state: MatchState) -> "Snapshot":
        """Create a deterministic snapshot without exposing mutable state."""

        return cls(
            phase=state.phase,
            tick=state.tick,
            revision=state.revision,
            stage_width=state.stage.width,
            stage_height=state.stage.height,
            player_ids=tuple(sorted(state.players)),
            player_positions_x=tuple(
                (player_id, state.players[player_id].position_x)
                for player_id in sorted(state.players)
            ),
            player_velocities_x=tuple(
                (player_id, state.players[player_id].velocity_x)
                for player_id in sorted(state.players)
            ),
            active_player_id=state.turn.active_player_id,
            turn_end_tick=state.turn.end_tick,
            round_number=state.turn.round_number,
            ball_positions=tuple(
                (ball_id, state.balls[ball_id].position_x, state.balls[ball_id].position_y)
                for ball_id in sorted(state.balls)
            ),
            player_damage=tuple(
                (player_id, state.players[player_id].damage)
                for player_id in sorted(state.players)
            ),
            attack_used=tuple(
                (player_id, state.players[player_id].attack_used)
                for player_id in sorted(state.players)
            ),
            last_attack_hits=state.last_attack_hits,
            player_round_scores=tuple(
                (player_id, state.players[player_id].round_score)
                for player_id in sorted(state.players)
            ),
            round_winners=state.round_winners,
            round_winner_history=state.round_winner_history,
            match_winners=state.match_winners,
            match_result=state.match_result,
        )
