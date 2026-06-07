from __future__ import annotations

from app.i18n import en, zh_CN, zh_TW


LANGUAGES = {
    "en": en,
    "zh_CN": zh_CN,
    "zh_TW": zh_TW,
}


class Translator:
    def __init__(self, language: str = "zh_TW") -> None:
        self.language = language if language in LANGUAGES else "en"

    def set_language(self, language: str) -> None:
        self.language = language if language in LANGUAGES else "en"

    def text(self, key: str, **values) -> str:
        module = LANGUAGES[self.language]
        fallback = en.STRINGS.get(key, key)
        return module.STRINGS.get(key, fallback).format(**values)
