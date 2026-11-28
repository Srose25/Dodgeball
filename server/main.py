"""Launch the v1 LAN WebSocket server with same-process static serving."""

import argparse
import asyncio
import socket
from pathlib import Path

from .transport import GameServer, serve, static_process_request


def detect_lan_ipv4() -> str | None:
    """Detect a likely non-loopback IPv4 address without sending traffic."""

    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        address = probe.getsockname()[0]
        return address if not address.startswith("127.") else None
    except OSError:
        return None
    finally:
        probe.close()


def choose_port(start: int = 8765, end: int = 8775) -> int:
    """Return the first locally bindable TCP port in the approved range."""

    import socket

    for port in range(start, end + 1):
        with socket.socket() as probe:
            try:
                probe.bind(("0.0.0.0", port))
            except OSError:
                continue
            return port
    raise OSError("no approved LAN port is available")


async def run(host: str, port: int) -> None:
    """Run the authoritative LAN server until interrupted."""

    if serve is None:
        raise RuntimeError("websockets is required; install requirements.txt before starting the LAN server")
    game_server = GameServer(Path(__file__).parents[1] / "client")

    async def process_request(connection, request):
        """Serve the minimal client while preserving the WebSocket upgrade path."""

        return await static_process_request(connection, request, game_server.client_root)

    async with serve(
        game_server.handler,
        host,
        port,
        max_size=16 * 1024,
        process_request=process_request,
    ):
        lan_ip = detect_lan_ipv4()
        print(f"Dodgeball LAN server bound to {host}:{port}")
        print(f"Open on this computer: http://localhost:{port}/")
        if lan_ip:
            print(f"Open from LAN clients: http://{lan_ip}:{port}/")
        else:
            print("LAN address: unable to detect automatically; use this computer's IPv4 address")
        print(f"WebSocket path: /ws (derived from the page URL)")
        await asyncio.Future()


def main() -> None:
    """Parse launch options and start the LAN server."""

    parser = argparse.ArgumentParser(description="Dodgeball LAN server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=None)
    args = parser.parse_args()
    port = args.port or choose_port()
    try:
        asyncio.run(run(args.host, port))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
