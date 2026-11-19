"""6. Caption Writing Agent — Instagram uchun o'zbekcha matn yozadi."""
from typing import List

from pydantic import BaseModel

from agents.base import ask_claude, load_prompt
from agents.education import LessonContent
from config import settings


class Caption(BaseModel):
    hook: str             # birinchi qator — e'tiborni tortadi
    matn: str             # asosiy caption matni
    cta: str              # harakatga chaqiruv
    heshteglar: List[str]

    def full_text(self) -> str:
        return f"{self.hook}\n\n{self.matn}\n\n{self.cta}\n\n{' '.join(self.heshteglar)}"


def write_caption(lesson: LessonContent, feedback: str = "") -> Caption:
    brand = settings.load_brand()
    message = (
        f"Dars mazmuni (JSON):\n{lesson.model_dump_json(indent=2)}\n\n"
        f"Majburiy heshteglar: {' '.join(brand['caption']['default_hashtags'])}\n"
        f"Jami heshteglar soni: {brand['caption']['hashtags_count']}\n"
    )
    if feedback:
        message += f"\nOldingi variantda topilgan xatolar — ularni tuzating:\n{feedback}\n"
    return ask_claude(load_prompt("caption"), message, Caption)
