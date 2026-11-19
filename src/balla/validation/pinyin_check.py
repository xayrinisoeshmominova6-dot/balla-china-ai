"""Pinyin'ni avtomatik tekshirish.

Tartib:
  1. So'z HSK ro'yxatida bo'lsa — ro'yxatdagi pinyin bilan solishtiriladi.
  2. Aks holda — `pypinyin` kutubxonasi mustaqil hisoblagan pinyin bilan.
     Agar belgining bir necha o'qilishi bo'lsa (多音字) va Claude bergani ulardan biri
     bo'lsa, natija POLYPHONE bo'ladi — ya'ni "odam ko'rishi kerak".

Muhim: bu tekshiruv xatolarni USHLASH vositasi, yakuniy hakam emas.
Yakuniy so'z — o'qituvchida.

Eslatma: lug'atlarda pinyin "asl ohang" bilan yoziladi (masalan 不 = bù, 一 = yī).
Gapdagi ohang o'zgarishlari (变调) bu yerda tekshirilmaydi.
"""

from __future__ import annotations

import itertools
import re
import unicodedata

from pypinyin import Style, pinyin

from balla.schemas.lesson import PinyinCheck
from balla.validation.hsk_list import HSKList

_HANZI = re.compile(r"[㐀-鿿]")
_MAX_COMBINATIONS = 64


def normalize(p: str) -> str:
    """Solishtirish uchun: kichik harf, bo'shliq/apostrof/tire olib tashlanadi, ü = v emas."""
    p = unicodedata.normalize("NFC", p).lower()
    return re.sub(r"[\s'’\-·]", "", p)


def toneless(p: str) -> str:
    """Ohang belgilarini olib tashlaydi: 'nǐhǎo' -> 'nihao' (ü -> u)."""
    decomposed = unicodedata.normalize("NFD", normalize(p))
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _pypinyin_default(hanzi: str) -> str:
    return "".join(s[0] for s in pinyin(hanzi, style=Style.TONE))


def _pypinyin_all(hanzi: str) -> set[str]:
    per_char = [syls for syls in pinyin(hanzi, style=Style.TONE, heteronym=True)]
    count = 1
    for syls in per_char:
        count *= len(syls)
    if count > _MAX_COMBINATIONS:
        return set()
    return {"".join(c) for c in itertools.product(*per_char)}


def check_pinyin(hanzi: str, given: str, hsk: HSKList | None = None) -> PinyinCheck:
    if not _HANZI.search(hanzi):
        return PinyinCheck.NOT_CHECKED
    g = normalize(given)

    if hsk is not None and (word := hsk.lookup(hanzi)):
        refs = list(word.pinyin)
        if g in {normalize(p) for p in refs}:
            return PinyinCheck.MATCH
    else:
        default = _pypinyin_default(hanzi)
        if g == normalize(default):
            return PinyinCheck.MATCH
        if g in {normalize(p) for p in _pypinyin_all(hanzi)}:
            return PinyinCheck.POLYPHONE
        refs = [default]

    if toneless(given) in {toneless(p) for p in refs}:
        return PinyinCheck.TONE_DIFF
    return PinyinCheck.MISMATCH
