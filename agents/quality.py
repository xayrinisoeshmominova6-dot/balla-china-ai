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


def _issue(level, place, problem, fix) -> Issue:
    return Issue(jiddiylik=level, joy=place, muammo=problem, taklif=fix)


def rule_checks(lesson: LessonContent, caption: Caption, extra_text: str = "") -> List[Issue]:
    """API'siz, oddiy Python qoidalari bilan tekshirish (tez va bepul)."""
    from agents.carousel import is_hanzi

    brand = settings.load_brand()
    issues: List[Issue] = []

    # 1. Kirill harflari — hamma o'zbekcha matnda
    texts = {
        "sarlavha": lesson.sarlavha,
        "kichik_sarlavha": lesson.kichik_sarlavha,
        "maslahat": lesson.maslahat,
        "keng_xato": f"{lesson.keng_xato.xato} {lesson.keng_xato.togri} {lesson.keng_xato.izoh}",
        "test": f"{lesson.test.savol} {' '.join(lesson.test.variantlar)} {lesson.test.izoh}",
        "caption": caption.full_text(),
        "reels_ssenariy": extra_text,
    }
    for i, w in enumerate(lesson.sozlar):
        texts[f"sozlar[{i}]"] = f"{w.tarjima} {w.soz_turkumi} {w.eslab_qolish} {w.misol_tarjima}"
    for place, text in texts.items():
        if CYRILLIC.search(text):
            issues.append(_issue("xato", place, "Kirill harflari topildi", "Faqat lotin yozuvidan foydalaning"))

    # 2. So'zlar
    if not 4 <= len(lesson.sozlar) <= 6:
        issues.append(_issue("xato" if not lesson.sozlar else "ogohlantirish", "sozlar",
                             f"{len(lesson.sozlar)} ta so'z (kerak: 4–6)", "So'zlar sonini 4–6 ga keltiring"))
    for i, w in enumerate(lesson.sozlar):
        n_chars = sum(1 for ch in w.hanzi if is_hanzi(ch))
        if n_chars != len(w.bogin_pinyin):
            issues.append(_issue("xato", f"sozlar[{i}].bogin_pinyin",
                                 f"{w.hanzi}: {n_chars} ta ieroglif, lekin {len(w.bogin_pinyin)} ta bo'g'in",
                                 "Har bir ieroglif uchun bittadan pinyin bo'g'ini yozing"))
        if w.hanzi not in w.misol_hanzi:
            issues.append(_issue("ogohlantirish", f"sozlar[{i}].misol_hanzi",
                                 f"Misol gapda {w.hanzi} yo'q", "Misol gapga shu so'zni aynan qo'shing"))

    # 3. Muqova
    if lesson.sarlavha_urgu.strip() not in lesson.sarlavha:
        issues.append(_issue("ogohlantirish", "sarlavha_urgu", "Urg'u qismi sarlavha ichida topilmadi",
                             "sarlavha_urgu ni sarlavhadan aynan ko'chiring"))
    if len(lesson.sarlavha) > 60:
        issues.append(_issue("ogohlantirish", "sarlavha", f"Sarlavha uzun ({len(lesson.sarlavha)} belgi)",
                             "55 belgigacha qisqartiring"))

    # 4. Test
    if len(lesson.test.variantlar) != 3 or not 0 <= lesson.test.togri_javob < len(lesson.test.variantlar):
        issues.append(_issue("xato", "test", "Test variantlari 3 ta emas yoki to'g'ri javob raqami noto'g'ri",
                             "Aynan 3 ta variant va 0–2 oralig'ida to'g'ri javob bering"))

    # 5. Caption
    max_len = brand["caption"]["max_length"]
    if len(caption.full_text()) > max_len:
        issues.append(_issue("xato", "caption", f"Caption {max_len} belgidan uzun", "Matnni qisqartiring"))
    for tag in brand["caption"]["default_hashtags"]:
        if tag not in caption.heshteglar:
            issues.append(_issue("ogohlantirish", "heshteglar", f"{tag} heshtegi yo'q", f"{tag} ni qo'shing"))
    return issues


def review(lesson: LessonContent, caption: Caption, extra_text: str = "") -> QCReport:
    """extra_text — qo'shimcha tekshiriladigan matn (masalan, Reels ssenariysi)."""
    message = (
        f"Dars mazmuni:\n{lesson.model_dump_json(indent=2)}\n\n"
        f"Caption:\n{caption.full_text()}\n"
    )
    if extra_text:
        message += f"\nReels ssenariysi:\n{extra_text}\n"
    report = ask_claude(load_prompt("quality"), message, QCReport, effort="high")
    report.muammolar = rule_checks(lesson, caption, extra_text) + report.muammolar
    return report
