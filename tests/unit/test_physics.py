"""Deterministic SP-3 geometry, boundary, and contact-foundation tests."""

import unittest

from simulation.physics import (
    Circle,
    CollisionContact,
    CollisionPriority,
    ContactIdentity,
    ContactTracker,
    StageBounds,
    Vec2,
    circles_overlap,
    contain_circle,
    attack_hits_circle,
    order_contacts,
    resolve_ball_boundary,
    swept_circle_intersects,
)


class PhysicsTests(unittest.TestCase):
    """Verify pure geometry and server-owned boundary behavior."""

    def test_grazing_and_overlap_are_inclusive_and_deterministic(self) -> None:
        """Touching circles collide; a one-unit gap does not."""

        first = Circle("a", Vec2(0, 0), 5)
        grazing = Circle("b", Vec2(10, 0), 5)
        separated = Circle("c", Vec2(11, 0), 5)
        overlapping = Circle("d", Vec2(3, 0), 5)
        self.assertTrue(circles_overlap(first, grazing))
        self.assertFalse(circles_overlap(first, separated))
        self.assertTrue(circles_overlap(first, overlapping))

    def test_player_containment_clamps_stage_edges(self) -> None:
        """A player center is clamped so its full circle remains boxed."""

        stage = StageBounds(100, 80)
        self.assertEqual(contain_circle(Vec2(-5, 100), 10, stage), Vec2(10, 70))
        self.assertEqual(contain_circle(Vec2(50, 40), 10, stage), Vec2(50, 40))

    def test_ball_corner_bounce_is_axis_deterministic(self) -> None:
        """A corner contact resolves left/right before top/bottom consistently."""

        result = resolve_ball_boundary(
            Vec2(-5, 105), Vec2(-10, 20), 10, StageBounds(100, 100), 0.85
        )
        self.assertEqual(result.center, Vec2(10, 90))
        self.assertEqual(result.velocity, Vec2(8.5, -17.0))
        self.assertEqual(result.touched, ("left", "bottom"))

    def test_invalid_dimensions_and_radii_are_rejected(self) -> None:
        """Non-positive dimensions and impossible circle fits fail explicitly."""

        with self.assertRaises(ValueError):
            StageBounds(0, 100)
        with self.assertRaises(ValueError):
            StageBounds(100, -1)
        with self.assertRaises(ValueError):
            Circle("bad", Vec2(0, 0), 0)
        with self.assertRaises(ValueError):
            contain_circle(Vec2(10, 10), 51, StageBounds(100, 100))

    def test_swept_circle_catches_high_speed_tunneling(self) -> None:
        """Segment testing detects a target crossed between fixed-step endpoints."""

        target = Circle("target", Vec2(50, 50), 5)
        self.assertFalse(circles_overlap(Circle("moving", Vec2(90, 50), 5), target))
        self.assertTrue(swept_circle_intersects(Vec2(10, 50), Vec2(90, 50), 5, target))

    def test_contact_identity_epochs_change_after_separation_and_bounce(self) -> None:
        """Repeated overlap is one event; separation and bounce create new epochs."""

        tracker = ContactTracker()
        self.assertEqual(tracker.observe("ball", "p1", True), ContactIdentity("ball", "p1", 0))
        self.assertIsNone(tracker.observe("ball", "p1", True))
        self.assertIsNone(tracker.observe("ball", "p1", False))
        self.assertEqual(tracker.observe("ball", "p1", True), ContactIdentity("ball", "p1", 1))
        tracker.bounce("ball")
        self.assertEqual(tracker.observe("ball", "p1", True), ContactIdentity("ball", "p1", 2))

    def test_collision_order_uses_priority_then_stable_ids(self) -> None:
        """Collision resolution order is independent of input collection order."""

        contacts = [
            CollisionContact(CollisionPriority.PLAYER_PLAYER, ContactIdentity("p2", "p1", 0)),
            CollisionContact(CollisionPriority.BALL_PLAYER, ContactIdentity("b2", "p1", 0)),
            CollisionContact(CollisionPriority.BALL_PLAYER, ContactIdentity("b1", "p2", 0)),
            CollisionContact(CollisionPriority.BOUNDARY, ContactIdentity("b2", "stage", 0)),
        ]
        ordered = order_contacts(contacts)
        self.assertEqual(
            [(contact.priority, contact.identity.source_id) for contact in ordered],
            [
                (CollisionPriority.BOUNDARY, "b2"),
                (CollisionPriority.BALL_PLAYER, "b1"),
                (CollisionPriority.BALL_PLAYER, "b2"),
                (CollisionPriority.PLAYER_PLAYER, "p2"),
            ],
        )

    def test_attack_hitbox_is_forward_semicircle(self) -> None:
        """A forward hit is accepted while a rear target is excluded."""

        attacker = Vec2(100, 100)
        forward = Circle("forward", Vec2(160, 100), 24)
        rear = Circle("rear", Vec2(40, 100), 24)
        side = Circle("side", Vec2(100, 200), 24)
        self.assertTrue(attack_hits_circle(attacker, forward, 1, 72))
        self.assertFalse(attack_hits_circle(attacker, rear, 1, 72))
        self.assertFalse(attack_hits_circle(attacker, side, 1, 72))


if __name__ == "__main__":
    unittest.main()
