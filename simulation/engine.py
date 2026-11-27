"""Deterministic local simulation shell through SP-2."""

from .commands import (
    Command,
    CommandResult,
    CommandType,
    MoveDirection,
    order_commands,
)
from .config import SimulationConfig
from .phases import GamePhase, InvalidPhaseTransition, PhaseMachine
from .physics import StageBounds, Vec2, contain_circle, resolve_ball_boundary
from .physics import (
    Circle,
    ContactTracker,
    attack_hits_circle,
    circles_overlap,
    knockback_vector,
    separation_for_circles,
)
from .state import DodgeballState, MatchState, PlayerState, Snapshot, TurnState


class Simulation:
    """Advance authoritative lifecycle, movement, and timed turns at 60 Hz."""

    def __init__(self, config: SimulationConfig | None = None) -> None:
        """Create a fresh local simulation in the lobby phase."""

        selected_config = config or SimulationConfig()
        self.state = MatchState(config=selected_config)
        self._phases = PhaseMachine()
        self._seen_sequences: dict[str, int] = {}
        self._contact_tracker = ContactTracker()
        self._pending_attacks: set[str] = set()

    def add_player(self, player_id: str, color: str) -> None:
        """Add a local player before setup, assigning the first player as host."""

        if self.state.phase is not GamePhase.LOBBY:
            raise ValueError("players can only join during the lobby")
        if not player_id or player_id in self.state.players:
            raise ValueError("player_id must be non-empty and unique")
        if len(self.state.players) >= self.state.config.max_players:
            raise ValueError("maximum active player count reached")
        self.state.players[player_id] = PlayerState(
            player_id=player_id,
            color=color,
            position_x=self.state.stage.width / 2,
            position_y=self.state.stage.height / 2,
        )
        if self.state.host_player_id is None:
            self.state.host_player_id = player_id

    def add_ball(self, ball_id: str, position: Vec2, velocity: Vec2 = Vec2(0.0, 0.0)) -> None:
        """Add a server-owned dodgeball before setup for local physics checks."""

        if self.state.phase is not GamePhase.LOBBY:
            raise ValueError("balls can only be added during the lobby")
        if not ball_id or ball_id in self.state.balls:
            raise ValueError("ball_id must be non-empty and unique")
        stage = StageBounds(self.state.stage.width, self.state.stage.height)
        contained = contain_circle(position, self.state.config.ball_collision_radius, stage)
        self.state.balls[ball_id] = DodgeballState(
            ball_id=ball_id,
            position_x=contained.x,
            position_y=contained.y,
            velocity_x=velocity.x,
            velocity_y=velocity.y,
            visible_radius=self.state.config.ball_visible_radius,
            collision_radius=self.state.config.ball_collision_radius,
        )

    def configure_match(
        self,
        rounds: int = 1,
        turn_seconds: int = 30,
        requester_id: str | None = None,
    ) -> None:
        """Set local match timing when requested by the host during setup."""

        if self.state.phase is not GamePhase.SETUP:
            raise ValueError("match configuration requires setup phase")
        if requester_id != self.state.host_player_id:
            raise PermissionError("only the host may configure the match")
        if rounds <= 0:
            raise ValueError("rounds must be positive")
        if turn_seconds not in self.state.config.turn_presets:
            raise ValueError("turn_seconds must be an approved preset")
        self.state.configured_rounds = rounds
        self.state.turn_duration_seconds = turn_seconds

    def return_to_setup(self) -> None:
        """Return from match result to setup and clear all match-only results."""

        if self.state.phase is not GamePhase.MATCH_RESULT:
            raise ValueError("return to setup requires match result phase")
        self._phases.transition(GamePhase.SETUP)
        self.state.phase = GamePhase.SETUP
        self.state.round_winners = ()
        self.state.round_winner_history = ()
        self.state.match_winners = ()
        self.state.match_result = None
        self.state.configured_rounds = 1
        self.state.turn = TurnState(order=tuple(sorted(self.state.players)))
        self.state.balls.clear()
        self._contact_tracker = ContactTracker()
        self._pending_attacks.clear()
        for player in self.state.players.values():
            player.damage = 0
            player.round_score = 0
            player.round_wins = 0
            player.attack_used = False
            player.knockback_x = 0.0
            player.knockback_y = 0.0

    def step(self, commands: list[Command] | tuple[Command, ...] = ()) -> Snapshot:
        """Advance exactly one fixed tick after deterministic command intake."""

        self.state.last_attack_hits = ()
        self._pending_attacks.clear()
        if not isinstance(commands, (list, tuple)):
            results = [
                CommandResult(False, "malformed_batch", "commands must be a list or tuple")
            ]
        elif not all(self._has_valid_shape(command) for command in commands):
            results = [
                CommandResult(False, "malformed_command", "command entry has an invalid shape")
                for _ in commands
            ] or [CommandResult(False, "malformed_batch", "command batch is empty")]
        else:
            results = [self._handle(command) for command in order_commands(list(commands))]

        self.state.last_command_results = tuple(results)
        self._move_players()
        self._advance_balls()
        self._resolve_attacks()
        self._resolve_ball_contacts()
        self._separate_players()
        self._expire_turn_if_due()
        self._pending_attacks.clear()
        self.state.tick += 1
        self.state.revision += 1
        return self.snapshot()

    @staticmethod
    def _has_valid_shape(command: object) -> bool:
        """Return whether an object satisfies the local command contract."""

        return (
            isinstance(command, Command)
            and isinstance(command.command_type, CommandType)
            and type(command.receive_ordinal) is int
            and type(command.client_sequence) is int
            and (command.player_id is None or isinstance(command.player_id, str))
            and (command.direction is None or isinstance(command.direction, MoveDirection))
        )

    def snapshot(self) -> Snapshot:
        """Return a read-only snapshot of authoritative local state."""

        return Snapshot.from_state(self.state)

    def _handle(self, command: Command) -> CommandResult:
        """Validate and apply one local command without partial mutation."""

        if command.receive_ordinal < 0 or command.client_sequence < 0:
            return CommandResult(False, "invalid_metadata", "command metadata is negative")
        gameplay_command = command.command_type in (
            CommandType.MOVE_START,
            CommandType.MOVE_STOP,
            CommandType.ATTACK,
        )
        if gameplay_command and command.player_id is not None:
            previous = self._seen_sequences.get(command.player_id, -1)
            if command.client_sequence <= previous:
                return CommandResult(False, "stale_sequence", "client sequence is not increasing")

        if command.command_type in (CommandType.MOVE_START, CommandType.MOVE_STOP):
            result = self._handle_movement(command)
        elif command.command_type is CommandType.ATTACK:
            result = self._handle_attack(command)
        else:
            result = self._handle_lifecycle(command)
        if gameplay_command and command.player_id is not None:
            self._seen_sequences[command.player_id] = command.client_sequence
        return result

    def _handle_movement(self, command: Command) -> CommandResult:
        """Accept movement only from the active player during an active turn."""

        if command.direction is None:
            return CommandResult(False, "invalid_command", "movement requires a direction")
        if self.state.phase is not GamePhase.ACTIVE_TURN:
            return CommandResult(False, "out_of_turn", "movement is unavailable outside an active turn")
        if command.player_id != self.state.turn.active_player_id:
            return CommandResult(False, "out_of_turn", "only the active player may move")
        player = self.state.players.get(command.player_id or "")
        if player is None or not player.connected:
            return CommandResult(False, "unknown_player", "player is not connected")
        is_pressed = command.command_type is CommandType.MOVE_START
        if command.direction is MoveDirection.LEFT:
            player.held_left = is_pressed
            if is_pressed:
                player.facing = MoveDirection.LEFT
        else:
            player.held_right = is_pressed
            if is_pressed:
                player.facing = MoveDirection.RIGHT
        return CommandResult(True, "accepted", f"movement {command.command_type.value}")

    def _handle_attack(self, command: Command) -> CommandResult:
        """Accept one E-key attack intent from the active player per turn."""

        if self.state.phase is not GamePhase.ACTIVE_TURN:
            return CommandResult(False, "out_of_turn", "attack is unavailable outside an active turn")
        if command.player_id != self.state.turn.active_player_id:
            return CommandResult(False, "out_of_turn", "only the active player may attack")
        player = self.state.players.get(command.player_id or "")
        if player is None or not player.connected:
            return CommandResult(False, "unknown_player", "player is not connected")
        if player.attack_used:
            return CommandResult(False, "attack_already_used", "one attack is allowed per turn")
        player.attack_used = True
        self._pending_attacks.add(player.player_id)
        return CommandResult(True, "accepted", "attack queued")

    def _handle_lifecycle(self, command: Command) -> CommandResult:
        """Apply host lifecycle commands and reject unauthorized transitions."""

        if command.command_type is CommandType.START_SETUP:
            if command.player_id != self.state.host_player_id:
                return CommandResult(False, "not_host", "only the host may start setup")
            try:
                self._phases.transition(GamePhase.SETUP)
            except InvalidPhaseTransition as error:
                return CommandResult(False, "invalid_transition", str(error))
            self.state.phase = GamePhase.SETUP
            self.state.turn = TurnState(order=tuple(sorted(self.state.players)))
            return CommandResult(True, "accepted", "setup started")

        if command.command_type is CommandType.START_MATCH:
            if command.player_id != self.state.host_player_id:
                return CommandResult(False, "not_host", "only the host may start the match")
            if not self.state.turn.order:
                return CommandResult(False, "no_players", "at least one player is required")
            try:
                self._phases.transition(GamePhase.TURN_START)
                self._phases.transition(GamePhase.ACTIVE_TURN)
            except InvalidPhaseTransition as error:
                return CommandResult(False, "invalid_transition", str(error))
            self._reset_round_state()
            self.state.round_winners = ()
            self.state.round_winner_history = ()
            self.state.match_winners = ()
            self.state.match_result = None
            self.state.phase = GamePhase.ACTIVE_TURN
            self._begin_next_turn()
            return CommandResult(True, "accepted", "match started")

        if command.command_type is CommandType.HOST_DISCONNECT:
            try:
                self._phases.transition(GamePhase.HOST_DISCONNECTED)
            except InvalidPhaseTransition as error:
                return CommandResult(False, "invalid_transition", str(error))
            self.state.phase = GamePhase.HOST_DISCONNECTED
            return CommandResult(True, "accepted", "host disconnected")

        if command.command_type is CommandType.CLOSE:
            try:
                self._phases.transition(GamePhase.CLOSED)
            except InvalidPhaseTransition as error:
                return CommandResult(False, "invalid_transition", str(error))
            self.state.phase = GamePhase.CLOSED
            return CommandResult(True, "accepted", "simulation closed")

        return CommandResult(False, "invalid_command", "command type is not supported")

    def _begin_next_turn(self) -> None:
        """Select the next connected player and initialize its timer."""

        completed = set(self.state.turn.completed_player_ids)
        candidates = [
            player_id
            for player_id in self.state.turn.order
            if player_id not in completed
            and player_id in self.state.players
            and self.state.players[player_id].connected
        ]
        if not candidates:
            return
        active_player_id = candidates[0]
        duration_ticks = self.state.turn_duration_seconds * self.state.config.tick_rate
        self.state.turn = TurnState(
            active_player_id=active_player_id,
            start_tick=self.state.tick,
            end_tick=self.state.tick + duration_ticks,
            order=self.state.turn.order,
            completed_player_ids=self.state.turn.completed_player_ids,
            round_number=self.state.turn.round_number,
        )
        self.state.players[active_player_id].attack_used = False

    def _move_players(self) -> None:
        """Advance regular movement and existing knockback for every player."""

        delta = self.state.config.tick_seconds
        active_id = self.state.turn.active_player_id if self.state.phase is GamePhase.ACTIVE_TURN else None
        for player_id in sorted(self.state.players):
            player = self.state.players[player_id]
            if player_id == active_id:
                direction = int(player.held_right) - int(player.held_left)
                if direction:
                    player.velocity_x += direction * self.state.config.player_acceleration * delta
                    player.velocity_x = max(
                        -self.state.config.player_max_speed,
                        min(self.state.config.player_max_speed, player.velocity_x),
                    )
                else:
                    deceleration = self.state.config.player_deceleration * delta
                    if abs(player.velocity_x) <= deceleration:
                        player.velocity_x = 0.0
                    else:
                        player.velocity_x -= deceleration if player.velocity_x > 0 else -deceleration
            else:
                player.velocity_x = 0.0
            decay = max(0.0, 1.0 - delta / self.state.config.knockback_decay_seconds)
            player.knockback_x *= decay
            player.knockback_y *= decay
            player.position_x += (player.velocity_x + player.knockback_x) * delta
            player.position_y += player.knockback_y * delta
            contained = contain_circle(
                Vec2(player.position_x, player.position_y),
                self.state.config.player_radius,
                StageBounds(self.state.stage.width, self.state.stage.height),
            )
            player.position_x = contained.x
            player.position_y = contained.y

    def _advance_balls(self) -> None:
        """Advance balls and resolve boxed-stage boundary bounces only."""

        if self.state.phase is not GamePhase.ACTIVE_TURN:
            return
        delta = self.state.config.tick_seconds
        stage = StageBounds(self.state.stage.width, self.state.stage.height)
        for ball_id in sorted(self.state.balls):
            ball = self.state.balls[ball_id]
            center = Vec2(
                ball.position_x + ball.velocity_x * delta,
                ball.position_y + ball.velocity_y * delta,
            )
            resolution = resolve_ball_boundary(
                center,
                Vec2(ball.velocity_x, ball.velocity_y),
                ball.collision_radius,
                stage,
                self.state.config.boundary_restitution,
            )
            ball.position_x = resolution.center.x
            ball.position_y = resolution.center.y
            ball.velocity_x = resolution.velocity.x
            ball.velocity_y = resolution.velocity.y
            if resolution.touched:
                ball.contact_epoch += 1
                self._contact_tracker.bounce(ball_id)

    def _resolve_attacks(self) -> None:
        """Resolve one-tick attack hitboxes in stable attacker/target order."""

        hits: list[tuple[str, str]] = []
        for attacker_id in sorted(self._pending_attacks):
            attacker = self.state.players[attacker_id]
            attacker_center = Vec2(attacker.position_x, attacker.position_y)
            facing_x = -1 if attacker.facing is MoveDirection.LEFT else 1
            for target_id in sorted(self.state.players):
                if target_id == attacker_id:
                    continue
                target = self.state.players[target_id]
                target_circle = Circle(
                    target_id,
                    Vec2(target.position_x, target.position_y),
                    self.state.config.player_radius,
                )
                if attack_hits_circle(
                    attacker_center, target_circle, facing_x, self.state.config.attack_reach
                ):
                    hits.append((attacker_id, target_id))
                    self._apply_knockback(attacker, target)
            for ball_id in sorted(self.state.balls):
                ball = self.state.balls[ball_id]
                target_circle = Circle(
                    ball_id,
                    Vec2(ball.position_x, ball.position_y),
                    ball.collision_radius,
                )
                if attack_hits_circle(
                    attacker_center, target_circle, facing_x, self.state.config.attack_reach
                ):
                    hits.append((attacker_id, ball_id))
        self.state.last_attack_hits = tuple(hits)

    def _resolve_ball_contacts(self) -> None:
        """Apply deduplicated ball-player contact damage and knockback."""

        for ball_id in sorted(self.state.balls):
            ball = self.state.balls[ball_id]
            ball_circle = Circle(
                ball_id,
                Vec2(ball.position_x, ball.position_y),
                ball.collision_radius,
            )
            for player_id in sorted(self.state.players):
                player = self.state.players[player_id]
                player_circle = Circle(
                    player_id,
                    Vec2(player.position_x, player.position_y),
                    self.state.config.player_radius,
                )
                identity = self._contact_tracker.observe(
                    ball_id, player_id, circles_overlap(ball_circle, player_circle)
                )
                if identity is None:
                    continue
                damage = self._ball_contact_damage(ball.valid_contact_count)
                ball.valid_contact_count += 1
                player.damage = max(0, player.damage + damage)
                player.round_score = max(0, player.round_score + damage)
                self._apply_knockback_from_position(
                    Vec2(ball.position_x, ball.position_y), player
                )

    def _ball_contact_damage(self, contact_count: int) -> int:
        """Return the 100%/50%/25%/0% contact sequence value."""

        multiplier = (1.0, 0.5, 0.25, 0.0)[min(contact_count, 3)]
        return int(self.state.config.ball_hit_value * multiplier)

    def _separate_players(self) -> None:
        """Resolve player-player overlaps in stable pair order without damage."""

        player_ids = sorted(self.state.players)
        for index, first_id in enumerate(player_ids):
            for second_id in player_ids[index + 1 :]:
                first = self.state.players[first_id]
                second = self.state.players[second_id]
                separated = separation_for_circles(
                    Vec2(first.position_x, first.position_y),
                    Vec2(second.position_x, second.position_y),
                    self.state.config.player_radius,
                    self.state.config.player_radius,
                )
                if separated is None:
                    continue
                first_center, second_center = separated
                first_center = contain_circle(
                    first_center,
                    self.state.config.player_radius,
                    StageBounds(self.state.stage.width, self.state.stage.height),
                )
                second_center = contain_circle(
                    second_center,
                    self.state.config.player_radius,
                    StageBounds(self.state.stage.width, self.state.stage.height),
                )
                first.position_x, first.position_y = first_center.x, first_center.y
                second.position_x, second.position_y = second_center.x, second_center.y

    def _apply_knockback(self, source: PlayerState, target: PlayerState) -> None:
        """Apply bounded knockback from one player to another."""

        self._apply_knockback_from_position(
            Vec2(source.position_x, source.position_y), target, source.facing
        )

    def _apply_knockback_from_position(
        self,
        source_position: Vec2,
        target: PlayerState,
        fallback_direction: MoveDirection = MoveDirection.RIGHT,
    ) -> None:
        """Apply bounded knockback from a point using target accumulated damage."""

        impulse = min(
            self.state.config.knockback_max_impulse,
            self.state.config.knockback_base_impulse
            + self.state.config.knockback_damage_factor * target.damage,
        )
        direction = knockback_vector(
            source_position,
            Vec2(target.position_x, target.position_y),
            impulse,
            -1 if fallback_direction is MoveDirection.LEFT else 1,
        )
        target.knockback_x += direction.x
        target.knockback_y += direction.y

    def _expire_turn_if_due(self) -> None:
        """Pass a timed-out turn and select the next connected player."""

        if self.state.phase is not GamePhase.ACTIVE_TURN:
            return
        if self.state.turn.end_tick is None or self.state.tick + 1 < self.state.turn.end_tick:
            return
        completed = self.state.turn.completed_player_ids + (
            self.state.turn.active_player_id or "",
        )
        self.state.turn = TurnState(
            order=self.state.turn.order,
            completed_player_ids=completed,
            round_number=self.state.turn.round_number,
        )
        self._phases.transition(GamePhase.TURN_RESULT)
        self.state.phase = GamePhase.TURN_RESULT
        remaining = [
            player_id
            for player_id in self.state.turn.order
            if player_id not in completed
            and player_id in self.state.players
            and self.state.players[player_id].connected
        ]
        if remaining:
            self._start_next_turn()
        else:
            self._complete_round()

    def _start_next_turn(self) -> None:
        """Transition through turn-start into the next active player turn."""

        self._phases.transition(GamePhase.TURN_START)
        self._phases.transition(GamePhase.ACTIVE_TURN)
        self.state.phase = GamePhase.ACTIVE_TURN
        self._begin_next_turn()

    def _complete_round(self) -> None:
        """Freeze the round winner and either start another round or finish."""

        self._phases.transition(GamePhase.ROUND_RESULT)
        self.state.phase = GamePhase.ROUND_RESULT
        eligible = [
            player_id
            for player_id in self.state.turn.order
            if player_id in self.state.players and self.state.players[player_id].connected
        ]
        highest_score = max(
            (self.state.players[player_id].round_score for player_id in eligible),
            default=0,
        )
        winners = tuple(
            player_id
            for player_id in eligible
            if self.state.players[player_id].round_score == highest_score
        )
        self.state.round_winners = winners
        self.state.round_winner_history = self.state.round_winner_history + (winners,)
        for player_id in winners:
            self.state.players[player_id].round_wins += 1

        if self.state.turn.round_number >= self.state.configured_rounds:
            highest_wins = max(
                (self.state.players[player_id].round_wins for player_id in eligible),
                default=0,
            )
            self.state.match_winners = tuple(
                player_id
                for player_id in eligible
                if self.state.players[player_id].round_wins == highest_wins
            )
            self.state.match_result = "tie" if len(self.state.match_winners) != 1 else "winner"
            self._phases.transition(GamePhase.MATCH_RESULT)
            self.state.phase = GamePhase.MATCH_RESULT
            return

        self._reset_round_state()
        self.state.turn = TurnState(
            order=self.state.turn.order,
            round_number=self.state.turn.round_number + 1,
        )
        self._start_next_round()

    def _start_next_round(self) -> None:
        """Transition from round result into the next round's first turn."""

        self._phases.transition(GamePhase.TURN_START)
        self._phases.transition(GamePhase.ACTIVE_TURN)
        self.state.phase = GamePhase.ACTIVE_TURN
        self._begin_next_turn()

    def _reset_round_state(self) -> None:
        """Reset round-local damage and score while preserving match wins."""

        for player in self.state.players.values():
            player.damage = 0
            player.round_score = 0
            player.attack_used = False
            player.knockback_x = 0.0
            player.knockback_y = 0.0
            player.held_left = False
            player.held_right = False
        self._contact_tracker = ContactTracker()
