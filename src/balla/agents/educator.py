"""Xitoy tili o'qituvchisi agenti.

Ish tartibi:
  1. Tanlangan darajadagi tekshirilgan HSK ro'yxatini Claude'ga beradi.
  2. Claude mavzuga mos so'zlarni tanlaydi, o'zbekchaga tarjima qiladi, misollar yozadi.
  3. Tizim Claude javobini TEKSHIRADI:
       * so'z ro'yxatda bo'lsa — Hanzi/Pinyin/daraja ro'yxatdagi bilan almashtiriladi;
       * ro'yxatda yo'q so'z — "uncertain" deb belgilanadi;
       * har bir so'z va misol pinyin'i avtomatik tekshiriladi.
  4. Natija QORALAMA holatida saqlanadi. O'qituvchi tasdiqlamaguncha nashr qilinmaydi.
"""

from __future__ import annotations

from balla.agents.base import BaseAgent
from balla.llm.claude_client import ClaudeClient
from balla.schemas.lesson import Confidence, Lesson, PinyinCheck
from balla.validation.hsk_list import AVAILABLE_LEVELS, HSKList, get_hsk_list
from balla.validation.pinyin_check import check_pinyin


class EducatorAgent(BaseAgent):
    prompt_name = "educator"

    def __init__(self, llm: ClaudeClient, hsk: HSKList | None = None) -> None:
        super().__init__(llm)
        self.hsk = hsk or get_hsk_list()

    def build_prompt(self, topic: str, level: int, n_words: int) -> str:
        words = self.hsk.up_to_level(level)
        lines = [
            f"{w.hanzi} | {' / '.join(w.pinyin)} | HSK {w.level} | {'; '.join(w.meanings_en[:2])}"
            for w in words
        ]
        return (
            f"Topic: {topic}\n"
            f"Level: HSK {level} (new HSK 3.0 standard)\n"
            f"Number of words: {n_words}\n\n"
            f"VERIFIED WORD LIST ({len(lines)} words, levels 1–{level}):\n"
            + "\n".join(lines)
        )

    def create_lesson(self, topic: str, level: int = 1, n_words: int = 6) -> Lesson:
        if level not in AVAILABLE_LEVELS:
            raise ValueError(f"Hozircha faqat HSK {AVAILABLE_LEVELS} darajalari mavjud.")
        if not 1 <= n_words <= 12:
            raise ValueError("So'zlar soni 1 dan 12 gacha bo'lishi kerak.")
        lesson = self.ask(self.build_prompt(topic, level, n_words), Lesson)
        lesson.level = f"HSK {level}"
        return self.verify(lesson)

    def verify(self, lesson: Lesson) -> Lesson:
        """Claude javobini ro'yxat va pypinyin bilan tekshiradi."""
        for item in lesson.vocabulary:
            item.teacher_verified = False  # buni faqat odam o'zgartiradi
            ref = self.hsk.lookup(item.hanzi)
            if ref is None:
                item.confidence = Confidence.UNCERTAIN
                item.hsk_level = None
                item.notes = _append(item.notes, "Bu so'z tekshirilgan HSK ro'yxatida yo'q.")
            else:
                item.hanzi = ref.hanzi
                item.hsk_level = ref.level
                check = check_pinyin(item.hanzi, item.pinyin, self.hsk)
                if check != PinyinCheck.MATCH and len(ref.pinyin) == 1:
                    item.notes = _append(
                        item.notes, f"Pinyin ro'yxatdagiga almashtirildi ({item.pinyin} -> {ref.pinyin[0]})."
                    )
                    item.pinyin = ref.pinyin[0]
            item.pinyin_check = check_pinyin(item.hanzi, item.pinyin, self.hsk)

            for ex in item.examples:
                # Gaplarda ohang o'zgarishlari (变调) va yengil ohang bo'ladi, shuning uchun
                # bu yerdagi natija faqat ogohlantirish sifatida izohga yoziladi.
                ex_check = check_pinyin(ex.hanzi, ex.pinyin)
                if ex_check == PinyinCheck.MISMATCH:
                    item.notes = _append(
                        item.notes, f"Misol pinyin'ini tekshiring: «{ex.hanzi}»."
                    )
        return lesson


def _append(existing: str | None, new: str) -> str:
    return f"{existing} | {new}" if existing else new
