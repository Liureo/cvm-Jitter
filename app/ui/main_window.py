from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QColorDialog, QComboBox, QMainWindow, QMessageBox
from serial.tools import list_ports

from app.core.config_store import ConfigStore
from app.core.jitter_worker import (
    ConnectionWorker,
    JitterWorker,
    MouseDriver,
    TestMoveWorker,
)
from app.core.patterns import PATTERN_IDS
from app.core.theme import THEME_KEYS, normalize_theme
from app.i18n.translator import Translator
from app.ui.layout import build_main_window
from app.ui.styles import build_stylesheet
from app.web.server import WebBridge, WebUIServer


TRIGGER_MODE_IDS = ("hold", "toggle", "always")
TRIGGER_BUTTON_IDS = (0, 1, 2, 3, 4)
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config_store = ConfigStore()
        self.config = self.config_store.load()
        self.local_theme = normalize_theme(self.config.get("local_theme"))
        self.web_theme = normalize_theme(self.config.get("web_theme"))
        self.translator = Translator(str(self.config.get("language", "zh_TW")))
        self.driver: MouseDriver | None = None
        self.connection_worker: ConnectionWorker | None = None
        self.jitter_worker: JitterWorker | None = None
        self.test_move_worker: TestMoveWorker | None = None
        self.armed = False
        self.pending_arm = False
        self.toggle_active = False
        self.last_trigger_pressed = False
        self.connection_state = ("not_connected", {})
        self.run_state = ("idle", {})
        self.web_bridge = WebBridge()
        self.web_bridge.command.connect(self._handle_web_command)
        self.web_server = WebUIServer(self.web_bridge)

        self.setMinimumSize(720, 960)
        self.resize(720, 960)
        build_main_window(self)
        self._load_config()
        self._apply_local_theme()
        self._connect_auto_save()
        self.refresh_ports()
        self.retranslate_ui()

        self.trigger_timer = QTimer(self)
        self.trigger_timer.setInterval(10)
        self.trigger_timer.timeout.connect(self._poll_trigger)
        self.trigger_timer.start()

        self.web_state_timer = QTimer(self)
        self.web_state_timer.setInterval(300)
        self.web_state_timer.timeout.connect(self._publish_web_state)
        self.web_state_timer.start()

        if bool(self.config.get("webui_enabled", False)):
            self._toggle_webui(True)

    def _load_config(self) -> None:
        self.delay_spin.setValue(int(self.config.get("delay_ms", 10)))
        self.amplitude_spin.setValue(int(self.config.get("amplitude", 3)))
        self.pressure_amplitude_spin.setValue(
            int(self.config.get("vertical_pressure_amplitude", 1))
        )
        self.pressure_delay_spin.setValue(
            int(self.config.get("vertical_pressure_delay_ms", 10))
        )
        self.vertical_pressure_checkbox.setChecked(
            bool(self.config.get("vertical_pressure_enabled", False))
        )
        self.separate_web_theme_checkbox.setChecked(
            bool(self.config.get("separate_web_theme", False))
        )
        self._set_combo_data(
            self.language_combo, str(self.config.get("language", "zh_TW"))
        )
        self._set_combo_data(
            self.hardware_combo, str(self.config.get("hardware", "makcu"))
        )
        self._set_combo_data(
            self.ferrum_mode_combo,
            str(self.config.get("ferrum_mode", "serial")),
        )
        self.net_host_edit.setText(
            str(self.config.get("net_host", "192.168.2.188"))
        )
        self.net_port_spin.setValue(int(self.config.get("net_port", 8808)))
        self.net_uuid_edit.setText(str(self.config.get("net_uuid", "")))
        self._set_combo_data(
            self.baud_combo, int(self.config.get("baud_rate", 115_200))
        )
        self.web_enable_checkbox.blockSignals(True)
        self.web_enable_checkbox.setChecked(
            bool(self.config.get("webui_enabled", False))
        )
        self.web_enable_checkbox.blockSignals(False)
        self.saved_port = str(self.config.get("com_port", ""))
        self._rebuild_pattern_combo(str(self.config.get("pattern", "upper_left")))
        self._rebuild_trigger_combos(
            str(self.config.get("trigger_mode", "hold")),
            int(self.config.get("trigger_button", 0)),
        )
        self._update_connection_fields()
        self._update_vertical_pressure_fields()

    def _connect_auto_save(self) -> None:
        for signal in (
            self.delay_spin.valueChanged,
            self.amplitude_spin.valueChanged,
            self.pattern_combo.currentIndexChanged,
            self.vertical_pressure_checkbox.toggled,
            self.pressure_amplitude_spin.valueChanged,
            self.pressure_delay_spin.valueChanged,
            self.separate_web_theme_checkbox.toggled,
            self.trigger_mode_combo.currentIndexChanged,
            self.trigger_button_combo.currentIndexChanged,
            self.baud_combo.currentIndexChanged,
            self.hardware_combo.currentIndexChanged,
            self.ferrum_mode_combo.currentIndexChanged,
            self.net_host_edit.textChanged,
            self.net_port_spin.valueChanged,
            self.net_uuid_edit.textChanged,
            self.port_combo.currentTextChanged,
        ):
            signal.connect(self._save_config)
        self.hardware_combo.currentIndexChanged.connect(
            self._update_connection_fields
        )
        self.ferrum_mode_combo.currentIndexChanged.connect(
            self._update_connection_fields
        )

    def _save_config(self, *_args) -> None:
        self.config_store.save(
            {
                "language": self.translator.language,
                "webui_enabled": self.web_enable_checkbox.isChecked(),
                "hardware": str(self.hardware_combo.currentData() or "makcu"),
                "ferrum_mode": str(
                    self.ferrum_mode_combo.currentData() or "serial"
                ),
                "net_host": self.net_host_edit.text().strip(),
                "net_port": self.net_port_spin.value(),
                "net_uuid": self.net_uuid_edit.text().strip(),
                "com_port": self._selected_port(),
                "baud_rate": int(self.baud_combo.currentData() or 115_200),
                "delay_ms": self.delay_spin.value(),
                "pattern": str(self.pattern_combo.currentData() or "upper_left"),
                "amplitude": self.amplitude_spin.value(),
                "vertical_pressure_enabled": (
                    self.vertical_pressure_checkbox.isChecked()
                ),
                "vertical_pressure_amplitude": (
                    self.pressure_amplitude_spin.value()
                ),
                "vertical_pressure_delay_ms": self.pressure_delay_spin.value(),
                "separate_web_theme": (
                    self.separate_web_theme_checkbox.isChecked()
                ),
                "local_theme": dict(self.local_theme),
                "web_theme": dict(self.web_theme),
                "trigger_mode": str(
                    self.trigger_mode_combo.currentData() or "hold"
                ),
                "trigger_button": int(
                    self.trigger_button_combo.currentData()
                    if self.trigger_button_combo.currentData() is not None
                    else 0
                ),
            }
        )
        self.save_label.setText(self.tr_text("saved"))

    def _change_language(self, _index: int) -> None:
        language = self.language_combo.currentData()
        if not language:
            return
        pattern = self.pattern_combo.currentData()
        trigger_mode = self.trigger_mode_combo.currentData()
        trigger_button = self.trigger_button_combo.currentData()
        self.translator.set_language(str(language))
        self._rebuild_pattern_combo(str(pattern or "upper_left"))
        self._rebuild_trigger_combos(
            str(trigger_mode or "hold"),
            int(trigger_button if trigger_button is not None else 0),
        )
        self.retranslate_ui()
        self._save_config()

    def retranslate_ui(self) -> None:
        self.setWindowTitle(self.tr_text("window_title"))
        self.title_label.setText(self.tr_text("app_title"))
        self.subtitle_label.setText(self.tr_text("subtitle"))
        self.save_label.setText(self.tr_text("saved"))
        self.language_label.setText(self.tr_text("language"))
        self.tabs.setTabText(0, self.tr_text("tab_hardware"))
        self.tabs.setTabText(1, self.tr_text("tab_settings"))
        self.tabs.setTabText(2, self.tr_text("tab_advanced"))
        self.tabs.setTabText(3, self.tr_text("tab_theme"))
        self.connection_title.setText(self.tr_text("connection_title"))
        self.connection_description.setText(
            self.tr_text("connection_description")
        )
        self.hardware_label.setText(self.tr_text("hardware"))
        self.ferrum_mode_label.setText(self.tr_text("connection_mode"))
        self.net_host_label.setText(self.tr_text("net_host"))
        self.net_port_label.setText(self.tr_text("net_port"))
        self.net_uuid_label.setText(self.tr_text("net_uuid"))
        self.port_label.setText(self.tr_text("com_port"))
        self.port_combo.setPlaceholderText(self.tr_text("port_placeholder"))
        self.refresh_button.setText(self.tr_text("refresh"))
        self.test_move_button.setText(self.tr_text("test_move"))
        self.baud_label.setText(self.tr_text("baud_rate"))
        self.jitter_title.setText(self.tr_text("jitter_title"))
        self.jitter_description.setText(self.tr_text("jitter_description"))
        self.pattern_label.setText(self.tr_text("pattern"))
        self.amplitude_label.setText(self.tr_text("amplitude"))
        self.delay_label.setText(self.tr_text("delay"))
        self.pressure_title.setText(self.tr_text("pressure_title"))
        self.pressure_description.setText(
            self.tr_text("pressure_description")
        )
        self.vertical_pressure_checkbox.setText(
            self.tr_text("pressure_enable")
        )
        self.pressure_amplitude_label.setText(
            self.tr_text("pressure_amplitude")
        )
        self.pressure_delay_label.setText(self.tr_text("pressure_delay"))
        self.local_theme_title.setText(self.tr_text("local_theme_title"))
        self.local_theme_description.setText(
            self.tr_text("local_theme_description")
        )
        self.separate_web_theme_checkbox.setText(
            self.tr_text("separate_web_theme")
        )
        self.web_theme_title.setText(self.tr_text("web_theme_title"))
        self.web_theme_description.setText(
            self.tr_text("web_theme_description")
        )
        for scope in ("local", "web"):
            for key in THEME_KEYS:
                self.theme_labels[scope][key].setText(
                    self.tr_text(f"theme_{key}")
                )
        self.trigger_title.setText(self.tr_text("trigger_title"))
        self.trigger_description.setText(self.tr_text("trigger_description"))
        self.web_title.setText(self.tr_text("web_title"))
        self.web_description.setText(self.tr_text("web_description"))
        self.web_enable_checkbox.setText(self.tr_text("web_enable"))
        self.trigger_mode_label.setText(self.tr_text("trigger_mode"))
        self.trigger_button_label.setText(self.tr_text("trigger_button"))
        self.start_button.setText(self.tr_text("enable"))
        self.stop_button.setText(self.tr_text("stop"))
        self._render_connection_state()
        self._render_run_state()
        self._render_web_address()
        self._update_connection_fields()
        self._update_theme_controls()

    def tr_text(self, key: str, **values) -> str:
        return self.translator.text(key, **values)

    def _rebuild_pattern_combo(self, selected: str) -> None:
        self.pattern_combo.blockSignals(True)
        self.pattern_combo.clear()
        for pattern_id in PATTERN_IDS:
            self.pattern_combo.addItem(
                self.tr_text(f"pattern_{pattern_id}"), pattern_id
            )
        self._set_combo_data(self.pattern_combo, selected)
        self.pattern_combo.blockSignals(False)

    def _rebuild_trigger_combos(self, selected_mode: str, selected_button: int) -> None:
        self.trigger_mode_combo.blockSignals(True)
        self.trigger_mode_combo.clear()
        for mode in TRIGGER_MODE_IDS:
            self.trigger_mode_combo.addItem(self.tr_text(f"trigger_{mode}"), mode)
        self._set_combo_data(self.trigger_mode_combo, selected_mode)
        self.trigger_mode_combo.blockSignals(False)

        self.trigger_button_combo.blockSignals(True)
        self.trigger_button_combo.clear()
        button_keys = ("left", "right", "middle", "side1", "side2")
        for index, key in zip(TRIGGER_BUTTON_IDS, button_keys):
            self.trigger_button_combo.addItem(self.tr_text(f"button_{key}"), index)
        self._set_combo_data(self.trigger_button_combo, selected_button)
        self.trigger_button_combo.blockSignals(False)
        self._on_trigger_mode_changed()

    def refresh_ports(self) -> None:
        selected = self._selected_port() or getattr(self, "saved_port", "")
        ports = [(port.device, port.description) for port in list_ports.comports()]
        self.port_combo.blockSignals(True)
        self.port_combo.clear()
        for port, description in ports:
            self.port_combo.addItem(f"{port} - {description}", port)
        index = self.port_combo.findData(selected)
        if index >= 0:
            self.port_combo.setCurrentIndex(index)
        elif selected:
            self.port_combo.setEditText(selected)
        elif ports:
            self.port_combo.setCurrentIndex(0)
        self.saved_port = ""
        self.port_combo.blockSignals(False)
        if hasattr(self, "save_label"):
            self._save_config()

    def _selected_port(self) -> str:
        return self.port_combo.currentText().split(" - ", 1)[0].strip()

    def toggle_connection(self) -> None:
        if self.driver and self.driver.connected:
            self.disconnect_hardware()
        else:
            self.connect_hardware()

    def connect_hardware(self, arm_after_connect: bool = False) -> None:
        if self.connection_worker and self.connection_worker.isRunning():
            return
        port = self._selected_port()
        using_net = (
            self.hardware_combo.currentData() == "ferrum"
            and self.ferrum_mode_combo.currentData() == "net"
        )
        if not using_net and not port:
            QMessageBox.warning(
                self,
                self.tr_text("missing_port_title"),
                self.tr_text("missing_port"),
            )
            return
        if using_net and (
            not self.net_host_edit.text().strip()
            or not self.net_uuid_edit.text().strip()
        ):
            QMessageBox.warning(
                self,
                self.tr_text("connection_failed_title"),
                "Ferrum Net requires IP, Port, and UUID.",
            )
            return

        self.pending_arm = arm_after_connect
        self._save_config()
        self._set_connection_state("connecting", port=port)
        self.connection_dot.setStyleSheet("color: #d29922;")
        self.connect_button.setEnabled(False)
        self._set_connection_settings_enabled(False)

        self.connection_worker = ConnectionWorker(
            str(self.hardware_combo.currentData()),
            port,
            int(self.baud_combo.currentData()),
            ferrum_mode=str(self.ferrum_mode_combo.currentData() or "serial"),
            net_host=self.net_host_edit.text().strip(),
            net_port=self.net_port_spin.value(),
            net_uuid=self.net_uuid_edit.text().strip(),
        )
        self.connection_worker.connected.connect(self._on_connected)
        self.connection_worker.failed.connect(self._on_connection_failed)
        self.connection_worker.finished.connect(self._on_connection_finished)
        self.connection_worker.start()

    def _on_connected(self, driver: MouseDriver, port: str) -> None:
        self.driver = driver
        self.connection_dot.setStyleSheet("color: #3fb950;")
        connection_port = driver.port_name or port
        connection_baud = (
            "Net"
            if self.hardware_combo.currentData() == "ferrum"
            and self.ferrum_mode_combo.currentData() == "net"
            else str(int(driver.baud_rate))
        )
        self._set_connection_state(
            "connected",
            hardware=self.hardware_combo.currentText(),
            port=connection_port,
            baud=connection_baud,
        )
        self.connect_button.setEnabled(True)
        self.test_move_button.setEnabled(True)
        if self.pending_arm:
            self.pending_arm = False
            self._activate_arm_state()

    def _on_connection_failed(self, message: str) -> None:
        self.pending_arm = False
        self.driver = None
        self.connection_dot.setStyleSheet("color: #f85149;")
        self._set_connection_state("connection_failed")
        self._set_run_state("idle")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.test_move_button.setEnabled(False)
        QMessageBox.critical(
            self,
            self.tr_text("connection_failed_title"),
            message,
        )

    def _on_connection_finished(self) -> None:
        self.connection_worker = None
        if not (self.driver and self.driver.connected):
            self.connect_button.setEnabled(True)
            self._set_connection_settings_enabled(True)

    def disconnect_hardware(self) -> None:
        self.disarm_jitter()
        if self.test_move_worker and self.test_move_worker.isRunning():
            self.test_move_worker.wait()
        self.test_move_worker = None
        if self.driver:
            self.driver.cleanup()
        self.driver = None
        self.connection_dot.setStyleSheet("color: #6e7681;")
        self._set_connection_state("not_connected")
        self.test_move_button.setEnabled(False)
        self._set_connection_settings_enabled(True)

    def test_move(self) -> None:
        if not (self.driver and self.driver.connected):
            return
        if self.test_move_worker and self.test_move_worker.isRunning():
            return
        self.test_move_button.setEnabled(False)
        self.test_move_worker = TestMoveWorker(self.driver)
        self.test_move_worker.failed.connect(self._on_test_move_failed)
        self.test_move_worker.finished.connect(self._on_test_move_finished)
        self.test_move_worker.start()

    def _on_test_move_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            self.tr_text("test_move_error_title"),
            message,
        )

    def _on_test_move_finished(self) -> None:
        self.test_move_worker = None
        self.test_move_button.setEnabled(
            bool(self.driver and self.driver.connected)
        )

    def arm_jitter(self) -> None:
        if self.armed or self.pending_arm:
            return
        if not (self.driver and self.driver.connected):
            self._set_run_state("waiting_connection")
            self.connect_hardware(arm_after_connect=True)
            return
        self._activate_arm_state()

    def _activate_arm_state(self) -> None:
        self.armed = True
        self.toggle_active = False
        self.last_trigger_pressed = False
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.test_move_button.setEnabled(False)
        self._set_runtime_settings_enabled(False)
        if self.trigger_mode_combo.currentData() == "always":
            self._set_run_state("running")
            self._start_motion()
        else:
            self._set_run_state("armed")

    def disarm_jitter(self) -> None:
        self.pending_arm = False
        self.armed = False
        self.toggle_active = False
        self.last_trigger_pressed = False
        self._stop_motion()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.test_move_button.setEnabled(
            bool(self.driver and self.driver.connected)
        )
        self._set_runtime_settings_enabled(True)
        self._set_run_state("idle")

    def _poll_trigger(self) -> None:
        if self.driver and not self.driver.connected:
            self._handle_connection_lost()
            return
        if not self.armed or not self.driver:
            return

        mode = self.trigger_mode_combo.currentData()
        if mode == "always":
            if not self._motion_running():
                self._start_motion()
            return

        button_index = int(self.trigger_button_combo.currentData())
        pressed = self.driver.is_button_pressed(button_index)
        if mode == "hold":
            if pressed and not self._motion_running():
                self._set_run_state("hold_running")
                self._start_motion()
            elif not pressed and self._motion_running():
                self._stop_motion()
                self._set_run_state("armed")
        elif mode == "toggle" and pressed and not self.last_trigger_pressed:
            self.toggle_active = not self.toggle_active
            if self.toggle_active:
                self._set_run_state("toggle_on")
                self._start_motion()
            else:
                self._stop_motion()
                self._set_run_state("toggle_off")
        self.last_trigger_pressed = pressed

    def _handle_connection_lost(self) -> None:
        self.disarm_jitter()
        if self.driver:
            self.driver.cleanup()
        self.driver = None
        self.connection_dot.setStyleSheet("color: #f85149;")
        self._set_connection_state("connection_lost")
        self.test_move_button.setEnabled(False)
        self._set_connection_settings_enabled(True)

    def _start_motion(self) -> None:
        if self._motion_running() or not (self.driver and self.driver.connected):
            return
        self.jitter_worker = JitterWorker(
            driver=self.driver,
            delay_ms=self.delay_spin.value(),
            pattern_id=str(self.pattern_combo.currentData()),
            amplitude=self.amplitude_spin.value(),
            vertical_pressure_enabled=(
                self.vertical_pressure_checkbox.isChecked()
            ),
            vertical_pressure_amplitude=self.pressure_amplitude_spin.value(),
            vertical_pressure_delay_ms=self.pressure_delay_spin.value(),
        )
        self.jitter_worker.failed.connect(self._on_jitter_failed)
        self.jitter_worker.finished.connect(self._on_jitter_finished)
        self.jitter_worker.start()

    def _stop_motion(self) -> None:
        if self.jitter_worker and self.jitter_worker.isRunning():
            self.jitter_worker.requestInterruption()
            self.jitter_worker.wait()
        self.jitter_worker = None

    def _motion_running(self) -> bool:
        return bool(self.jitter_worker and self.jitter_worker.isRunning())

    def _on_jitter_failed(self, message: str) -> None:
        QMessageBox.critical(
            self,
            self.tr_text("jitter_error_title"),
            message,
        )
        self.armed = False

    def _on_jitter_finished(self) -> None:
        if self.jitter_worker is self.sender():
            self.jitter_worker = None
        if not self.armed:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self._set_runtime_settings_enabled(True)
            self._set_run_state("idle")

    def _set_connection_state(self, key: str, **values) -> None:
        self.connection_state = (key, values)
        self._render_connection_state()

    def _render_connection_state(self) -> None:
        key, values = self.connection_state
        self.connection_status.setText(self.tr_text(key, **values))
        connected = bool(self.driver and self.driver.connected)
        self.connect_button.setText(
            self.tr_text("disconnect" if connected else (
                "reconnect" if key in ("connection_failed", "connection_lost")
                else "connect"
            ))
        )

    def _set_run_state(self, key: str, **values) -> None:
        self.run_state = (key, values)
        self._render_run_state()

    def _render_run_state(self) -> None:
        key, values = self.run_state
        self.run_status.setText(self.tr_text(key, **values))

    def _set_connection_settings_enabled(self, enabled: bool) -> None:
        self.hardware_combo.setEnabled(enabled)
        self.ferrum_mode_combo.setEnabled(enabled)
        self.port_combo.setEnabled(enabled)
        self.baud_combo.setEnabled(enabled)
        self.net_host_edit.setEnabled(enabled)
        self.net_port_spin.setEnabled(enabled)
        self.net_uuid_edit.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)
        self._update_connection_fields()

    def _update_connection_fields(self, *_args) -> None:
        hardware = self.hardware_combo.currentData()
        ferrum = hardware == "ferrum"
        net = ferrum and self.ferrum_mode_combo.currentData() == "net"
        self.ferrum_mode_label.setVisible(ferrum)
        self.ferrum_mode_combo.setVisible(ferrum)
        self.port_label.setVisible(not net)
        self.port_combo.setVisible(not net)
        self.baud_label.setVisible(not net)
        self.baud_combo.setVisible(not net)
        self.refresh_button.setVisible(not net)
        for widget in (
            self.net_host_label,
            self.net_host_edit,
            self.net_port_label,
            self.net_port_spin,
            self.net_uuid_label,
            self.net_uuid_edit,
        ):
            widget.setVisible(net)

    def _set_runtime_settings_enabled(self, enabled: bool) -> None:
        self.pattern_combo.setEnabled(enabled)
        self.amplitude_spin.setEnabled(enabled)
        self.delay_spin.setEnabled(enabled)
        self.vertical_pressure_checkbox.setEnabled(enabled)
        self._update_vertical_pressure_fields()
        self.trigger_mode_combo.setEnabled(enabled)
        self.trigger_button_combo.setEnabled(
            enabled and self.trigger_mode_combo.currentData() != "always"
        )

    def _on_trigger_mode_changed(self, *_args) -> None:
        self.trigger_button_combo.setEnabled(
            self.trigger_mode_combo.currentData() != "always" and not self.armed
        )

    def _update_vertical_pressure_fields(self, *_args) -> None:
        enabled = (
            self.vertical_pressure_checkbox.isChecked()
            and not self.armed
        )
        self.pressure_amplitude_spin.setEnabled(enabled)
        self.pressure_delay_spin.setEnabled(enabled)

    def choose_theme_color(self, scope: str, key: str) -> None:
        if scope not in ("local", "web") or key not in THEME_KEYS:
            return
        theme = self.local_theme if scope == "local" else self.web_theme
        name = self.tr_text(f"theme_{key}")
        selected = QColorDialog.getColor(
            QColor(theme[key]),
            self,
            self.tr_text("choose_color", name=name),
        )
        if not selected.isValid():
            return
        theme[key] = selected.name().upper()
        if scope == "local":
            self._apply_local_theme()
        else:
            self._refresh_theme_buttons()
        self._save_config()
        self._publish_web_state()

    def _apply_local_theme(self) -> None:
        self.setStyleSheet(build_stylesheet(self.local_theme))
        self._refresh_theme_buttons()

    def _refresh_theme_buttons(self) -> None:
        if not hasattr(self, "theme_buttons"):
            return
        for scope, theme in (
            ("local", self.local_theme),
            ("web", self.web_theme),
        ):
            for key, button in self.theme_buttons[scope].items():
                color = theme[key]
                red, green, blue = QColor(color).getRgb()[:3]
                foreground = (
                    "#10151D"
                    if (red * 299 + green * 587 + blue * 114) > 150000
                    else "#FFFFFF"
                )
                button.setText(color.upper())
                button.setStyleSheet(
                    f"background: {color}; color: {foreground};"
                    f" border: 1px solid {foreground};"
                )

    def _update_theme_controls(self, *_args) -> None:
        separate = self.separate_web_theme_checkbox.isChecked()
        for widget in self.theme_buttons["web"].values():
            widget.setEnabled(separate)
        self._refresh_theme_buttons()

    def _effective_web_theme(self) -> dict[str, str]:
        if self.separate_web_theme_checkbox.isChecked():
            return dict(self.web_theme)
        return dict(self.local_theme)

    def _toggle_webui(self, enabled: bool) -> None:
        try:
            if enabled:
                self.web_server.start()
            else:
                self.web_server.stop()
        except OSError as exc:
            self.web_enable_checkbox.blockSignals(True)
            self.web_enable_checkbox.setChecked(False)
            self.web_enable_checkbox.blockSignals(False)
            QMessageBox.critical(self, "WebUI", str(exc))
        self._render_web_address()
        self._save_config()
        self._publish_web_state()

    def _render_web_address(self) -> None:
        if self.web_server.running:
            url = self.web_server.lan_url
            self.web_address.setText(
                f'<a href="{url}">{self.tr_text("web_address", url=url)}</a>'
            )
        else:
            self.web_address.setText(self.tr_text("web_disabled"))

    def _publish_web_state(self) -> None:
        ports = [
            {"device": port.device, "description": port.description}
            for port in list_ports.comports()
        ]
        self.web_server.update_state(
            {
                "language": self.translator.language,
                "hardware": str(self.hardware_combo.currentData() or "makcu"),
                "ferrum_mode": str(
                    self.ferrum_mode_combo.currentData() or "serial"
                ),
                "net_host": self.net_host_edit.text().strip(),
                "net_port": self.net_port_spin.value(),
                "net_uuid": self.net_uuid_edit.text().strip(),
                "com_port": self._selected_port(),
                "baud_rate": int(self.baud_combo.currentData() or 115_200),
                "delay_ms": self.delay_spin.value(),
                "pattern": str(self.pattern_combo.currentData() or "upper_left"),
                "amplitude": self.amplitude_spin.value(),
                "vertical_pressure_enabled": (
                    self.vertical_pressure_checkbox.isChecked()
                ),
                "vertical_pressure_amplitude": (
                    self.pressure_amplitude_spin.value()
                ),
                "vertical_pressure_delay_ms": self.pressure_delay_spin.value(),
                "web_theme": self._effective_web_theme(),
                "trigger_mode": str(
                    self.trigger_mode_combo.currentData() or "hold"
                ),
                "trigger_button": int(
                    self.trigger_button_combo.currentData()
                    if self.trigger_button_combo.currentData() is not None
                    else 0
                ),
                "ports": ports,
                "connected": bool(self.driver and self.driver.connected),
                "armed": self.armed,
                "connection_status": self.connection_status.text(),
                "run_status": self.run_status.text(),
            }
        )

    def _handle_web_command(self, command: str, payload: object) -> None:
        data = payload if isinstance(payload, dict) else {}
        if command == "connect":
            self.connect_hardware()
        elif command == "disconnect":
            self.disconnect_hardware()
        elif command == "start":
            self.arm_jitter()
        elif command == "stop":
            self.disarm_jitter()
        elif command == "config":
            self._apply_web_config(data)
        self._publish_web_state()

    def _apply_web_config(self, data: dict) -> None:
        language = str(data.get("language", self.translator.language))
        self._set_combo_data(self.language_combo, language)

        if not (self.driver and self.driver.connected):
            self._set_combo_data(
                self.hardware_combo,
                str(data.get("hardware", self.hardware_combo.currentData())),
            )
            self._set_combo_data(
                self.ferrum_mode_combo,
                str(data.get("ferrum_mode", self.ferrum_mode_combo.currentData())),
            )
            self.net_host_edit.setText(
                str(data.get("net_host", self.net_host_edit.text()))
            )
            self.net_port_spin.setValue(
                int(data.get("net_port", self.net_port_spin.value()))
            )
            self.net_uuid_edit.setText(
                str(data.get("net_uuid", self.net_uuid_edit.text()))
            )
            port = str(data.get("com_port", self._selected_port()))
            index = self.port_combo.findData(port)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)
            elif port:
                self.port_combo.setEditText(port)
            self._set_combo_data(
                self.baud_combo,
                int(data.get("baud_rate", self.baud_combo.currentData())),
            )

        if not self.armed:
            self._set_combo_data(
                self.pattern_combo,
                str(data.get("pattern", self.pattern_combo.currentData())),
            )
            self.amplitude_spin.setValue(
                max(1, min(500, int(data.get("amplitude", self.amplitude_spin.value()))))
            )
            self.delay_spin.setValue(
                max(1, min(5000, int(data.get("delay_ms", self.delay_spin.value()))))
            )
            self.vertical_pressure_checkbox.setChecked(
                bool(
                    data.get(
                        "vertical_pressure_enabled",
                        self.vertical_pressure_checkbox.isChecked(),
                    )
                )
            )
            self.pressure_amplitude_spin.setValue(
                max(
                    1,
                    min(
                        500,
                        int(
                            data.get(
                                "vertical_pressure_amplitude",
                                self.pressure_amplitude_spin.value(),
                            )
                        ),
                    ),
                )
            )
            self.pressure_delay_spin.setValue(
                max(
                    1,
                    min(
                        5000,
                        int(
                            data.get(
                                "vertical_pressure_delay_ms",
                                self.pressure_delay_spin.value(),
                            )
                        ),
                    ),
                )
            )
            self._set_combo_data(
                self.trigger_mode_combo,
                str(data.get("trigger_mode", self.trigger_mode_combo.currentData())),
            )
            self._set_combo_data(
                self.trigger_button_combo,
                int(data.get("trigger_button", self.trigger_button_combo.currentData())),
            )
        self._save_config()

    @staticmethod
    def _set_combo_data(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def closeEvent(self, event) -> None:
        self.trigger_timer.stop()
        self.web_state_timer.stop()
        self.web_server.stop()
        self.disarm_jitter()
        if self.test_move_worker and self.test_move_worker.isRunning():
            self.test_move_worker.wait()
        if self.connection_worker and self.connection_worker.isRunning():
            self.connection_worker.wait()
        if self.driver:
            self.driver.cleanup()
        event.accept()
