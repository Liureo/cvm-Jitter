from __future__ import annotations

import threading
import time
from typing import Protocol

from serial.tools import list_ports

from app.core.config_store import ConfigStore
from app.core.patterns import PATTERN_IDS, build_pattern
from app.hardware.ferrum import Ferrum
from app.hardware.makcu import Makcu


CONNECTION_FIELDS = {
    "hardware",
    "ferrum_mode",
    "com_port",
    "baud_rate",
    "net_host",
    "net_port",
    "net_uuid",
}
RUNTIME_FIELDS = {
    "pattern",
    "amplitude",
    "delay_ms",
    "vertical_pressure_enabled",
    "vertical_pressure_amplitude",
    "vertical_pressure_delay_ms",
    "trigger_mode",
    "trigger_button",
    "ads_required",
    "ads_button",
}
GENERAL_FIELDS = {
    "language",
    "webui_enabled",
    "separate_web_theme",
    "local_theme",
    "web_theme",
}
ALLOWED_FIELDS = CONNECTION_FIELDS | RUNTIME_FIELDS | GENERAL_FIELDS


class MouseDriver(Protocol):
    connected: bool
    port_name: str
    baud_rate: int

    def move(self, x: float, y: float) -> None: ...

    def is_button_pressed(self, idx: int) -> bool: ...

    def cleanup(self) -> None: ...


class MotionRunner:
    def __init__(
        self,
        driver: MouseDriver,
        config: dict,
        failed_callback,
    ) -> None:
        self.driver = driver
        self.config = dict(config)
        self.failed_callback = failed_callback
        self._stop_event = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="HeadlessMotionRunner",
        )

    @property
    def running(self) -> bool:
        return self._thread.is_alive()

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=3)

    def _run(self) -> None:
        net_x = 0
        net_y = 0
        try:
            if not self.driver.connected:
                raise RuntimeError("Hardware is not connected")

            delay_ms = max(1, int(self.config.get("delay_ms", 10)))
            amplitude = max(1, int(self.config.get("amplitude", 3)))
            pattern_id = str(self.config.get("pattern", "upper_left"))
            if pattern_id not in PATTERN_IDS:
                pattern_id = "upper_left"
            pressure_enabled = bool(
                self.config.get("vertical_pressure_enabled", False)
            )
            pressure_amplitude = max(
                1,
                int(self.config.get("vertical_pressure_amplitude", 1)),
            )
            pressure_delay_ms = max(
                1,
                int(self.config.get("vertical_pressure_delay_ms", 10)),
            )
            pattern = build_pattern(pattern_id, amplitude)
            index = 0
            jitter_interval = delay_ms / 1000.0
            pressure_interval = pressure_delay_ms / 1000.0
            next_jitter = time.monotonic()
            next_pressure = next_jitter

            while not self._stop_event.is_set():
                if not self.driver.connected:
                    raise RuntimeError("Hardware connection was lost")

                now = time.monotonic()
                move_x = 0
                move_y = 0

                if now >= next_jitter:
                    dx, dy = pattern[index]
                    move_x += dx
                    move_y += dy
                    net_x += dx
                    net_y += dy
                    index = (index + 1) % len(pattern)
                    next_jitter += jitter_interval
                    if next_jitter <= now:
                        next_jitter = now + jitter_interval

                if pressure_enabled and now >= next_pressure:
                    move_y += pressure_amplitude
                    next_pressure += pressure_interval
                    if next_pressure <= now:
                        next_pressure = now + pressure_interval

                if move_x or move_y:
                    self.driver.move(move_x, move_y)

                deadline = next_jitter
                if pressure_enabled:
                    deadline = min(deadline, next_pressure)
                remaining = max(0.001, min(0.02, deadline - time.monotonic()))
                self._stop_event.wait(remaining)
        except Exception as exc:
            self.failed_callback(str(exc))
        finally:
            if self.driver.connected and (net_x or net_y):
                self.driver.move(-net_x, -net_y)


