"""2. Chinese Education Agent — xitoy tili ta'limiy mazmunini tayyorlaydi."""
from typing import List

from pydantic import BaseModel

from agents.base import ask_claude, load_prompt


class Word(BaseModel):
    hanzi: str            # ieroglif, masalan: 你好
    pinyin: str           # tonli pinyin, masalan: nǐ hǎo
    tarjima: str          # o'zbekcha tarjima
    misol_hanzi: str      # misol gap ieroglifda
    misol_pinyin: str     # misol gap pinyinda
    misol_tarjima: str    # misol gap tarjimasi


class LessonContent(BaseModel):
    mavzu: str
    hsk_daraja: int
    sarlavha: str         # post uchun qisqa, qiziqarli sarlavha
    sozlar: List[Word]
    maslahat: str         # o'quvchiga bitta foydali maslahat


def create_lesson(topic: str, hsk_level: int, feedback: str = "") -> LessonContent:
    message = f"Mavzu: {topic}\nHSK darajasi: {hsk_level}\n"
    if feedback:
        message += f"\nOldingi variantda topilgan xatolar — ularni tuzating:\n{feedback}\n"
    return ask_claude(load_prompt("education"), message, LessonContent)
