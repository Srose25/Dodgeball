"""Deterministic, browser-independent game simulation components."""

from .config import SimulationConfig
from .phases import GamePhase, InvalidPhaseTransition, PhaseMachine
from .state import MatchState, Snapshot
from .engine import Simulation
from .physics import StageBounds, Vec2

__all__ = [
    "GamePhase",
    "InvalidPhaseTransition",
    "MatchState",
    "PhaseMachine",
    "Simulation",
    "SimulationConfig",
    "StageBounds",
    "Snapshot",
    "Vec2",
]
