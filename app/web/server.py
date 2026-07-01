from __future__ import annotations

import socket
import threading
from pathlib import Path
from typing import Callable

from flask import Flask, jsonify, render_template, request
from werkzeug.serving import make_server

try:
    from PySide6.QtCore import QObject, Signal
except ImportError:
    QObject = object
    Signal = None


if Signal is not None:
    class WebBridge(QObject):
        command = Signal(str, object)
else:
    class WebBridge(QObject):
        def __init__(self) -> None:
            self.command = None


class WebUIServer:
    def __init__(
        self,
        bridge: WebBridge | None = None,
        port: int = 8765,
        command_handler: Callable[[str, object], object] | None = None,
        state_provider: Callable[[], dict] | None = None,
    ) -> None:
        web_root = Path(__file__).resolve().parent
        self.app = Flask(
            __name__,
            template_folder=str(web_root / "templates"),
            static_folder=str(web_root / "static"),
        )
        self.bridge = bridge
        self.port = port
        self.command_handler = command_handler
        self.state_provider = state_provider
        self._server = None
        self._thread: threading.Thread | None = None
        self._state_lock = threading.Lock()
        self._state: dict = {}
        self._configure_routes()

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def lan_url(self) -> str:
        return f"http://{self._lan_ip()}:{self.port}"

    def update_state(self, state: dict) -> None:
        with self._state_lock:
            self._state = dict(state)

    def start(self) -> None:
        if self.running:
            return
        self._server = make_server(
            "0.0.0.0",
            self.port,
            self.app,
            threaded=True,
        )
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
            name="HardwareJitterWebUI",
        )
        self._thread.start()

    def stop(self) -> None:
        server = self._server
        if server is not None:
            server.shutdown()
            server.server_close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._server = None
        self._thread = None

    def _configure_routes(self) -> None:
        @self.app.get("/")
        def index():
            return render_template("index.html")

        @self.app.get("/api/state")
        def state():
            if self.state_provider is not None:
                return jsonify(self.state_provider())
            with self._state_lock:
                return jsonify(dict(self._state))

        @self.app.post("/api/config")
        def update_config():
            payload = request.get_json(silent=True) or {}
            self._emit_command("config", payload)
            return jsonify({"ok": True})

        @self.app.post("/api/action")
        def action():
            payload = request.get_json(silent=True) or {}
            action_name = str(payload.get("action", ""))
            if action_name not in {"connect", "disconnect", "start", "stop", "test"}:
                return jsonify({"ok": False, "error": "Invalid action"}), 400
            self._emit_command(action_name, {})
            return jsonify({"ok": True})

    def _emit_command(self, command: str, payload: object) -> None:
        if self.command_handler is not None:
            self.command_handler(command, payload)
            return
        if self.bridge is not None and getattr(self.bridge, "command", None) is not None:
            self.bridge.command.emit(command, payload)

    @staticmethod
    def _lan_ip() -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                return str(sock.getsockname()[0])
        except OSError:
            try:
                return socket.gethostbyname(socket.gethostname())
            except OSError:
                return "127.0.0.1"
