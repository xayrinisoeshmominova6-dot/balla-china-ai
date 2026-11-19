"""Tekshirilgan HSK so'zlar ro'yxatini yuklash.

Ro'yxat `data/hsk/hsk3_level{N}.json` fayllarida turadi (qarang: data/hsk/SOURCE.md).
Agar so'z ro'yxatda bo'lsa, uning Hanzi, Pinyin va HSK darajasi Claude'dan emas,
SHU RO'YXATDAN olinadi.
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from balla.config import PROJECT_ROOT

HSK_DIR = PROJECT_ROOT / "data" / "hsk"
AVAILABLE_LEVELS = (1, 2, 3)


@dataclass(frozen=True)
class HSKWord:
    hanzi: str
    pinyin: tuple[str, ...]
    meanings_en: tuple[str, ...]
    pos: tuple[str, ...]
    level: int


class HSKList:
    def __init__(self, words: list[HSKWord]) -> None:
        self.words = words
        self._by_hanzi: dict[str, HSKWord] = {}
        for w in words:  # pastki daraja ustun turadi
            if w.hanzi not in self._by_hanzi or w.level < self._by_hanzi[w.hanzi].level:
                self._by_hanzi[w.hanzi] = w

    def lookup(self, hanzi: str) -> HSKWord | None:
        return self._by_hanzi.get(unicodedata.normalize("NFC", hanzi.strip()))

    def up_to_level(self, level: int) -> list[HSKWord]:
        return [w for w in self.words if w.level <= level]

    def at_level(self, level: int) -> list[HSKWord]:
        return [w for w in self.words if w.level == level]

    @classmethod
    def load(cls, directory: Path = HSK_DIR) -> "HSKList":
        words: list[HSKWord] = []
        for level in AVAILABLE_LEVELS:
            path = directory / f"hsk3_level{level}.json"
            if not path.exists():
                continue
            for e in json.loads(path.read_text(encoding="utf-8")):
                words.append(HSKWord(
                    hanzi=e["hanzi"], pinyin=tuple(e["pinyin"]),
                    meanings_en=tuple(e["meanings_en"]), pos=tuple(e["pos"]),
                    level=int(e["level"]),
                ))
        if not words:
            raise FileNotFoundError(f"HSK ro'yxati topilmadi: {directory}")
        return cls(words)


@lru_cache
def get_hsk_list() -> HSKList:
    return HSKList.load()
