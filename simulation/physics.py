"""Pure deterministic geometry and boundary-resolution primitives.

This module deliberately has no knowledge of turns, attacks, scoring, transport,
or rendering. The simulation owns when these primitives are invoked.
"""

from dataclasses import dataclass
from enum import IntEnum
import math


@dataclass(frozen=True, slots=True)
class Vec2:
    """Finite two-dimensional point or velocity value."""

    x: float
    y: float

    def __post_init__(self) -> None:
        """Reject non-finite coordinates that could poison deterministic physics."""

        if not math.isfinite(self.x) or not math.isfinite(self.y):
            raise ValueError("Vec2 coordinates must be finite")


@dataclass(frozen=True, slots=True)
class StageBounds:
    """Validated top-left-origin rectangular stage bounds."""

    width: float
    height: float

    def __post_init__(self) -> None:
        """Reject non-finite or non-positive stage dimensions."""

        if (
            not math.isfinite(self.width)
            or not math.isfinite(self.height)
            or self.width <= 0
            or self.height <= 0
        ):
            raise ValueError("stage dimensions must be finite and positive")


@dataclass(frozen=True, slots=True)
class Circle:
    """Circular body used for logical hitbox calculations."""

    entity_id: str
    center: Vec2
    radius: float

    def __post_init__(self) -> None:
        """Reject empty or non-finite collision bodies."""

        if not self.entity_id:
            raise ValueError("circle entity_id must be non-empty")
        if not math.isfinite(self.radius) or self.radius <= 0:
            raise ValueError("circle radius must be finite and positive")


@dataclass(frozen=True, slots=True)
class BoundaryResolution:
    """Resolved center and velocity after deterministic box handling."""

    center: Vec2
    velocity: Vec2
    touched: tuple[str, ...]


class CollisionPriority(IntEnum):
    """Stable SP-3 ordering for future collision event resolution."""

    BOUNDARY = 0
    ATTACK = 1
    BALL_PLAYER = 2
    PLAYER_PLAYER = 3


@dataclass(frozen=True, slots=True)
class ContactIdentity:
    """Stable source/target/epoch identity for one contact episode."""

    source_id: str
    target_id: str
    contact_epoch: int

    def __post_init__(self) -> None:
        """Validate identity fields used for deterministic ordering."""

        if not self.source_id or not self.target_id or self.contact_epoch < 0:
            raise ValueError("contact identity fields are invalid")


@dataclass(frozen=True, slots=True)
class CollisionContact:
    """Ordered collision observation without gameplay consequences."""

    priority: CollisionPriority
    identity: ContactIdentity


class ContactTracker:
    """Track contact episodes and increment epochs after separation or bounce."""

    def __init__(self) -> None:
        """Create an empty contact ledger."""

        self._epochs: dict[tuple[str, str], int] = {}
        self._active: set[tuple[str, str]] = set()

    def observe(self, source_id: str, target_id: str, touching: bool) -> ContactIdentity | None:
        """Return an identity only when a pair enters a new contact episode."""

        pair = (source_id, target_id)
        epoch = self._epochs.get(pair, 0)
        if touching and pair not in self._active:
            self._active.add(pair)
            return ContactIdentity(source_id, target_id, epoch)
        if not touching and pair in self._active:
            self._active.remove(pair)
            self._epochs[pair] = epoch + 1
        return None

    def bounce(self, source_id: str) -> None:
        """Start a new contact epoch for every active contact from a bounced source."""

        affected = [pair for pair in self._active if pair[0] == source_id]
        for pair in sorted(affected):
            self._active.remove(pair)
            self._epochs[pair] = self._epochs.get(pair, 0) + 1


def attack_hits_circle(
    attacker_center: Vec2,
    target: Circle,
    facing_x: int,
    reach: float,
) -> bool:
    """Return whether a target lies in the attacker's forward semicircle."""

    if facing_x not in (-1, 1):
        raise ValueError("facing_x must be -1 or 1")
    if not math.isfinite(reach) or reach <= 0:
        raise ValueError("attack reach must be finite and positive")
    delta_x = target.center.x - attacker_center.x
    delta_y = target.center.y - attacker_center.y
    if delta_x * facing_x < 0:
        return False
    effective_reach = reach + target.radius
    return delta_x * delta_x + delta_y * delta_y <= effective_reach * effective_reach


