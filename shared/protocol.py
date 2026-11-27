"""Transport-free protocol envelope checks for the SP-6 design gate."""

from dataclasses import dataclass
import json

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 16 * 1024
SIMULATION_HZ = 60
SNAPSHOT_HZ = 30
GAMEPLAY_TYPES = frozenset({"move_start", "move_stop", "attack"})


@dataclass(frozen=True, slots=True)
class ProtocolCheck:
    """Result of validating one decoded protocol message."""

    accepted: bool
    code: str
    message: str


def validate_message(
    message: object,
    *,
    first_message: bool = False,
    last_gameplay_seq: int | None = None,
) -> ProtocolCheck:
    """Validate size, envelope, hello ordering, and gameplay sequence rules.

    This function does not open sockets, authenticate connections, or mutate
    simulation state. It is a design-level contract check for SP-6.
    """

    try:
        encoded = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError):
        return ProtocolCheck(False, "MALFORMED", "message is not JSON encodable")
    if len(encoded) > MAX_MESSAGE_BYTES:
        return ProtocolCheck(False, "TOO_LARGE", "decoded message exceeds 16 KiB")
    if not isinstance(message, dict):
        return ProtocolCheck(False, "MALFORMED", "message must be a JSON object")
    if message.get("version") != PROTOCOL_VERSION:
        return ProtocolCheck(False, "BAD_VERSION", "unsupported protocol version")
    message_type = message.get("type")
    if not isinstance(message_type, str):
        return ProtocolCheck(False, "MALFORMED", "message type is required")
    if first_message and message_type != "hello":
        return ProtocolCheck(False, "HELLO_REQUIRED", "hello must be the first message")
    if message_type in GAMEPLAY_TYPES:
        sequence = message.get("seq")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
            return ProtocolCheck(False, "MALFORMED", "gameplay seq must be a non-negative integer")
        if last_gameplay_seq is not None and sequence <= last_gameplay_seq:
            return ProtocolCheck(False, "DUPLICATE_SEQ", "gameplay seq must strictly increase")
    return ProtocolCheck(True, "OK", "message envelope accepted")
