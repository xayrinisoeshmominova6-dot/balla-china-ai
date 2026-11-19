"""Darsni o'qituvchi tekshirishi uchun qulay matn (Markdown) ko'rinishiga keltirish."""

from __future__ import annotations

from balla.schemas.lesson import Confidence, Lesson, PinyinCheck

_CHECK_LABEL = {
    PinyinCheck.MATCH: "✅ mos",
    PinyinCheck.MISMATCH: "⚠️ FARQ BOR",
    PinyinCheck.TONE_DIFF: "⚠️ ohang farqi",
    PinyinCheck.POLYPHONE: "⚠️ ko'p o'qilishli",
    PinyinCheck.NOT_CHECKED: "— tekshirilmagan",
}


def render_lesson(lesson: Lesson, content_id: int | None = None) -> str:
    head = f"# {lesson.title_uzbek}"
    if content_id is not None:
        head += f"  (#{content_id})"
    out = [head, "", f"**Mavzu:** {lesson.topic}  ·  **Daraja:** {lesson.level}", ""]

    attention = lesson.needs_attention
    if attention:
        out += [f"> ⚠️ **{len(attention)} ta so'z alohida e'tibor talab qiladi.**", ""]

    for i, v in enumerate(lesson.vocabulary, 1):
        flag = " 🟡 ISHONCH PAST" if v.confidence == Confidence.UNCERTAIN else ""
        lvl = f"HSK {v.hsk_level}" if v.hsk_level else "ro'yxatda yo'q"
        out.append(f"## {i}. {v.hanzi} — {v.pinyin}{flag}")
        out.append(f"- **Ma'nosi:** {v.uzbek} ({v.part_of_speech})")
        out.append(f"- **Daraja:** {lvl} · **Pinyin tekshiruvi:** {_CHECK_LABEL[v.pinyin_check]}")
        for ex in v.examples:
            out.append(f"- **Misol:** {ex.hanzi} — *{ex.pinyin}* — {ex.uzbek}")
        if v.notes:
            out.append(f"- **Izoh:** {v.notes}")
        out.append(f"- **O'qituvchi tasdiqladi:** {'✅' if v.teacher_verified else '☐'}")
        out.append("")

    if lesson.grammar_point:
        out += ["## Grammatika", lesson.grammar_point, ""]
    if lesson.pronunciation_tip:
        out += ["## Talaffuz maslahati", lesson.pronunciation_tip, ""]
    return "\n".join(out)