class HeadlessController:
    def __init__(self) -> None:
        self.config_store = ConfigStore()
        self.config = self.config_store.load()
        self.driver: MouseDriver | None = None
        self.armed = False
        self.toggle_active = False
        self.last_trigger_pressed = False
        self.connection_status = "Not connected"
        self.run_status = "Idle"
        self._motion: MotionRunner | None = None
        self._test_thread: threading.Thread | None = None
        self._state_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._trigger_thread = threading.Thread(
            target=self._trigger_loop,
            daemon=True,
            name="HeadlessTriggerPoller",
        )

    def start(self) -> None:
        if not self._trigger_thread.is_alive():
            self._trigger_thread.start()

    def shutdown(self) -> None:
        self._stop_event.set()
        self.disarm_jitter()
        if self._trigger_thread.is_alive():
            self._trigger_thread.join(timeout=3)
        if self._test_thread and self._test_thread.is_alive():
            self._test_thread.join(timeout=3)
        self.disconnect_hardware()

    def state(self) -> dict:
        with self._state_lock:
            config = dict(self.config)
            connected = bool(self.driver and self.driver.connected)
            armed = self.armed
            connection_status = self.connection_status
            run_status = self.run_status
            motion_running = self._motion_running_locked()
        config["web_theme"] = self._effective_web_theme(config)
        config.update(
            {
                "ports": self._list_ports(),
                "connected": connected,
                "armed": armed,
                "motion_running": motion_running,
                "connection_status": connection_status,
                "run_status": run_status,
            }
        )
        return config

    def handle_command(self, command: str, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        if command == "connect":
            self.connect_hardware()
        elif command == "disconnect":
            self.disconnect_hardware()
        elif command == "start":
            self.arm_jitter()
        elif command == "stop":
            self.disarm_jitter()
        elif command == "test":
            self.test_move()
        elif command == "config":
            self.apply_config(data)

    def apply_config(self, data: dict) -> None:
        with self._state_lock:
            connected = bool(self.driver and self.driver.connected)
            armed = self.armed
            next_config = dict(self.config)
            for key, value in data.items():
                if key not in ALLOWED_FIELDS:
                    continue
                if connected and key in CONNECTION_FIELDS:
                    continue
                if armed and key in RUNTIME_FIELDS:
                    continue
                next_config[key] = value
            self.config = self._normalize_config(next_config)
            self.config_store.save(self.config)

    def connect_hardware(self) -> None:
        with self._state_lock:
            if self.driver and self.driver.connected:
                return
            self.connection_status = "Connecting..."
            config = dict(self.config)

        driver = None
        try:
            hardware = str(config.get("hardware", "makcu"))
            if hardware == "ferrum":
                driver = Ferrum(
                    str(config.get("com_port", "")),
                    int(config.get("baud_rate", 115_200)),
                    connection_mode=str(config.get("ferrum_mode", "serial")),
                    net_host=str(config.get("net_host", "")),
                    net_port=int(config.get("net_port", 8808)),
                    net_uuid=str(config.get("net_uuid", "")),
                )
            else:
                Makcu.cleanup()
                driver = Makcu(
                    str(config.get("com_port", "")),
                    int(config.get("baud_rate", 115_200)),
                )
            if not driver.connected:
                raise RuntimeError(f"{hardware.upper()} connection failed")
        except Exception as exc:
            if driver is not None:
                driver.cleanup()
            with self._state_lock:
                self.driver = None
                self.connection_status = f"Connection failed: {exc}"
                self.run_status = "Idle"
            return

        with self._state_lock:
            self.driver = driver
            baud = (
                "Net"
                if hardware == "ferrum" and str(config.get("ferrum_mode")) == "net"
                else driver.baud_rate
            )
            self.connection_status = (
                f"Connected: {driver.port_name or config.get('com_port', '')} @ {baud}"
            )
            if self.armed:
                self._activate_arm_state_locked()

    def disconnect_hardware(self) -> None:
        self.disarm_jitter()
        with self._state_lock:
            driver = self.driver
            self.driver = None
            self.connection_status = "Not connected"
        if driver:
            driver.cleanup()

    def arm_jitter(self) -> None:
        with self._state_lock:
            if self.armed:
                return
            if not (self.driver and self.driver.connected):
                self.run_status = "Waiting for connection"
                connect_needed = True
            else:
                connect_needed = False

        if connect_needed:
            self.connect_hardware()

        with self._state_lock:
            if not (self.driver and self.driver.connected):
                return
            self._activate_arm_state_locked()

    def disarm_jitter(self) -> None:
        motion = None
        with self._state_lock:
            self.armed = False
            self.toggle_active = False
            self.last_trigger_pressed = False
            motion = self._motion
            self._motion = None
            self.run_status = "Idle"
        if motion:
            motion.stop()

    def test_move(self) -> None:
        with self._state_lock:
            if not (self.driver and self.driver.connected):
                return
            if self._test_thread and self._test_thread.is_alive():
                return
            driver = self.driver
        self._test_thread = threading.Thread(
            target=self._run_test_move,
            args=(driver,),
            daemon=True,
            name="HeadlessTestMove",
        )
        self._test_thread.start()

    def _run_test_move(self, driver: MouseDriver) -> None:
        try:
            if driver.connected:
                driver.move(80, 0)
                time.sleep(0.18)
            if driver.connected:
                driver.move(-80, 0)
        except Exception as exc:
            with self._state_lock:
                self.run_status = f"Test move failed: {exc}"

    def _trigger_loop(self) -> None:
        while not self._stop_event.wait(0.01):
            self._poll_trigger()

    def _poll_trigger(self) -> None:
        with self._state_lock:
            driver = self.driver
            if driver and not driver.connected:
                lost = True
            else:
                lost = False
            if lost:
                self.armed = False
                self.toggle_active = False
                self.last_trigger_pressed = False
                motion = self._motion
                self._motion = None
                self.driver = None
                self.connection_status = "Connection lost"
                self.run_status = "Idle"
            else:
                motion = None

        if motion:
            motion.stop()
        if lost:
            if driver:
                driver.cleanup()
            return

        with self._state_lock:
            if not self.armed or not self.driver:
                return
            driver = self.driver
            config = dict(self.config)

        mode = str(config.get("trigger_mode", "hold"))
        ads_required = bool(config.get("ads_required", False))
        ads_button = self._button_index(config.get("ads_button", 1))
        ads_pressed = not ads_required or driver.is_button_pressed(ads_button)

        if mode == "always":
            with self._state_lock:
                if ads_pressed and not self._motion_running_locked():
                    self.run_status = "Running"
                    self._start_motion_locked()
                elif not ads_pressed and self._motion_running_locked():
                    motion = self._motion
                    self._motion = None
                    self.run_status = "Waiting for ADS"
                else:
                    motion = None
            if motion:
                motion.stop()
            return

        button_index = self._button_index(config.get("trigger_button", 0))
        pressed = driver.is_button_pressed(button_index)
        motion = None
        with self._state_lock:
            if mode == "hold":
                if pressed and ads_pressed and not self._motion_running_locked():
                    self.run_status = "Hold running"
                    self._start_motion_locked()
                elif (not pressed or not ads_pressed) and self._motion_running_locked():
                    motion = self._motion
                    self._motion = None
                    self.run_status = (
                        "Waiting for ADS"
                        if ads_required and not ads_pressed
                        else "Armed"
                    )
                elif not pressed:
                    self.run_status = (
                        "Waiting for ADS"
                        if ads_required and not ads_pressed
                        else "Armed"
                    )
            elif mode == "toggle" and not ads_pressed:
                if self.toggle_active or self._motion_running_locked():
                    self.toggle_active = False
                    motion = self._motion
                    self._motion = None
                self.run_status = "Waiting for ADS"
            elif pressed and not self.last_trigger_pressed:
                self.toggle_active = not self.toggle_active
                if self.toggle_active:
                    self.run_status = "Toggle on"
                    self._start_motion_locked()
                else:
                    motion = self._motion
                    self._motion = None
                    self.run_status = "Toggle off"
            elif not self.toggle_active and self.run_status == "Waiting for ADS":
                self.run_status = "Armed"
            self.last_trigger_pressed = pressed
        if motion:
            motion.stop()

    def _activate_arm_state_locked(self) -> None:
        self.armed = True
        self.toggle_active = False
        self.last_trigger_pressed = False
        if str(self.config.get("trigger_mode", "hold")) == "always":
            if bool(self.config.get("ads_required", False)):
                self.run_status = "Waiting for ADS"
            else:
                self.run_status = "Running"
                self._start_motion_locked()
        else:
            self.run_status = (
                "Waiting for ADS"
                if bool(self.config.get("ads_required", False))
                else "Armed"
            )

    def _start_motion_locked(self) -> None:
        if self._motion_running_locked() or not (self.driver and self.driver.connected):
            return
        self._motion = MotionRunner(
            self.driver,
            dict(self.config),
            self._on_motion_failed,
        )
        self._motion.start()

    def _on_motion_failed(self, message: str) -> None:
        with self._state_lock:
            self.armed = False
            self.toggle_active = False
            self._motion = None
            self.run_status = f"Jitter failed: {message}"

    def _motion_running_locked(self) -> bool:
        return bool(self._motion and self._motion.running)

    def _effective_web_theme(self, config: dict) -> dict:
        if bool(config.get("separate_web_theme", False)):
            return dict(config.get("web_theme", {}))
        return dict(config.get("local_theme", {}))

    @staticmethod
    def _list_ports() -> list[dict[str, str]]:
        return [
            {"device": port.device, "description": port.description}
            for port in list_ports.comports()
        ]

    @staticmethod
    def _button_index(value) -> int:
        try:
            index = int(value)
        except (TypeError, ValueError):
            return 0
        return max(0, min(4, index))

    def _normalize_config(self, config: dict) -> dict:
        normalized = dict(config)
        normalized["language"] = str(normalized.get("language", "zh_TW"))
        pattern = str(normalized.get("pattern", "upper_left"))
        normalized["pattern"] = pattern if pattern in PATTERN_IDS else "upper_left"
        normalized["hardware"] = (
            "ferrum" if str(normalized.get("hardware")) == "ferrum" else "makcu"
        )
        normalized["ferrum_mode"] = (
            "net" if str(normalized.get("ferrum_mode")) == "net" else "serial"
        )
        normalized["com_port"] = str(normalized.get("com_port", "")).strip()
        normalized["net_host"] = str(normalized.get("net_host", "")).strip()
        normalized["net_uuid"] = str(normalized.get("net_uuid", "")).strip()
        normalized["net_port"] = self._clamp_int(
            normalized.get("net_port", 8808),
            1,
            65535,
            8808,
        )
        try:
            baud = int(normalized.get("baud_rate", 115_200))
        except (TypeError, ValueError):
            baud = 115_200
        normalized["baud_rate"] = 4_000_000 if baud == 4_000_000 else 115_200
        normalized["amplitude"] = self._clamp_int(
            normalized.get("amplitude", 3),
            1,
            500,
            3,
        )
        normalized["delay_ms"] = self._clamp_int(
            normalized.get("delay_ms", 10),
            1,
            5000,
            10,
        )
        normalized["vertical_pressure_enabled"] = bool(
            normalized.get("vertical_pressure_enabled", False)
        )
        normalized["vertical_pressure_amplitude"] = self._clamp_int(
            normalized.get("vertical_pressure_amplitude", 1),
            1,
            500,
            1,
        )
        normalized["vertical_pressure_delay_ms"] = self._clamp_int(
            normalized.get("vertical_pressure_delay_ms", 10),
            1,
            5000,
            10,
        )
        mode = str(normalized.get("trigger_mode", "hold"))
        normalized["trigger_mode"] = (
            mode if mode in {"hold", "toggle", "always"} else "hold"
        )
        normalized["trigger_button"] = self._button_index(
            normalized.get("trigger_button", 0)
        )
        normalized["ads_required"] = bool(normalized.get("ads_required", False))
        normalized["ads_button"] = self._button_index(normalized.get("ads_button", 1))
        normalized["webui_enabled"] = bool(normalized.get("webui_enabled", True))
        normalized["separate_web_theme"] = bool(
            normalized.get("separate_web_theme", False)
        )
        return normalized

    @staticmethod
    def _clamp_int(value, minimum: int, maximum: int, fallback: int) -> int:
        try:
            number = int(value)
        except (TypeError, ValueError):
            number = fallback
        return max(minimum, min(maximum, number))
