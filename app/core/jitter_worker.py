from __future__ import annotations

import time
from typing import Protocol

from PySide6.QtCore import QThread, Signal

from app.core.patterns import build_pattern
from app.hardware.ferrum import Ferrum
from app.hardware.makcu import Makcu


class MouseDriver(Protocol):
    connected: bool
    port_name: str
    baud_rate: int

    def move(self, x: float, y: float) -> None: ...

    def is_button_pressed(self, idx: int) -> bool: ...

    def cleanup(self) -> None: ...


class ConnectionWorker(QThread):
    connected = Signal(object, str)
    failed = Signal(str)

    def __init__(
        self,
        hardware: str,
        com_port: str,
        baud_rate: int,
        ferrum_mode: str = "serial",
        net_host: str = "",
        net_port: int = 8808,
        net_uuid: str = "",
    ) -> None:
        super().__init__()
        self.hardware = hardware
        self.com_port = com_port
        self.baud_rate = baud_rate
        self.ferrum_mode = ferrum_mode
        self.net_host = net_host
        self.net_port = net_port
        self.net_uuid = net_uuid

    def run(self) -> None:
        driver = None
        try:
            if self.hardware == "ferrum":
                driver = Ferrum(
                    self.com_port,
                    self.baud_rate,
                    connection_mode=self.ferrum_mode,
                    net_host=self.net_host,
                    net_port=self.net_port,
                    net_uuid=self.net_uuid,
                )
            else:
                Makcu.cleanup()
                driver = Makcu(self.com_port, self.baud_rate)

            if not driver.connected:
                raise RuntimeError(
                    f"{self.hardware.upper()} connection failed on {self.com_port}"
                )
            self.connected.emit(driver, driver.port_name or self.com_port)
        except Exception as exc:
            if driver is not None:
                driver.cleanup()
            self.failed.emit(str(exc))


class JitterWorker(QThread):
    failed = Signal(str)

    def __init__(
        self,
        driver: MouseDriver,
        delay_ms: int,
        pattern_id: str,
        amplitude: int,
        vertical_pressure_enabled: bool = False,
        vertical_pressure_amplitude: int = 1,
        vertical_pressure_delay_ms: int = 10,
    ) -> None:
        super().__init__()
        self.driver = driver
        self.delay_ms = max(1, int(delay_ms))
        self.pattern_id = pattern_id
        self.amplitude = max(1, int(amplitude))
        self.vertical_pressure_enabled = bool(vertical_pressure_enabled)
        self.vertical_pressure_amplitude = max(
            1, int(vertical_pressure_amplitude)
        )
        self.vertical_pressure_delay_ms = max(
            1, int(vertical_pressure_delay_ms)
        )

    def run(self) -> None:
        net_x = 0
        net_y = 0
        try:
            if not self.driver.connected:
                raise RuntimeError("Hardware is not connected")

            pattern = build_pattern(self.pattern_id, self.amplitude)
            index = 0
            jitter_interval = self.delay_ms / 1000.0
            pressure_interval = self.vertical_pressure_delay_ms / 1000.0
            next_jitter = time.monotonic()
            next_pressure = next_jitter

            while not self.isInterruptionRequested():
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

                if (
                    self.vertical_pressure_enabled
                    and now >= next_pressure
                ):
                    move_y += self.vertical_pressure_amplitude
                    next_pressure += pressure_interval
                    if next_pressure <= now:
                        next_pressure = now + pressure_interval

                if move_x or move_y:
                    self.driver.move(move_x, move_y)

                deadline = next_jitter
                if self.vertical_pressure_enabled:
                    deadline = min(deadline, next_pressure)
                remaining_ms = max(
                    1,
                    min(20, int((deadline - time.monotonic()) * 1000)),
                )
                self.msleep(remaining_ms)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            if self.driver.connected and (net_x or net_y):
                self.driver.move(-net_x, -net_y)


class TestMoveWorker(QThread):
    failed = Signal(str)

    def __init__(self, driver: MouseDriver, distance: int = 80) -> None:
        super().__init__()
        self.driver = driver
        self.distance = distance

    def run(self) -> None:
        try:
            if not self.driver.connected:
                raise RuntimeError("Hardware is not connected")
            self.driver.move(self.distance, 0)
            self.msleep(180)
            if self.driver.connected:
                self.driver.move(-self.distance, 0)
        except Exception as exc:
            self.failed.emit(str(exc))
