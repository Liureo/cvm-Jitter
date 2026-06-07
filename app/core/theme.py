from __future__ import annotations

import re


THEME_KEYS = ("background", "panel", "text", "muted", "accent")

DEFAULT_THEME = {
    "background": "#0d1522",
    "panel": "#172235",
    "text": "#f2f6fc",
    "muted": "#aab8cb",
    "accent": "#4f9cff",
}

_HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalize_theme(value: object) -> dict[str, str]:
    source = value if isinstance(value, dict) else {}
    return {
        key: (
            str(source.get(key))
            if _HEX_COLOR.fullmatch(str(source.get(key, "")))
            else default
        )
        for key, default in DEFAULT_THEME.items()
    }