def separation_for_circles(
    first_center: Vec2,
    second_center: Vec2,
    first_radius: float,
    second_radius: float,
) -> tuple[Vec2, Vec2] | None:
    """Return separated centers for an overlap, or ``None`` when separate."""

    if first_radius <= 0 or second_radius <= 0:
        raise ValueError("circle radii must be positive")
    delta_x = second_center.x - first_center.x
    delta_y = second_center.y - first_center.y
    distance_squared = delta_x * delta_x + delta_y * delta_y
    minimum_distance = first_radius + second_radius
    if distance_squared >= minimum_distance * minimum_distance:
        return None
    if distance_squared == 0:
        normal_x, normal_y, distance = 1.0, 0.0, 0.0
    else:
        distance = math.sqrt(distance_squared)
        normal_x, normal_y = delta_x / distance, delta_y / distance
    correction = (minimum_distance - distance) / 2
    return (
        Vec2(first_center.x - normal_x * correction, first_center.y - normal_y * correction),
        Vec2(second_center.x + normal_x * correction, second_center.y + normal_y * correction),
    )


def knockback_vector(source: Vec2, target: Vec2, impulse: float, fallback_x: int = 1) -> Vec2:
    """Return a bounded direction vector from source to target."""

    if not math.isfinite(impulse) or impulse < 0:
        raise ValueError("impulse must be finite and non-negative")
    delta_x = target.x - source.x
    delta_y = target.y - source.y
    distance = math.hypot(delta_x, delta_y)
    if distance == 0:
        if fallback_x not in (-1, 1):
            raise ValueError("fallback_x must be -1 or 1")
        return Vec2(float(fallback_x) * impulse, 0.0)
    return Vec2(delta_x / distance * impulse, delta_y / distance * impulse)


def circles_overlap(first: Circle, second: Circle) -> bool:
    """Return whether two circles touch or overlap, including grazing contact."""

    delta_x = first.center.x - second.center.x
    delta_y = first.center.y - second.center.y
    radius_sum = first.radius + second.radius
    return delta_x * delta_x + delta_y * delta_y <= radius_sum * radius_sum


def swept_circle_intersects(
    start: Vec2,
    end: Vec2,
    moving_radius: float,
    target: Circle,
) -> bool:
    """Return whether a moving circle intersects a target along its full segment."""

    if not math.isfinite(moving_radius) or moving_radius <= 0:
        raise ValueError("moving_radius must be finite and positive")
    segment_x = end.x - start.x
    segment_y = end.y - start.y
    segment_length_squared = segment_x * segment_x + segment_y * segment_y
    if segment_length_squared == 0:
        return circles_overlap(Circle("moving", start, moving_radius), target)
    projection = (
        (target.center.x - start.x) * segment_x
        + (target.center.y - start.y) * segment_y
    ) / segment_length_squared
    closest_factor = max(0.0, min(1.0, projection))
    closest = Vec2(start.x + closest_factor * segment_x, start.y + closest_factor * segment_y)
    return circles_overlap(Circle("moving", closest, moving_radius), target)


def contain_circle(center: Vec2, radius: float, stage: StageBounds) -> Vec2:
    """Clamp a circle center inside the stage or reject an impossible fit."""

    _validate_radius_fits(radius, stage)
    return Vec2(
        min(max(center.x, radius), stage.width - radius),
        min(max(center.y, radius), stage.height - radius),
    )


def resolve_ball_boundary(
    center: Vec2,
    velocity: Vec2,
    radius: float,
    stage: StageBounds,
    restitution: float,
) -> BoundaryResolution:
    """Contain a ball and reflect each contacted axis with restitution.

    Axes are processed in left/right/top/bottom order, making corner results
    deterministic and independent of dictionary or iteration order.
    """

    _validate_radius_fits(radius, stage)
    if not math.isfinite(restitution) or not 0 <= restitution <= 1:
        raise ValueError("restitution must be finite and between zero and one")
    x, y = center.x, center.y
    velocity_x, velocity_y = velocity.x, velocity.y
    touched: list[str] = []
    if x < radius:
        x = radius
        velocity_x = abs(velocity_x) * restitution
        touched.append("left")
    elif x > stage.width - radius:
        x = stage.width - radius
        velocity_x = -abs(velocity_x) * restitution
        touched.append("right")
    if y < radius:
        y = radius
        velocity_y = abs(velocity_y) * restitution
        touched.append("top")
    elif y > stage.height - radius:
        y = stage.height - radius
        velocity_y = -abs(velocity_y) * restitution
        touched.append("bottom")
    return BoundaryResolution(Vec2(x, y), Vec2(velocity_x, velocity_y), tuple(touched))


def order_contacts(contacts: list[CollisionContact]) -> list[CollisionContact]:
    """Return contacts in priority, source, target, then epoch order."""

    return sorted(
        contacts,
        key=lambda contact: (
            int(contact.priority),
            contact.identity.source_id,
            contact.identity.target_id,
            contact.identity.contact_epoch,
        ),
    )


def _validate_radius_fits(radius: float, stage: StageBounds) -> None:
    """Validate a positive circle radius against both stage dimensions."""

    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("circle radius must be finite and positive")
    if radius * 2 > stage.width or radius * 2 > stage.height:
        raise ValueError("circle radius cannot fit inside stage")
