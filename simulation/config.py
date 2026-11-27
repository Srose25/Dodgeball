"""Centralized simulation configuration for the v1 local shell."""

from dataclasses import dataclass
import math
from numbers import Real


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    """Immutable values shared by the deterministic simulation.

    Physics and gameplay values are intentionally provisional until their later
    stopping points. This SP-1 shell uses only the tick and stage settings.
    """

    stage_width: float = 1280.0
    stage_height: float = 720.0
    tick_rate: int = 60
    max_players: int = 4
    snapshot_rate: int = 30
    player_acceleration: float = 1800.0
    player_deceleration: float = 2400.0
    player_max_speed: float = 360.0
    turn_presets: tuple[int, ...] = (30, 45, 60, 120)
    player_radius: float = 24.0
    ball_visible_radius: float = 14.0
    ball_collision_radius: float = 18.0
    boundary_restitution: float = 0.85
    attack_reach: float = 72.0
    knockback_base_impulse: float = 220.0
    knockback_damage_factor: float = 2.0
    knockback_max_impulse: float = 520.0
    knockback_decay_seconds: float = 0.25
    ball_hit_value: int = 100

    def __post_init__(self) -> None:
        """Reject non-finite, non-positive, or structurally invalid settings."""

        for name in ("stage_width", "stage_height"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError(f"{name} must be a finite positive number")
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number")

        if isinstance(self.tick_rate, bool) or not isinstance(self.tick_rate, int):
            raise ValueError("tick_rate must be a positive integer")
        if self.tick_rate <= 0:
            raise ValueError("tick_rate must be a positive integer")

        for name in ("max_players", "snapshot_rate"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")

        for name in ("player_acceleration", "player_deceleration", "player_max_speed"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError(f"{name} must be a finite positive number")

        for name in (
            "player_radius",
            "ball_visible_radius",
            "ball_collision_radius",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError(f"{name} must be a finite positive number")
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number")

        if (
            isinstance(self.boundary_restitution, bool)
            or not isinstance(self.boundary_restitution, Real)
            or not math.isfinite(self.boundary_restitution)
            or not 0 <= self.boundary_restitution <= 1
        ):
            raise ValueError("boundary_restitution must be finite and between zero and one")

        for name in (
            "attack_reach",
            "knockback_base_impulse",
            "knockback_damage_factor",
            "knockback_max_impulse",
            "knockback_decay_seconds",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise ValueError(f"{name} must be a finite positive number")
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number")
        if isinstance(self.ball_hit_value, bool) or not isinstance(self.ball_hit_value, int):
            raise ValueError("ball_hit_value must be a non-negative integer")
        if self.ball_hit_value < 0:
            raise ValueError("ball_hit_value must be a non-negative integer")
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be a finite positive number")

        if not self.turn_presets or any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in self.turn_presets
        ):
            raise ValueError("turn_presets must contain positive integer durations")

    @property
    def tick_seconds(self) -> float:
        """Return the fixed duration of one simulation tick."""

        return 1.0 / self.tick_rate
