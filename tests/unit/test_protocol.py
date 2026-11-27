"""SP-6 design-level protocol artifact and envelope tests."""

import json
from pathlib import Path
import unittest

from shared.protocol import MAX_MESSAGE_BYTES, validate_message


class ProtocolTests(unittest.TestCase):
    """Verify protocol artifacts without starting transport or browser code."""

    def test_schema_is_valid_json_with_required_message_definitions(self) -> None:
        """The schema contains the approved protocol message vocabulary."""

        schema_path = Path(__file__).parents[2] / "shared" / "protocol_schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        definitions = schema["$defs"]
        for name in (
            "hello",
            "move",
            "attack",
            "state_snapshot",
            "command_rejected",
            "host_disconnected",
        ):
            self.assertIn(name, definitions)
        self.assertEqual(schema["oneOf"][0]["$ref"], "#/$defs/hello")

    def test_hello_must_be_first_and_versioned(self) -> None:
        """Non-hello first messages and wrong versions are rejected."""

        self.assertEqual(
            validate_message({"version": 1, "type": "move_start"}, first_message=True).code,
            "HELLO_REQUIRED",
        )
        self.assertEqual(
            validate_message({"version": 2, "type": "hello"}, first_message=True).code,
            "BAD_VERSION",
        )
        self.assertTrue(
            validate_message(
                {"version": 1, "type": "hello", "request_id": "r1", "client_name": "test"},
                first_message=True,
            ).accepted
        )

    def test_size_and_gameplay_sequence_rules(self) -> None:
        """Oversized messages and non-increasing gameplay sequences reject."""

        oversized = {"version": 1, "type": "hello", "request_id": "r1", "client_name": "x" * MAX_MESSAGE_BYTES}
        self.assertEqual(validate_message(oversized).code, "TOO_LARGE")
        message = {"version": 1, "type": "attack", "seq": 4}
        self.assertTrue(validate_message(message, last_gameplay_seq=3).accepted)
        self.assertEqual(validate_message(message, last_gameplay_seq=4).code, "DUPLICATE_SEQ")

    def test_malformed_gameplay_sequence_rejects_without_transport(self) -> None:
        """Gameplay sequence shape is checked independently of live connections."""

        result = validate_message({"version": 1, "type": "attack", "seq": "4"})
        self.assertEqual((result.accepted, result.code), (False, "MALFORMED"))


if __name__ == "__main__":
    unittest.main()
