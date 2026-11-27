"""Static SP-8 browser-client contract checks."""

from pathlib import Path
import unittest


CLIENT = Path(__file__).parents[2] / "client"


class ClientAssetTests(unittest.TestCase):
    """Ensure the browser handoff contains the required protocol/UI surface."""

    def test_entrypoint_loads_modular_client_and_all_screens(self) -> None:
        html = (CLIENT / "index.html").read_text(encoding="utf-8")
        for marker in ("screen-lobby", "screen-setup", "screen-game", "screen-result", "game-canvas", "client.js"):
            self.assertIn(marker, html)

    def test_client_uses_intents_not_authoritative_gameplay_state(self) -> None:
        script = (CLIENT / "client.js").read_text(encoding="utf-8")
        for marker in ("create_lobby", "join_lobby", "host_config", "ready", "start_match", "move_start", "move_stop", "attack", "command_rejected", "state_snapshot"):
            self.assertIn(marker, script)
        self.assertIn("new WebSocket", script)
        self.assertNotIn("player.x =", script)
        self.assertNotIn("player.damage =", script)

    def test_renderer_and_hud_are_display_only(self) -> None:
        renderer = (CLIENT / "renderer.js").read_text(encoding="utf-8")
        hud = (CLIENT / "hud.js").read_text(encoding="utf-8")
        self.assertIn("interpolation is visual only", renderer)
        self.assertIn("remaining_turn_ticks", hud)
        self.assertIn("match_winners", (CLIENT / "client.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
