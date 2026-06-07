from __future__ import annotations

import json
from pathlib import Path

from app.core.theme import DEFAULT_THEME, normalize_theme


DEFAULT_CONFIG = {
    "language": "zh_TW",
    "webui_enabled": False,
    "hardware": "makcu",
    "ferrum_mode": "serial",
    "net_host": "192.168.2.188",
    "net_port": 8808,
    "net_uuid": "",
    "com_port": "",
    "baud_rate": 115200,
    "delay_ms": 10,
    "pattern": "upper_left",
    "amplitude": 3,
    "vertical_pressure_enabled": False,
    "vertical_pressure_amplitude": 1,
    "vertical_pressure_delay_ms": 10,
    "separate_web_theme": False,
    "local_theme": dict(DEFAULT_THEME),
    "web_theme": dict(DEFAULT_THEME),
    "trigger_mode": "hold",
    "trigger_button": 0,
}

LEGACY_VALUES = {
    "pattern": {
        "左上": "upper_left",
        "右上": "upper_right",
        "水平": "horizontal",
        "左下": "lower_left",
        "右下": "lower_right",
        "畫圈": "circle",
    },
    "trigger_mode": {
        "按住觸發": "hold",
        "切換觸發": "toggle",
        "不使用觸發鍵": "always",
    },
}


class ConfigStore:
    def __init__(self) -> None:
        self.path = Path(__file__).resolve().parents[2] / "config.json"

    def load(self) -> dict:
        data = DEFAULT_CONFIG.copy()
        try:
            saved = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                data.update(saved)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        for field, replacements in LEGACY_VALUES.items():
            data[field] = replacements.get(data.get(field), data.get(field))
        data["local_theme"] = normalize_theme(data.get("local_theme"))
        data["web_theme"] = normalize_theme(data.get("web_theme"))
        return data

    def save(self, data: dict) -> None:
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
