"""Static SP-8 browser-client contract checks."""

from pathlib import Path
import re
import unittest


CLIENT = Path(__file__).parents[2] / "client"


class ClientAssetTests(unittest.TestCase):
    """Ensure the browser handoff contains the required protocol/UI surface."""

    def test_entrypoint_loads_modular_client_and_all_screens(self) -> None:
        html = (CLIENT / "index.html").read_text(encoding="utf-8")
        for marker in ("screen-lobby", "screen-setup", "screen-game", "screen-result", "game-canvas", "player-count", "setup-status", "client.js"):
            self.assertIn(marker, html)
        self.assertIn('<link rel="stylesheet" href="styles.css">', html)
        self.assertIn('<script type="module" src="/client.js"></script>', html)

    def test_static_asset_paths_and_mime_extensions_match_server_contract(self) -> None:
        """Static browser references map to files and expected response types."""

        html = (CLIENT / "index.html").read_text(encoding="utf-8")
        referenced = re.findall(r'(?:href|src)="([^"#?]+)"', html)
        self.assertIn("styles.css", referenced)
        self.assertIn("/client.js", referenced)
        for reference in referenced:
            asset = CLIENT / reference.lstrip("/")
            self.assertTrue(asset.is_file(), reference)
        self.assertEqual((CLIENT / "index.html").suffix, ".html")
        self.assertEqual((CLIENT / "client.js").suffix, ".js")
        self.assertEqual((CLIENT / "styles.css").suffix, ".css")

    def test_stylesheet_is_readable_and_preserves_required_selectors(self) -> None:
        """CSS uses one declaration per line and retains every screen selector."""

        css = (CLIENT / "styles.css").read_text(encoding="utf-8")
        for selector in (":root", ".hidden", ".screen", ".canvas-wrap", "canvas", "@media"):
            self.assertIn(selector, css)
        self.assertNotRegex(css, r"\{[^{}\r\n]*:[^{}\r\n]*;")
        self.assertNotIn("!important;}", css)

    def test_client_uses_intents_not_authoritative_gameplay_state(self) -> None:
        script = (CLIENT / "client.js").read_text(encoding="utf-8")
        for marker in ("create_lobby", "join_lobby", "host_config", "ready", "start_match", "move_start", "move_stop", "attack", "command_rejected", "state_snapshot", "authoritativePhase", "active_turn"):
            self.assertIn(marker, script)
        self.assertIn("new WebSocket", script)
        self.assertIn("/ws", script)
        self.assertIn("hello", script)
        self.assertIn("welcome", script)
        self.assertIn("lobby_state", script)
        self.assertNotIn("player.x =", script)
        self.assertNotIn("player.damage =", script)

    def test_renderer_and_hud_are_display_only(self) -> None:
        renderer = (CLIENT / "renderer.js").read_text(encoding="utf-8")
        hud = (CLIENT / "hud.js").read_text(encoding="utf-8")
        self.assertIn("interpolation is visual only", renderer)
        self.assertIn("remaining_turn_ticks", hud)
        self.assertIn("match_winners", (CLIENT / "client.js").read_text(encoding="utf-8"))

    def test_u2_phase_routing_keeps_lobby_and_setup_out_of_game_screen(self) -> None:
        """U2-QA-001: authoritative lobby/setup phases must not open gameplay."""

        script = (CLIENT / "client.js").read_text(encoding="utf-8")
        self.assertRegex(script, r"phase.{0,80}(lobby|setup)")
        self.assertRegex(script, r"(lobby|setup).{0,80}show\(['\"]setup['\"]\)")
        self.assertIn("active_turn", script)

    def test_u2_client_exposes_setup_and_connection_contract(self) -> None:
        """U2-QA-001: setup must expose roster, count, config, and readiness state."""

        html = (CLIENT / "index.html").read_text(encoding="utf-8")
        for marker in (
            "connected",
            "roster",
            "round-count",
            "turn-seconds",
            "ready-button",
            "start-match",
        ):
            self.assertIn(marker, html)

    def test_u2_gameplay_input_is_gated_by_authoritative_active_phase(self) -> None:
        """U2-QA-001: pre-match keyboard input must not be treated as gameplay."""

        script = (CLIENT / "client.js").read_text(encoding="utf-8")
        self.assertRegex(script, r"authoritativePhase.{0,80}active_turn")
        self.assertRegex(script, r"gameplayKey.{0,240}authoritativePhase")


if __name__ == "__main__":
    unittest.main()
