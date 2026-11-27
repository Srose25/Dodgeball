"""Authoritative LAN lobby runtime around the existing Simulation."""

from dataclasses import dataclass, field
import asyncio
import secrets
from typing import Any, Awaitable, Callable

from simulation.commands import Command, CommandType, MoveDirection
from simulation.engine import Simulation
from simulation.phases import GamePhase
from simulation.state import Snapshot

MAX_PLAYERS = 4
JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@dataclass(slots=True)
class PlayerSession:
    """Transport-neutral player connection metadata."""

    connection_id: str
    player_id: str
    client_name: str
    is_host: bool = False
    ready: bool = False
    connected: bool = True
    last_gameplay_seq: int | None = None
    send: Callable[[dict[str, Any]], Awaitable[None]] | None = None
    lobby: "LobbyRuntime | None" = None


@dataclass(slots=True)
class QueuedCommand:
    """A validated gameplay intent waiting for the next fixed tick."""

    receive_ordinal: int
    session: PlayerSession
    message: dict[str, Any]


def generate_join_code() -> str:
    """Generate a six-character uppercase LAN join code."""

    return "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(6))


@dataclass(slots=True)
class LobbyRuntime:
    """Own one authoritative Simulation and its connected LAN players."""

    join_code: str
    simulation: Simulation = field(default_factory=Simulation)
    sessions: dict[str, PlayerSession] = field(default_factory=dict)
    pending: list[QueuedCommand] = field(default_factory=list)
    _tick_task: asyncio.Task[None] | None = None
    _running: bool = False

    def add_session(self, session: PlayerSession, color: str) -> None:
        """Admit a player to the lobby or raise when the v1 cap is reached."""

        if len(self.sessions) >= MAX_PLAYERS:
            raise ValueError("CAPACITY_FULL")
        if self.simulation.state.phase is not GamePhase.LOBBY:
            raise ValueError("LATE_JOIN")
        self.sessions[session.connection_id] = session
        self.simulation.add_player(session.player_id, color)

    def enqueue(self, item: QueuedCommand) -> None:
        """Queue a validated gameplay command for the next fixed tick."""

        self.pending.append(item)

    async def start(self) -> None:
        """Start this lobby's fixed-rate simulation task."""

        if self._tick_task is None:
            self._running = True
            self._tick_task = asyncio.create_task(self._run_ticks())

    async def stop(self) -> None:
        """Stop the lobby tick task without touching external connections."""

        self._running = False
        if self._tick_task is not None:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
            self._tick_task = None

    async def _run_ticks(self) -> None:
        """Drain queued intents at 60 Hz and publish 30 Hz snapshots."""

        interval = 1.0 / self.simulation.state.config.tick_rate
        snapshot_every = max(1, self.simulation.state.config.tick_rate // 30)
        while self._running:
            started = asyncio.get_running_loop().time()
            self.tick_once()
            if self.simulation.state.tick % snapshot_every == 0:
                await self.broadcast(self.snapshot_message())
            elapsed = asyncio.get_running_loop().time() - started
            await asyncio.sleep(max(0.0, interval - elapsed))

    def tick_once(self) -> Snapshot:
        """Apply all queued commands in receive order and advance one tick."""

        queued = sorted(self.pending, key=lambda item: item.receive_ordinal)
        self.pending.clear()
        commands: list[Command] = []
        for item in queued:
            message = item.message
            command_type = CommandType(message["type"])
            direction = message.get("direction")
            commands.append(
                Command(
                    command_type=command_type,
                    receive_ordinal=item.receive_ordinal,
                    client_sequence=message["seq"],
                    player_id=item.session.player_id,
                    direction=MoveDirection(direction) if direction else None,
                )
            )
        snapshot = self.simulation.step(commands)
        for item, result in zip(queued, self.simulation.state.last_command_results):
            if not result.accepted and item.session.send is not None:
                asyncio.create_task(
                    item.session.send(
                        command_rejected_message(
                            result.code.upper(),
                            result.message,
                            seq=item.message.get("seq"),
                            request_id=item.message.get("request_id"),
                        )
                    )
                )
        return snapshot

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send one server message to all currently connected players."""

        await asyncio.gather(
            *(
                session.send(message)
                for session in self.sessions.values()
                if session.connected and session.send is not None
            ),
            return_exceptions=True,
        )

    def snapshot_message(self) -> dict[str, Any]:
        """Serialize the authoritative simulation snapshot for LAN clients."""

        snapshot = self.simulation.snapshot()
        remaining = 0
        end_tick = self.simulation.state.turn.end_tick
        if end_tick is not None:
            remaining = max(0, end_tick - snapshot.tick)
        players = []
        for player_id in snapshot.player_ids:
            player = self.simulation.state.players[player_id]
            players.append(
                {
                    "id": player_id,
                    "color": player.color,
                    "x": player.position_x,
                    "y": player.position_y,
                    "vx": player.velocity_x,
                    "damage": player.damage,
                    "score": player.round_score,
                    "attack_used": player.attack_used,
                }
            )
        balls = [
            {
                "id": ball_id,
                "x": ball.position_x,
                "y": ball.position_y,
                "vx": ball.velocity_x,
                "vy": ball.velocity_y,
            }
            for ball_id, ball in sorted(self.simulation.state.balls.items())
        ]
        return {
            "version": 1,
            "type": "state_snapshot",
            "tick": snapshot.tick,
            "revision": snapshot.revision,
            "phase": snapshot.phase.value,
            "round_number": snapshot.round_number,
            "active_player_id": snapshot.active_player_id,
            "remaining_turn_ticks": remaining,
            "players": players,
            "balls": balls,
            "round_winners": snapshot.round_winners,
            "match_winners": snapshot.match_winners,
            "match_result": snapshot.match_result,
        }


def command_rejected_message(
    code: str,
    message: str,
    *,
    seq: int | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build the standard non-mutating command rejection event."""

    result: dict[str, Any] = {
        "version": 1,
        "type": "command_rejected",
        "code": code,
        "message": message,
    }
    if seq is not None:
        result["seq"] = seq
    if request_id is not None:
        result["request_id"] = request_id
    return result
