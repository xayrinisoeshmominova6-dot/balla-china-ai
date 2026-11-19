"""2. Chinese Education Agent — xitoy tili ta'limiy mazmunini tayyorlaydi.

Natija carousel tuzilmasiga mos keladi:
  muqova → har bir so'z → keng tarqalgan xato → test → takrorlash + CTA
"""
from typing import List

from pydantic import BaseModel, Field

from agents.base import ask_claude, load_prompt


class Word(BaseModel):
    hanzi: str = Field(description="Soddalashtirilgan ieroglif(lar), masalan: 服务员")
    pinyin: str = Field(description="To'liq pinyin ton belgilari bilan, masalan: fúwùyuán")
    bogin_pinyin: List[str] = Field(
        description="Har bir ieroglif uchun alohida pinyin bo'g'ini, tartib bo'yicha. "
                    "服务员 → ['fú','wù','yuán']. Soni ieroglif soniga TENG bo'lishi shart.")
    tarjima: str = Field(description="Qisqa o'zbekcha tarjima (1–4 so'z)")
    soz_turkumi: str = Field(description="ot, fe'l, sifat, ibora va h.k.")
    eslab_qolish: str = Field(
        description="Eslab qolish usuli: ieroglif tarkibi, o'zbekcha tovush o'xshashligi "
                    "yoki qiziq bog'lanish. 1–2 gap.")
    misol_hanzi: str = Field(description="Misol gap; ichida shu so'z albatta bo'lsin")
    misol_pinyin: str
    misol_tarjima: str


class Mistake(BaseModel):
    xato: str = Field(description="O'zbek o'quvchilari ko'p qiladigan xato (xitoycha + pinyin)")
    togri: str = Field(description="To'g'ri variant (xitoycha + pinyin)")
    izoh: str = Field(description="Nima uchun shunday — 1–2 qisqa gap")


class Quiz(BaseModel):
    savol: str = Field(description="Qisqa test savoli o'zbekcha")
    variantlar: List[str] = Field(description="Aynan 3 ta javob varianti")
    togri_javob: int = Field(description="To'g'ri variant raqami: 0, 1 yoki 2")
    izoh: str = Field(description="To'g'ri javob izohi (caption oxirida ishlatiladi)")


class LessonContent(BaseModel):
    mavzu: str
    hsk_daraja: int
    sarlavha: str = Field(description="Muqova sarlavhasi: kuchli hook, ko'pi bilan 55 belgi")
    sarlavha_urgu: str = Field(
        description="Sarlavhadagi ajratib ko'rsatiladigan qism (aynan sarlavha ichidan olingan "
                    "1–3 so'z yoki raqam), masalan: '5 ta ibora'")
    kichik_sarlavha: str = Field(description="Muqova ostidagi qisqa va'da, ko'pi bilan 60 belgi")
    sozlar: List[Word]
    keng_xato: Mistake
    test: Quiz
    maslahat: str = Field(description="Bitta amaliy maslahat, 1–2 gap")


def create_lesson(topic: str, hsk_level: int, feedback: str = "") -> LessonContent:
    message = f"Mavzu: {topic}\nHSK darajasi: {hsk_level}\n"
    if feedback:
        message += f"\nOldingi variantda topilgan xatolar — ularni tuzating:\n{feedback}\n"
    return ask_claude(load_prompt("education"), message, LessonContent, effort="high")
