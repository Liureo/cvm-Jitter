from __future__ import annotations

import socket
import struct
import threading
import time

import serial


SUPPORTED_BAUD_RATES = (115_200, 4_000_000)
CMD_CONNECT = 0xAF3C2828
CMD_MOUSE_MOVE = 0xAEDE7345
CMD_MONITOR = 0x27388020
NET_RESPONSE_TIMEOUT = 0.7


class Ferrum:
    """Ferrum driver supporting Software API Serial and KMBox-compatible Net."""

    def __init__(
        self,
        port_name: str = "",
        baud_rate: int = 115_200,
        connection_mode: str = "serial",
        net_host: str = "192.168.2.188",
        net_port: int = 8808,
        net_uuid: str = "",
    ) -> None:
        self.connection_mode = connection_mode
        self._serial: serial.Serial | None = None
        self._socket: socket.socket | None = None
        self._monitor_socket: socket.socket | None = None
        self._lock = threading.Lock()
        self._button_lock = threading.Lock()
        self._button_states = {index: False for index in range(5)}
        self._running = False
        self._listener: threading.Thread | None = None
        self._port_name = port_name
        self._baud_rate = int(baud_rate)
        self._net_host = net_host.strip()
        self._net_port = int(net_port)
        self._net_uuid = net_uuid.strip()
        self._net_mac = 0
        self._net_rand = 0
        self._net_index = 0

        try:
            if self.connection_mode == "net":
                self._connect_net()
            else:
                self._connect_serial()
        except Exception:
            self.cleanup()
            raise

    @property
    def connected(self) -> bool:
        if not self._running:
            return False
        if self.connection_mode == "net":
            return self._socket is not None
        return bool(self._serial is not None and self._serial.is_open)

    @property
    def port_name(self) -> str:
        if self.connection_mode == "net":
            return f"{self._net_host}:{self._net_port}"
        return self._port_name

    @property
    def baud_rate(self) -> int:
        return 0 if self.connection_mode == "net" else self._baud_rate

    def _connect_serial(self) -> None:
        if self._baud_rate not in SUPPORTED_BAUD_RATES:
            raise ValueError(f"Unsupported Ferrum baud rate: {self._baud_rate}")
        self._serial = serial.Serial(
            self._port_name,
            self._baud_rate,
            timeout=0.1,
        )
        time.sleep(0.1)
        if not self._verify_serial_device():
            raise RuntimeError(
                f"Ferrum did not respond on {self._port_name} "
                f"at {self._baud_rate} baud"
            )
        self._serial.reset_input_buffer()
        self._send_serial("km.buttons(1)")
        self._running = True
        self._listener = threading.Thread(
            target=self._listen_serial,
            daemon=True,
            name="FerrumSerialListener",
        )
        self._listener.start()

    def _connect_net(self) -> None:
        if not self._net_host:
            raise ValueError("Ferrum Net IP is required")
        if not (1 <= self._net_port <= 65535):
            raise ValueError("Ferrum Net port must be between 1 and 65535")
        if len(self._net_uuid) != 8:
            raise ValueError("Ferrum Net UUID must contain 8 hexadecimal digits")
        try:
            self._net_mac = int(self._net_uuid, 16)
        except ValueError as exc:
            raise ValueError("Ferrum Net UUID must be hexadecimal") from exc

        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind(("0.0.0.0", 0))
        self._socket.connect((self._net_host, self._net_port))
        self._socket.settimeout(NET_RESPONSE_TIMEOUT)
        self._socket.send(self._build_header(0, 0, CMD_CONNECT))
        try:
            reply = self._socket.recv(64)
        except socket.timeout as exc:
            raise RuntimeError("Ferrum Net handshake timed out") from exc
        if len(reply) < 8:
            raise RuntimeError("Ferrum Net returned an invalid handshake")
        self._net_rand = struct.unpack_from("<I", reply, 4)[0]
        self._running = True

        self._monitor_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._monitor_socket.bind(("0.0.0.0", 0))
        self._monitor_socket.settimeout(0.2)
        monitor_port = self._monitor_socket.getsockname()[1]
        monitor_rand = 0xAA550000 | monitor_port
        self._send_net_command(CMD_MONITOR, rand=monitor_rand)
        self._listener = threading.Thread(
            target=self._listen_net,
            daemon=True,
            name="FerrumNetMonitor",
        )
        self._listener.start()

    def _verify_serial_device(self) -> bool:
        if self._serial is None:
            return False
        self._serial.reset_input_buffer()
        self._serial.write(b"km.version()\r\n")
        self._serial.flush()
        response = bytearray()
        deadline = time.monotonic() + 0.8
        while time.monotonic() < deadline:
            waiting = self._serial.in_waiting
            if waiting:
                response.extend(self._serial.read(waiting))
                if b"Ferrum" in response:
                    return True
                if b">>>" in response:
                    break
            time.sleep(0.01)
        return b"Ferrum" in response

    def _send_serial(self, command: str) -> None:
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Ferrum Serial is not connected")
        with self._lock:
            self._serial.write(f"{command}\r\n".encode("ascii"))
            self._serial.flush()

    def _build_header(self, rand: int, index: int, command: int) -> bytes:
        return struct.pack("<IIII", self._net_mac, rand, index, command)

    def _next_index(self) -> int:
        index = self._net_index
        self._net_index = (self._net_index + 1) & 0xFFFFFFFF
        return index

    def _send_net_command(
        self,
        command: int,
        payload: bytes = b"",
        *,
        rand: int | None = None,
    ) -> None:
        if self._socket is None:
            raise RuntimeError("Ferrum Net is not connected")
        index = self._next_index()
        packet = self._build_header(
            self._net_rand if rand is None else rand,
            index,
            command,
        ) + payload
        with self._lock:
            try:
                self._socket.send(packet)
                reply = self._socket.recv(max(64, len(packet)))
            except (socket.timeout, OSError) as exc:
                self._running = False
                raise RuntimeError(
                    f"Ferrum Net command 0x{command:08X} failed"
                ) from exc
        if len(reply) < 16:
            self._running = False
            raise RuntimeError("Ferrum Net returned an invalid response")
        _mac, _rand, reply_index, reply_command = struct.unpack_from(
            "<IIII", reply, 0
        )
        if reply_index != index or reply_command != command:
            self._running = False
            raise RuntimeError(
                "Ferrum Net response did not match the sent command"
            )

    def _listen_serial(self) -> None:
        while self._running:
            try:
                if self._serial is None or not self._serial.is_open:
                    self._running = False
                    break
                data = self._serial.read(1)
                if data:
                    value = data[0]
                    if value not in (0x0A, 0x0D, 0x20) and value <= 31:
                        self._update_buttons(value)
            except serial.SerialException:
                self._running = False
                break
            except Exception:
                time.sleep(0.001)
        self._clear_buttons()

    def _listen_net(self) -> None:
        while self._running:
            try:
                if self._monitor_socket is None:
                    break
                data, _address = self._monitor_socket.recvfrom(64)
                if len(data) >= 2:
                    raw_buttons = struct.unpack_from("<h", data, 0)[0]
                    self._update_buttons((raw_buttons >> 8) & 0x1F)
            except socket.timeout:
                continue
            except OSError:
                break
        self._clear_buttons()

    def _update_buttons(self, mask: int) -> None:
        with self._button_lock:
            for index in range(5):
                self._button_states[index] = bool(mask & (1 << index))

    def _clear_buttons(self) -> None:
        with self._button_lock:
            for index in self._button_states:
                self._button_states[index] = False

    def move(self, x: float, y: float) -> None:
        if not self.connected:
            return
        dx = max(-32768, min(32767, int(x)))
        dy = max(-32768, min(32767, int(y)))
        if self.connection_mode == "net":
            # Ferrum/KMBox Net expects the complete soft_mouse_t structure:
            # button, x, y, wheel, followed by ten trajectory points.
            payload = struct.pack("<14i", 0, dx, dy, 0, *([0] * 10))
            self._send_net_command(CMD_MOUSE_MOVE, payload)
        else:
            self._send_serial(f"km.move({dx}, {dy})")

    def is_button_pressed(self, idx: int) -> bool:
        with self._button_lock:
            return self._button_states.get(idx, False)

    def cleanup(self) -> None:
        if self.connection_mode == "net" and self._socket is not None:
            try:
                self._send_net_command(CMD_MONITOR, rand=0)
            except Exception:
                pass
        self._running = False
        if self._serial is not None and self._serial.is_open:
            try:
                self._send_serial("km.buttons(0)")
            except Exception:
                pass
            try:
                self._serial.close()
            except Exception:
                pass
        for sock in (self._monitor_socket, self._socket):
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
        self._serial = None
        self._monitor_socket = None
        self._socket = None
        self._clear_buttons()
