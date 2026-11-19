"""1. Main AI Manager — agentlarni ketma-ket ishga tushiradi.

Ish tartibi:
  Education → Caption → Quality Control
  QC xato topsa → bir marta qayta ishlaydi → yana QC.
Natija output/ papkasiga JSON qilib saqlanadi. HECH NARSA joylanmaydi.
"""
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from agents.caption import Caption, write_caption
from agents.education import LessonContent, create_lesson
from agents.quality import QCReport, review
from config import settings

MAX_REVISIONS = 1


@dataclass
class Draft:
    lesson: LessonContent
    caption: Caption
    qc: QCReport
    status: str           # "qc_passed" yoki "qc_failed"
    file: Path


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "post"


def create_draft(topic: str, hsk_level: int, log=print) -> Draft:
    log("📚 Education agent: dars mazmuni tayyorlanmoqda...")
    lesson = create_lesson(topic, hsk_level)
    log("✍️  Caption agent: matn yozilmoqda...")
    caption = write_caption(lesson)
    log("🔍 Quality Control: tekshirilmoqda...")
    qc = review(lesson, caption)

    for attempt in range(MAX_REVISIONS):
        if qc.passed:
            break
        log(f"♻️  Xatolar topildi, qayta ishlanmoqda ({attempt + 1}/{MAX_REVISIONS})...")
        feedback = qc.as_feedback()
        lesson = create_lesson(topic, hsk_level, feedback)
        caption = write_caption(lesson, feedback)
        qc = review(lesson, caption)

    status = "qc_passed" if qc.passed else "qc_failed"
    out_dir = settings.ROOT_DIR / "output"
    out_dir.mkdir(exist_ok=True)
    file = out_dir / f"{datetime.now():%Y%m%d_%H%M%S}_{_slug(topic)}.json"
    file.write_text(json.dumps({
        "status": status,
        "lesson": lesson.model_dump(),
        "caption": caption.model_dump(),
        "caption_full": caption.full_text(),
        "qc": {"ball": qc.ball, "muammolar": [i.model_dump() for i in qc.muammolar]},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return Draft(lesson, caption, qc, status, file)
