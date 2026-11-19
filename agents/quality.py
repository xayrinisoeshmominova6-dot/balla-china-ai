"""7. Quality Control Agent — kontentni tekshiradi.

Ikki xil tekshiruv bor:
1. Oddiy qoidalar (Python) — tez va bepul: kirill harflari, uzunlik, heshteglar.
2. Claude tekshiruvi — pinyin, tonlar, tarjima to'g'riligi.
"""
import re
from typing import List, Literal

from pydantic import BaseModel

from agents.base import ask_claude, load_prompt
from agents.caption import Caption
from agents.education import LessonContent
from config import settings

CYRILLIC = re.compile(r"[Ѐ-ӿ]")


class Issue(BaseModel):
    jiddiylik: Literal["xato", "ogohlantirish"]
    joy: str              # qayerda: masalan "sozlar[2].pinyin" yoki "caption"
    muammo: str
    taklif: str


class QCReport(BaseModel):
    ball: int             # 0–100
    muammolar: List[Issue]

    @property
    def passed(self) -> bool:
        return not any(i.jiddiylik == "xato" for i in self.muammolar)

    def as_feedback(self) -> str:
        return "\n".join(f"- [{i.joy}] {i.muammo} → {i.taklif}" for i in self.muammolar)


def rule_checks(lesson: LessonContent, caption: Caption) -> List[Issue]:
    """API'siz, oddiy Python qoidalari bilan tekshirish."""
    brand = settings.load_brand()
    issues: List[Issue] = []

    texts = {
        "sarlavha": lesson.sarlavha,
        "maslahat": lesson.maslahat,
        "caption": caption.full_text(),
    }
    for i, w in enumerate(lesson.sozlar):
        texts[f"sozlar[{i}].tarjima"] = w.tarjima
        texts[f"sozlar[{i}].misol_tarjima"] = w.misol_tarjima
    for place, text in texts.items():
        if CYRILLIC.search(text):
            issues.append(Issue(jiddiylik="xato", joy=place,
                                muammo="Kirill harflari topildi",
                                taklif="Faqat lotin yozuvidan foydalaning"))

    max_len = brand["caption"]["max_length"]
    if len(caption.full_text()) > max_len:
        issues.append(Issue(jiddiylik="xato", joy="caption",
                            muammo=f"Caption {max_len} belgidan uzun",
                            taklif="Matnni qisqartiring"))

    for tag in brand["caption"]["default_hashtags"]:
        if tag not in caption.heshteglar:
            issues.append(Issue(jiddiylik="ogohlantirish", joy="heshteglar",
                                muammo=f"{tag} heshtegi yo'q",
                                taklif=f"{tag} ni qo'shing"))

    if not lesson.sozlar:
        issues.append(Issue(jiddiylik="xato", joy="sozlar",
                            muammo="Birorta ham so'z yo'q", taklif="So'zlar qo'shing"))
    return issues


def review(lesson: LessonContent, caption: Caption) -> QCReport:
    message = (
        f"Dars mazmuni:\n{lesson.model_dump_json(indent=2)}\n\n"
        f"Caption:\n{caption.full_text()}\n"
    )
    report = ask_claude(load_prompt("quality"), message, QCReport)
    report.muammolar = rule_checks(lesson, caption) + report.muammolar
    return report
