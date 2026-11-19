"""1. Main AI Manager — agentlarni ketma-ket ishga tushiradi.

Ish tartibi:
  Education → (Reels ssenariy) → Caption → Quality Control
  QC xato topsa → bir marta qayta ishlaydi → yana QC.
  Carousel bo'lsa → slayd rasmlari chiziladi.
Natija bazaga (data/balla.db) va output/ papkasiga saqlanadi. HECH NARSA joylanmaydi.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from agents.caption import Caption, write_caption
from agents.carousel import render_carousel, render_reels_cover
from agents.education import LessonContent, create_lesson
from agents.quality import QCReport, review
from agents.reels import ReelsScript, write_script
from config import settings
from storage import database

MAX_REVISIONS = 1
FORMATS = ("carousel", "reels")


@dataclass
class Draft:
    id: int
    format: str
    lesson: LessonContent
    caption: Caption
    qc: QCReport
    status: str
    slides: List[Path]
    script: Optional[ReelsScript]


def _generate(topic, hsk_level, fmt, feedback):
    lesson = create_lesson(topic, hsk_level, feedback)
    script = write_script(lesson, feedback) if fmt == "reels" else None
    caption = write_caption(lesson, feedback)
    return lesson, script, caption


def create_draft(topic: str, hsk_level: int, fmt: str = "carousel",
                 feedback: str = "", log=print) -> Draft:
    """feedback — foydalanuvchining tahrir izohi (Telegram'dagi ✏️ tugmasidan)."""
    if fmt not in FORMATS:
        raise ValueError(f"Format {FORMATS} dan biri bo'lishi kerak")

    log("📚 Agentlar kontent tayyorlamoqda...")
    lesson, script, caption = _generate(topic, hsk_level, fmt, feedback)
    log("🔍 Sifat nazorati...")
    qc = review(lesson, caption, script.as_text() if script else "")

    for attempt in range(MAX_REVISIONS):
        if qc.passed:
            break
        log(f"♻️  Xatolar topildi, qayta ishlanmoqda ({attempt + 1}/{MAX_REVISIONS})...")
        fix = qc.as_feedback() + (f"\n\nFoydalanuvchi izohi: {feedback}" if feedback else "")
        lesson, script, caption = _generate(topic, hsk_level, fmt, fix)
        qc = review(lesson, caption, script.as_text() if script else "")

    status = "qc_passed" if qc.passed else "qc_failed"
    data = {
        "lesson": lesson.model_dump(),
        "caption": caption.model_dump(),
        "caption_full": caption.full_text(),
        "script": script.model_dump() if script else None,
        "qc": {"ball": qc.ball, "muammolar": [i.model_dump() for i in qc.muammolar]},
        "feedback": feedback,
        "slides": [],
    }
    draft_id = database.save_draft(topic, hsk_level, fmt, status, data)

    out_dir = settings.ROOT_DIR / "output" / f"draft_{draft_id}"
    if fmt == "carousel":
        log("🎨 Carousel slaydlari chizilmoqda...")
        slides = render_carousel(lesson, out_dir)
    else:
        log("🎨 Reels muqovasi chizilmoqda...")
        slides = render_reels_cover(lesson, out_dir)
    data["slides"] = [str(p.relative_to(settings.ROOT_DIR)) for p in slides]
    database.update_data(draft_id, data)

    return Draft(draft_id, fmt, lesson, caption, qc, status, slides, script)
