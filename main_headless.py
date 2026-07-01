from __future__ import annotations

import argparse
import signal
import sys
import threading

from app.core.headless_controller import HeadlessController
from app.web.server import WebUIServer


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run cvm Jitter as a headless WebUI service.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="WebUI listen port. Default: 8765.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    stop_event = threading.Event()
    controller = HeadlessController()
    server = WebUIServer(
        port=args.port,
        command_handler=controller.handle_command,
        state_provider=controller.state,
    )

    def request_stop(_signum, _frame) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    controller.start()
    server.start()
    print(f"[INFO] cvm Jitter headless WebUI: {server.lan_url}")
    try:
        stop_event.wait()
    finally:
        server.stop()
        controller.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
