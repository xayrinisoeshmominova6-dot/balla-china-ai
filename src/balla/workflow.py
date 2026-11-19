"""Kontent bilan ishlash jarayoni: yaratish -> tekshiruv -> tasdiqlash.

Qo'shimcha qoida (darslar uchun): o'qituvchi barcha so'zlarni tasdiqlamaguncha
darsni TASDIQLANGAN holatiga o'tkazib bo'lmaydi.
"""

from __future__ import annotations

from pathlib import Path

from balla.agents.lesson_render import render_lesson
from balla.config import PROJECT_ROOT
from balla.schemas.content import ContentStatus, ContentType
from balla.schemas.lesson import Lesson
from balla.storage.database import ContentStore

LESSONS_DIR = PROJECT_ROOT / "output" / "lessons"


class NotVerifiedError(ValueError):
    pass


def save_lesson(store: ContentStore, lesson: Lesson, out_dir: Path = LESSONS_DIR) -> tuple[int, Path]:
    cid = store.add(ContentType.LESSON, lesson.title_uzbek, lesson.model_dump(mode="json"))
    return cid, export_lesson(store, cid, out_dir)


def load_lesson(store: ContentStore, cid: int) -> Lesson:
    item = store.get(cid)
    if item is None or item["type"] != ContentType.LESSON.value:
        raise KeyError(f"#{cid} raqamli dars topilmadi.")
    return Lesson.model_validate(item["payload"])


def export_lesson(store: ContentStore, cid: int, out_dir: Path = LESSONS_DIR) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"lesson_{cid}.md"
    path.write_text(render_lesson(load_lesson(store, cid), cid), encoding="utf-8")
    return path


def teacher_verify(store: ContentStore, cid: int, positions: list[int] | None, *, actor: str) -> Lesson:
    """O'qituvchi so'zlarni tasdiqlaydi. positions=None — hammasi. Raqamlar 1 dan boshlanadi."""
    lesson = load_lesson(store, cid)
    idxs = range(len(lesson.vocabulary)) if positions is None else [p - 1 for p in positions]
    for i in idxs:
        if not 0 <= i < len(lesson.vocabulary):
            raise IndexError(f"{i + 1}-so'z mavjud emas.")
        lesson.vocabulary[i].teacher_verified = True
    store.update_payload(cid, lesson.model_dump(mode="json"), actor=actor,
                         note=f"o'qituvchi tasdiqladi: {'hammasi' if positions is None else positions}")
    return lesson


def approve(store: ContentStore, cid: int, *, actor: str) -> None:
    item = store.get(cid)
    if item is None:
        raise KeyError(f"#{cid} topilmadi.")
    if item["type"] == ContentType.LESSON.value and not load_lesson(store, cid).fully_verified:
        raise NotVerifiedError(
            "O'qituvchi hali barcha so'zlarni tasdiqlamagan. Avval: balla verify ID"
        )
    store.set_status(cid, ContentStatus.APPROVED, actor=actor)
