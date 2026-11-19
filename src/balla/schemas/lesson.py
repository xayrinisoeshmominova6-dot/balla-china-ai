"""Xitoy tili darsi uchun ma'lumot shakllari.

Har bir so'zda tekshiruv maydonlari bor. Ular AI yozgan ma'lumotni
"hali tekshirilmagan" deb belgilab turadi:
  * `confidence`          — Claude o'z javobiga qanchalik ishonchli
  * `pinyin_check`        — pypinyin bilan avtomatik solishtirish natijasi
  * `teacher_verified`    — o'qituvchi tasdiqlaganmi (faqat odam o'zgartiradi)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Confidence(str, Enum):
    HIGH = "high"
    UNCERTAIN = "uncertain"  # Claude ishonchi komil emas — albatta tekshirilsin


class PinyinCheck(str, Enum):
    NOT_CHECKED = "not_checked"
    MATCH = "match"
    MISMATCH = "mismatch"            # ⚠️ farq bor — odam ko'rishi shart
    TONE_DIFF = "tone_diff"          # bo'g'inlar bir xil, faqat ohang farq qiladi
                                     # (ko'pincha yengil ohang yoki 变调) — odam ko'rishi kerak
    POLYPHONE = "polyphone"          # ko'p o'qilishli belgi (多音字) — odam ko'rishi kerak


class ExampleSentence(BaseModel):
    hanzi: str = Field(description="Xitoycha gap (soddalashtirilgan ieroglif)")
    pinyin: str = Field(description="Ohang belgilari bilan pinyin, masalan: nǐ hǎo")
    uzbek: str = Field(description="O'zbekcha tarjima (lotin yozuvida)")


class VocabItem(BaseModel):
    hanzi: str = Field(description="So'z, soddalashtirilgan ieroglifda")
    pinyin: str = Field(description="Ohang belgilari bilan pinyin")
    uzbek: str = Field(description="O'zbekcha ma'nosi (lotin yozuvida)")
    part_of_speech: str = Field(description="So'z turkumi, o'zbekcha (ot, fe'l, sifat...)")
    hsk_level: int | None = Field(
        default=None,
        description="HSK darajasi, faqat berilgan ro'yxatdan aniq ma'lum bo'lsa; aks holda null",
    )
    examples: list[ExampleSentence] = Field(default_factory=list)
    confidence: Confidence = Confidence.HIGH
    notes: str | None = Field(default=None, description="Noaniqlik bo'lsa, shu yerda izoh")

    # Quyidagilarni Claude to'ldirmaydi — tizim va o'qituvchi to'ldiradi
    pinyin_check: PinyinCheck = PinyinCheck.NOT_CHECKED
    teacher_verified: bool = False


class Lesson(BaseModel):
    title_uzbek: str
    topic: str
    level: str = Field(description="Masalan: HSK 1")
    vocabulary: list[VocabItem]
    grammar_point: str | None = None
    pronunciation_tip: str | None = None

    @property
    def needs_attention(self) -> list[VocabItem]:
        """O'qituvchi albatta ko'rishi kerak bo'lgan so'zlar."""
        return [
            v
            for v in self.vocabulary
            if v.confidence == Confidence.UNCERTAIN
            or v.pinyin_check
            in (PinyinCheck.MISMATCH, PinyinCheck.POLYPHONE, PinyinCheck.TONE_DIFF)
        ]

    @property
    def fully_verified(self) -> bool:
        return bool(self.vocabulary) and all(v.teacher_verified for v in self.vocabulary)
