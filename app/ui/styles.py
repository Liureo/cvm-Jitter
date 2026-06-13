from __future__ import annotations

from app.core.theme import DEFAULT_THEME, normalize_theme


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))


def _rgba(color: str, alpha: int) -> str:
    red, green, blue = _rgb(color)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def build_stylesheet(theme: object) -> str:
    colors = normalize_theme(theme)
    background = colors["background"]
    panel = colors["panel"]
    text = colors["text"]
    muted = colors["muted"]
    accent = colors["accent"]
    border = _rgba(muted, 65)
    soft_border = _rgba(muted, 42)
    input_background = _rgba(background, 220)
    button_background = _rgba(panel, 235)
    hover_background = _rgba(accent, 42)

    return f"""
QMainWindow,
QWidget#appRoot {{
    background: {background};
    color: {text};
    font-size: 14px;
}}
QLabel {{
    color: {text};
    background: transparent;
}}
QCheckBox,
QTabWidget,
QTabBar,
QWidget#tabPage {{
    color: {text};
    background: transparent;
}}
QLabel#title {{
    font-size: 30px;
    font-weight: 700;
    color: {text};
}}
QLabel#subtitle, QLabel#cardDescription {{
    color: {muted};
    font-size: 12px;
}}
QLabel#fieldLabel {{ color: {muted}; font-size: 12px; }}
QLabel#saveStatus {{ color: {accent}; font-size: 12px; }}
QLabel#cardTitle {{ color: {text}; font-size: 17px; font-weight: 650; }}
QLabel#webAddress {{ color: {accent}; font-size: 12px; }}
QLabel#footerLinks {{ color: {muted}; font-size: 11px; }}
QLabel#footerLinks a {{ color: {accent}; }}
QTabWidget#mainTabs::pane {{
    border: 0;
    background: transparent;
}}
QTabBar::tab {{
    min-width: 112px;
    min-height: 38px;
    margin-right: 8px;
    padding: 0 18px;
    color: {muted};
    background: {panel};
    border: 1px solid {soft_border};
    border-radius: 8px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {text};
    background: {hover_background};
    border-color: {accent};
}}
QTabBar::tab:hover {{ color: {text}; border-color: {accent}; }}
QFrame#card {{
    background: {panel};
    border: 1px solid {soft_border};
    border-radius: 12px;
}}
QComboBox, QSpinBox, QLineEdit {{
    min-height: 38px;
    padding: 0 11px;
    color: {text};
    background: {input_background};
    border: 1px solid {border};
    border-radius: 7px;
    selection-color: {text};
    selection-background-color: {accent};
}}
QComboBox QAbstractItemView {{
    color: {text};
    background: {panel};
    border: 1px solid {border};
    selection-color: {text};
    selection-background-color: {accent};
}}
QComboBox:hover, QSpinBox:hover, QLineEdit:hover {{ border-color: {accent}; }}
QComboBox:focus, QSpinBox:focus, QLineEdit:focus {{ border-color: {accent}; }}
QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {{
    color: {muted};
    background: {_rgba(background, 145)};
}}
QCheckBox {{ spacing: 10px; color: {text}; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1px solid {border};
    border-radius: 4px;
    background: {input_background};
}}
QCheckBox::indicator:checked {{
    background: {accent};
    border-color: {accent};
}}
QPushButton {{
    min-height: 38px;
    padding: 0 16px;
    color: {text};
    background: {button_background};
    border: 1px solid {border};
    border-radius: 7px;
    font-weight: 600;
}}
QPushButton:hover {{ background: {hover_background}; border-color: {accent}; }}
QPushButton:pressed {{ background: {_rgba(accent, 65)}; }}
QPushButton:disabled {{ color: {muted}; background: {_rgba(panel, 155)}; }}
QPushButton#connectButton {{ color: {accent}; }}
QPushButton#testMoveButton {{ color: #62ddad; }}
QPushButton#startButton {{
    min-height: 48px;
    color: #ffffff;
    background: #23864d;
    border-color: #31a662;
}}
QPushButton#startButton:hover {{ background: #2a9959; }}
QPushButton#stopButton {{ min-height: 48px; color: #ff8179; }}
QLabel#connectionDot {{ color: {muted}; font-size: 16px; }}
QLabel#connectionStatus {{ color: {muted}; }}
QLabel#runStatus {{
    min-height: 44px;
    background: {panel};
    border: 1px solid {soft_border};
    border-radius: 9px;
    color: {text};
    font-weight: 600;
}}
"""


MAIN_STYLESHEET = build_stylesheet(DEFAULT_THEME)
