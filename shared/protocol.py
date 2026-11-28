"""Transport-free protocol envelope checks for the SP-6 design gate."""

from dataclasses import dataclass
import json

PROTOCOL_VERSION = 1
MAX_MESSAGE_BYTES = 16 * 1024
SIMULATION_HZ = 60
SNAPSHOT_HZ = 30
GAMEPLAY_TYPES = frozenset({"move_start", "move_stop", "attack"})
CLIENT_REQUEST_TYPES = frozenset(
    {"create_lobby", "join_lobby", "ready", "host_config", "start_match", "leave"}
)
MESSAGE_TYPES = GAMEPLAY_TYPES | CLIENT_REQUEST_TYPES | {"hello"}


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
    if message_type not in MESSAGE_TYPES:
        return ProtocolCheck(False, "UNKNOWN_REQUEST", "unsupported message type")
    if first_message and message_type != "hello":
        return ProtocolCheck(False, "HELLO_REQUIRED", "hello must be the first message")
    if message_type == "hello":
        if not isinstance(message.get("request_id"), str) or not message["request_id"]:
            return ProtocolCheck(False, "MALFORMED", "hello request_id is required")
        client_name = message.get("client_name")
        if not isinstance(client_name, str) or not 1 <= len(client_name) <= 32:
            return ProtocolCheck(False, "MALFORMED", "hello client_name must be 1-32 characters")
    elif message_type in CLIENT_REQUEST_TYPES:
        request_id = message.get("request_id")
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 64:
            return ProtocolCheck(False, "MALFORMED", "request_id must be 1-64 characters")
        if message_type == "join_lobby":
            join_code = message.get("join_code")
            if not isinstance(join_code, str) or len(join_code) != 6 or any(character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for character in join_code):
                return ProtocolCheck(False, "MALFORMED", "join_code must be six uppercase alphanumeric characters")
        elif message_type == "ready":
            if not isinstance(message.get("ready"), bool):
                return ProtocolCheck(False, "MALFORMED", "ready must be boolean")
        elif message_type == "host_config":
            rounds = message.get("rounds")
            turn_seconds = message.get("turn_seconds")
            if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds < 1:
                return ProtocolCheck(False, "MALFORMED", "rounds must be a positive integer")
            if turn_seconds not in {30, 45, 60, 120}:
                return ProtocolCheck(False, "MALFORMED", "turn_seconds must be 30, 45, 60, or 120")
    if message_type in GAMEPLAY_TYPES:
        sequence = message.get("seq")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 0:
            return ProtocolCheck(False, "MALFORMED", "gameplay seq must be a non-negative integer")
        if last_gameplay_seq is not None and sequence <= last_gameplay_seq:
            return ProtocolCheck(False, "DUPLICATE_SEQ", "gameplay seq must strictly increase")
        if message_type in {"move_start", "move_stop"} and message.get("direction") not in {"left", "right"}:
            return ProtocolCheck(False, "MALFORMED", "movement direction must be left or right")
    return ProtocolCheck(True, "OK", "message envelope accepted")
