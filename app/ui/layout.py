from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.i18n.translator import LANGUAGES
from app.core.theme import THEME_KEYS
from app.ui.styles import MAIN_STYLESHEET


BAUD_RATES = (("115200", 115_200), ("4M (4000000)", 4_000_000))
HARDWARE_TYPES = (("MAKCU", "makcu"), ("Ferrum", "ferrum"))


def _card() -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("card")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(13)
    return frame, layout


def _tab_page() -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    page.setObjectName("tabPage")
    layout = QVBoxLayout(page)
    layout.setContentsMargins(4, 18, 4, 4)
    layout.setSpacing(16)
    return page, layout


def build_main_window(window) -> None:
    page = QWidget()
    page.setObjectName("appRoot")
    root = QVBoxLayout(page)
    root.setContentsMargins(30, 24, 30, 26)
    root.setSpacing(14)

    header = QHBoxLayout()
    title_column = QVBoxLayout()
    title_column.setSpacing(5)
    window.title_label = QLabel()
    window.title_label.setObjectName("title")
    window.subtitle_label = QLabel()
    window.subtitle_label.setObjectName("subtitle")
    title_column.addWidget(window.title_label)
    title_column.addWidget(window.subtitle_label)
    header.addLayout(title_column)
    header.addStretch()

    language_column = QVBoxLayout()
    language_column.setSpacing(6)
    window.language_label = QLabel()
    window.language_label.setObjectName("fieldLabel")
    window.language_combo = QComboBox()
    window.language_combo.setMinimumWidth(130)
    for code, module in LANGUAGES.items():
        window.language_combo.addItem(module.LANGUAGE_NAME, code)
    window.language_combo.currentIndexChanged.connect(window._change_language)
    language_column.addWidget(window.language_label)
    language_column.addWidget(window.language_combo)
    header.addLayout(language_column)
    root.addLayout(header)

    save_row = QHBoxLayout()
    save_row.addStretch()
    window.save_label = QLabel()
    window.save_label.setObjectName("saveStatus")
    save_row.addWidget(window.save_label)
    root.addLayout(save_row)

    window.tabs = QTabWidget()
    window.tabs.setObjectName("mainTabs")
    hardware_page, hardware_layout = _tab_page()
    settings_page, settings_layout = _tab_page()
    advanced_page, advanced_layout = _tab_page()
    theme_page, theme_layout = _tab_page()
    window.hardware_tab = hardware_page
    window.settings_tab = settings_page
    window.advanced_tab = advanced_page
    window.theme_tab = theme_page

    connection_card, connection_layout = _card()
    window.connection_title = QLabel()
    window.connection_title.setObjectName("cardTitle")
    window.connection_description = QLabel()
    window.connection_description.setObjectName("cardDescription")
    window.connection_description.setWordWrap(True)
    connection_layout.addWidget(window.connection_title)
    connection_layout.addWidget(window.connection_description)

    connection_grid = QGridLayout()
    connection_grid.setHorizontalSpacing(16)
    connection_grid.setVerticalSpacing(9)
    connection_grid.setColumnStretch(0, 1)
    connection_grid.setColumnStretch(1, 1)
    connection_grid.setColumnStretch(2, 1)
    window.hardware_label = QLabel()
    window.hardware_combo = QComboBox()
    for label, value in HARDWARE_TYPES:
        window.hardware_combo.addItem(label, value)
    window.port_label = QLabel()
    window.port_combo = QComboBox()
    window.port_combo.setEditable(True)
    window.baud_label = QLabel()
    window.baud_combo = QComboBox()
    for label, value in BAUD_RATES:
        window.baud_combo.addItem(label, value)
    window.ferrum_mode_label = QLabel()
    window.ferrum_mode_combo = QComboBox()
    window.ferrum_mode_combo.addItem("Serial", "serial")
    window.ferrum_mode_combo.addItem("Net", "net")
    window.net_host_label = QLabel()
    window.net_host_edit = QLineEdit()
    window.net_port_label = QLabel()
    window.net_port_spin = QSpinBox()
    window.net_port_spin.setRange(1, 65535)
    window.net_uuid_label = QLabel()
    window.net_uuid_edit = QLineEdit()
    window.net_uuid_edit.setMaxLength(8)
    connection_grid.addWidget(window.hardware_label, 0, 0)
    connection_grid.addWidget(window.ferrum_mode_label, 0, 1)
    connection_grid.addWidget(window.port_label, 0, 2)
    connection_grid.addWidget(window.hardware_combo, 1, 0)
    connection_grid.addWidget(window.ferrum_mode_combo, 1, 1)
    connection_grid.addWidget(window.port_combo, 1, 2)
    connection_grid.addWidget(window.baud_label, 2, 0)
    connection_grid.addWidget(window.net_host_label, 2, 0)
    connection_grid.addWidget(window.net_port_label, 2, 1)
    connection_grid.addWidget(window.net_uuid_label, 2, 2)
    connection_grid.addWidget(window.baud_combo, 3, 0, 1, 3)
    connection_grid.addWidget(window.net_host_edit, 3, 0)
    connection_grid.addWidget(window.net_port_spin, 3, 1)
    connection_grid.addWidget(window.net_uuid_edit, 3, 2)
    connection_layout.addLayout(connection_grid)

    connection_actions = QHBoxLayout()
    window.connection_dot = QLabel("●")
    window.connection_dot.setObjectName("connectionDot")
    window.connection_status = QLabel()
    window.connection_status.setObjectName("connectionStatus")
    window.refresh_button = QPushButton()
    window.refresh_button.clicked.connect(window.refresh_ports)
    window.test_move_button = QPushButton()
    window.test_move_button.setObjectName("testMoveButton")
    window.test_move_button.setEnabled(False)
    window.test_move_button.clicked.connect(window.test_move)
    window.connect_button = QPushButton()
    window.connect_button.setObjectName("connectButton")
    window.connect_button.clicked.connect(window.toggle_connection)
    connection_actions.addWidget(window.connection_dot)
    connection_actions.addWidget(window.connection_status)
    connection_actions.addStretch()
    connection_actions.addWidget(window.refresh_button)
    connection_actions.addWidget(window.test_move_button)
    connection_actions.addWidget(window.connect_button)
    connection_layout.addLayout(connection_actions)
    hardware_layout.addWidget(connection_card)

    web_card, web_layout = _card()
    window.web_title = QLabel()
    window.web_title.setObjectName("cardTitle")
    window.web_description = QLabel()
    window.web_description.setObjectName("cardDescription")
    window.web_description.setWordWrap(True)
    window.web_enable_checkbox = QCheckBox()
    window.web_enable_checkbox.toggled.connect(window._toggle_webui)
    window.web_address = QLabel()
    window.web_address.setObjectName("webAddress")
    window.web_address.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextBrowserInteraction
    )
    window.web_address.setOpenExternalLinks(True)
    web_layout.addWidget(window.web_title)
    web_layout.addWidget(window.web_description)
    web_layout.addWidget(window.web_enable_checkbox)
    web_layout.addWidget(window.web_address)
    hardware_layout.addWidget(web_card)
    hardware_layout.addStretch()

    jitter_card, jitter_layout = _card()
    window.jitter_title = QLabel()
    window.jitter_title.setObjectName("cardTitle")
    window.jitter_description = QLabel()
    window.jitter_description.setObjectName("cardDescription")
    window.jitter_description.setWordWrap(True)
    jitter_layout.addWidget(window.jitter_title)
    jitter_layout.addWidget(window.jitter_description)
    jitter_grid = QGridLayout()
    jitter_grid.setHorizontalSpacing(18)
    jitter_grid.setVerticalSpacing(9)
    for column in range(3):
        jitter_grid.setColumnStretch(column, 1)
    window.pattern_label = QLabel()
    window.pattern_combo = QComboBox()
    window.amplitude_label = QLabel()
    window.amplitude_spin = QSpinBox()
    window.amplitude_spin.setRange(1, 500)
    window.amplitude_spin.setSuffix(" px")
    window.delay_label = QLabel()
    window.delay_spin = QSpinBox()
    window.delay_spin.setRange(1, 5000)
    window.delay_spin.setSuffix(" ms")
    jitter_grid.addWidget(window.pattern_label, 0, 0)
    jitter_grid.addWidget(window.amplitude_label, 0, 1)
    jitter_grid.addWidget(window.delay_label, 0, 2)
    jitter_grid.addWidget(window.pattern_combo, 1, 0)
    jitter_grid.addWidget(window.amplitude_spin, 1, 1)
    jitter_grid.addWidget(window.delay_spin, 1, 2)
    jitter_layout.addLayout(jitter_grid)
    settings_layout.addWidget(jitter_card)

    trigger_card, trigger_layout = _card()
    window.trigger_title = QLabel()
    window.trigger_title.setObjectName("cardTitle")
    window.trigger_description = QLabel()
    window.trigger_description.setObjectName("cardDescription")
    window.trigger_description.setWordWrap(True)
    trigger_layout.addWidget(window.trigger_title)
    trigger_layout.addWidget(window.trigger_description)
    trigger_grid = QGridLayout()
    trigger_grid.setHorizontalSpacing(18)
    trigger_grid.setVerticalSpacing(9)
    trigger_grid.setColumnStretch(0, 1)
    trigger_grid.setColumnStretch(1, 1)
    window.trigger_mode_label = QLabel()
    window.trigger_mode_combo = QComboBox()
    window.trigger_mode_combo.currentIndexChanged.connect(
        window._on_trigger_mode_changed
    )
    window.trigger_button_label = QLabel()
    window.trigger_button_combo = QComboBox()
    window.ads_required_checkbox = QCheckBox()
    window.ads_required_checkbox.toggled.connect(
        window._update_ads_fields
    )
    window.ads_button_label = QLabel()
    window.ads_button_combo = QComboBox()
    trigger_grid.addWidget(window.trigger_mode_label, 0, 0)
    trigger_grid.addWidget(window.trigger_button_label, 0, 1)
    trigger_grid.addWidget(window.trigger_mode_combo, 1, 0)
    trigger_grid.addWidget(window.trigger_button_combo, 1, 1)
    trigger_grid.addWidget(window.ads_required_checkbox, 3, 0)
    trigger_grid.addWidget(window.ads_button_label, 2, 1)
    trigger_grid.addWidget(window.ads_button_combo, 3, 1)
    trigger_layout.addLayout(trigger_grid)
    settings_layout.addWidget(trigger_card)
    settings_layout.addStretch()

    pressure_card, pressure_layout = _card()
    window.pressure_title = QLabel()
    window.pressure_title.setObjectName("cardTitle")
    window.pressure_description = QLabel()
    window.pressure_description.setObjectName("cardDescription")
    window.pressure_description.setWordWrap(True)
    window.vertical_pressure_checkbox = QCheckBox()
    window.vertical_pressure_checkbox.toggled.connect(
        window._update_vertical_pressure_fields
    )
    pressure_layout.addWidget(window.pressure_title)
    pressure_layout.addWidget(window.pressure_description)
    pressure_layout.addWidget(window.vertical_pressure_checkbox)

    pressure_grid = QGridLayout()
    pressure_grid.setHorizontalSpacing(18)
    pressure_grid.setVerticalSpacing(9)
    pressure_grid.setColumnStretch(0, 1)
    pressure_grid.setColumnStretch(1, 1)
    window.pressure_amplitude_label = QLabel()
    window.pressure_amplitude_spin = QSpinBox()
    window.pressure_amplitude_spin.setRange(1, 500)
    window.pressure_amplitude_spin.setSuffix(" px")
    window.pressure_delay_label = QLabel()
    window.pressure_delay_spin = QSpinBox()
    window.pressure_delay_spin.setRange(1, 5000)
    window.pressure_delay_spin.setSuffix(" ms")
    pressure_grid.addWidget(window.pressure_amplitude_label, 0, 0)
    pressure_grid.addWidget(window.pressure_delay_label, 0, 1)
    pressure_grid.addWidget(window.pressure_amplitude_spin, 1, 0)
    pressure_grid.addWidget(window.pressure_delay_spin, 1, 1)
    pressure_layout.addLayout(pressure_grid)
    advanced_layout.addWidget(pressure_card)
    advanced_layout.addStretch()

    window.theme_labels = {"local": {}, "web": {}}
    window.theme_buttons = {"local": {}, "web": {}}

    local_theme_card, local_theme_layout = _card()
    window.local_theme_title = QLabel()
    window.local_theme_title.setObjectName("cardTitle")
    window.local_theme_description = QLabel()
    window.local_theme_description.setObjectName("cardDescription")
    window.local_theme_description.setWordWrap(True)
    window.separate_web_theme_checkbox = QCheckBox()
    window.separate_web_theme_checkbox.toggled.connect(
        window._update_theme_controls
    )
    local_theme_layout.addWidget(window.local_theme_title)
    local_theme_layout.addWidget(window.local_theme_description)
    local_theme_layout.addWidget(window.separate_web_theme_checkbox)

    local_theme_grid = QGridLayout()
    local_theme_grid.setHorizontalSpacing(18)
    local_theme_grid.setVerticalSpacing(9)
    for column in range(len(THEME_KEYS)):
        local_theme_grid.setColumnStretch(column, 1)
    for index, key in enumerate(THEME_KEYS):
        label = QLabel()
        button = QPushButton()
        local_theme_grid.addWidget(label, 0, index)
        local_theme_grid.addWidget(button, 1, index)
        button.clicked.connect(
            lambda _checked=False, color_key=key: window.choose_theme_color(
                "local", color_key
            )
        )
        window.theme_labels["local"][key] = label
        window.theme_buttons["local"][key] = button
    local_theme_layout.addLayout(local_theme_grid)
    theme_layout.addWidget(local_theme_card)

    window.web_theme_card, web_theme_layout = _card()
    window.web_theme_title = QLabel()
    window.web_theme_title.setObjectName("cardTitle")
    window.web_theme_description = QLabel()
    window.web_theme_description.setObjectName("cardDescription")
    window.web_theme_description.setWordWrap(True)
    web_theme_layout.addWidget(window.web_theme_title)
    web_theme_layout.addWidget(window.web_theme_description)

    web_theme_grid = QGridLayout()
    web_theme_grid.setHorizontalSpacing(18)
    web_theme_grid.setVerticalSpacing(9)
    for column in range(len(THEME_KEYS)):
        web_theme_grid.setColumnStretch(column, 1)
    for index, key in enumerate(THEME_KEYS):
        label = QLabel()
        button = QPushButton()
        web_theme_grid.addWidget(label, 0, index)
        web_theme_grid.addWidget(button, 1, index)
        button.clicked.connect(
            lambda _checked=False, color_key=key: window.choose_theme_color(
                "web", color_key
            )
        )
        window.theme_labels["web"][key] = label
        window.theme_buttons["web"][key] = button
    web_theme_layout.addLayout(web_theme_grid)
    theme_layout.addWidget(window.web_theme_card)
    theme_layout.addStretch()

    window.tabs.addTab(hardware_page, "")
    window.tabs.addTab(settings_page, "")
    window.tabs.addTab(advanced_page, "")
    window.tabs.addTab(theme_page, "")
    root.addWidget(window.tabs, 1)

    window.run_status = QLabel()
    window.run_status.setObjectName("runStatus")
    window.run_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    root.addWidget(window.run_status)

    actions = QHBoxLayout()
    actions.setSpacing(12)
    window.start_button = QPushButton()
    window.start_button.setObjectName("startButton")
    window.start_button.clicked.connect(window.arm_jitter)
    window.stop_button = QPushButton()
    window.stop_button.setObjectName("stopButton")
    window.stop_button.setEnabled(False)
    window.stop_button.clicked.connect(window.disarm_jitter)
    actions.addWidget(window.start_button, 2)
    actions.addWidget(window.stop_button, 1)
    root.addLayout(actions)

    window.footer_links = QLabel()
    window.footer_links.setObjectName("footerLinks")
    window.footer_links.setAlignment(Qt.AlignmentFlag.AlignCenter)
    window.footer_links.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextBrowserInteraction
    )
    window.footer_links.setOpenExternalLinks(True)
    root.addWidget(window.footer_links)

    window.setCentralWidget(page)
    window.setStyleSheet(MAIN_STYLESHEET)
