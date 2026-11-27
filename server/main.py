"""Launch the v1 LAN WebSocket server with same-process static serving."""

import argparse
import asyncio
from pathlib import Path

from .transport import GameServer, serve, static_process_request


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
        print(f"Dodgeball LAN server: http://{host}:{port}/")
        print(f"WebSocket endpoint: ws://{host}:{port}/ws")
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
