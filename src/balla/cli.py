"""Buyruq qatori (terminal) orqali boshqarish.

Sozlamalar:
    balla check                         — sozlamalarni tekshiradi (kalitlarni ko'rsatmaydi)
    balla instagram                     — Instagram ulanishini tekshiradi (faqat o'qiydi)

Dars yaratish va tekshirish:
    balla lesson "Oila" --level 1 --words 6   — yangi dars (QORALAMA)
    balla show ID                       — kontentni ko'rsatish
    balla review ID                     — tekshiruvga yuborish
    balla verify ID [--words 1 3]       — o'qituvchi so'zlarni tasdiqlaydi
    balla approve ID                    — tasdiqlash (barcha so'zlar tasdiqlangan bo'lsa)
    balla reject ID --note "sabab"      — rad etish
    balla list                          — barcha kontent ro'yxati
    balla history ID                    — kontent holatlari tarixi
"""

from __future__ import annotations

import argparse
import sys

from balla.config import get_settings
from balla.schemas.content import ContentStatus, InvalidTransitionError
from balla.storage.database import ContentStore

HUMAN = "human:cli"


def _store() -> ContentStore:
    return ContentStore(get_settings().resolved_database_path)


def cmd_check(_: argparse.Namespace) -> int:
    s = get_settings()
    print("Balla China AI — sozlamalar tekshiruvi\n")
    key_status = "✅ bor" if s.has_claude_key else "❌ yo'q (.env faylini to'ldiring)"
    ig_status = "✅ sozlangan" if s.instagram_configured else "⏸  sozlanmagan (quruq rejim)"
    print(f"  Claude API kaliti:     {key_status}")
    print(f"  Claude modeli:         {s.claude_model}")
    print(f"  Fikrlash chuqurligi:   {s.claude_effort}")
    print(f"  Instagram API:         {ig_status}")
    print(f"  Ma'lumotlar bazasi:    {s.resolved_database_path}")
    return 0 if s.has_claude_key else 1


def cmd_list(_: argparse.Namespace) -> int:
    items = _store().list()
    if not items:
        print("Hozircha kontent yo'q.")
    for it in items:
        print(f"  #{it['id']:<4} [{it['status']:<10}] {it['type']:<9} {it['title']}")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    for h in _store().history(args.id):
        print(f"  {h['at']}  {h['from_status'] or '-':>10} -> {h['to_status']:<10} ({h['actor']}) {h['note'] or ''}")
    return 0


def cmd_instagram(_: argparse.Namespace) -> int:
    from balla.integrations.instagram import InstagramClient, InstagramError

    try:
        p = InstagramClient().get_profile()
    except InstagramError as e:
        print(f"❌ {e}")
        return 1
    print("✅ Instagram'ga ulanish ishlayapti!\n")
    print(f"  Akkaunt:      @{p.username}")
    if p.name:
        print(f"  Nomi:         {p.name}")
    print(f"  Obunachilar:  {p.followers_count if p.followers_count is not None else '-'}")
    print(f"  Postlar:      {p.media_count if p.media_count is not None else '-'}")
    return 0


def cmd_lesson(args: argparse.Namespace) -> int:
    from balla.agents.educator import EducatorAgent
    from balla.agents.lesson_render import render_lesson
    from balla.llm.claude_client import ClaudeClient, ClaudeError
    from balla.workflow import save_lesson

    print(f"⏳ Dars tayyorlanmoqda: «{args.topic}», HSK {args.level}, {args.words} ta so'z...")
    try:
        lesson = EducatorAgent(ClaudeClient()).create_lesson(args.topic, args.level, args.words)
    except (ClaudeError, ValueError) as e:
        print(f"❌ {e}")
        return 1
    store = _store()
    cid, path = save_lesson(store, lesson)
    print(render_lesson(lesson, cid))
    print(f"\n💾 Saqlandi: #{cid} (QORALAMA) → {path}")
    print(f"Keyingi qadam: balla review {cid}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    from balla.agents.lesson_render import render_lesson
    from balla.workflow import load_lesson

    store = _store()
    item = store.get(args.id)
    if item is None:
        print(f"❌ #{args.id} topilmadi.")
        return 1
    print(f"Holat: {item['status']}\n")
    if item["type"] == "lesson":
        print(render_lesson(load_lesson(store, args.id), args.id))
    else:
        print(item["payload"])
    return 0


def _transition(cid: int, status: ContentStatus, note: str | None = None) -> int:
    try:
        _store().set_status(cid, status, actor=HUMAN, note=note)
    except (InvalidTransitionError, KeyError) as e:
        print(f"❌ {e}")
        return 1
    print(f"✅ #{cid} → {status.value}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    return _transition(args.id, ContentStatus.IN_REVIEW)


def cmd_reject(args: argparse.Namespace) -> int:
    return _transition(args.id, ContentStatus.REJECTED, args.note)


def cmd_verify(args: argparse.Namespace) -> int:
    from balla.workflow import export_lesson, teacher_verify

    store = _store()
    try:
        lesson = teacher_verify(store, args.id, args.words, actor=HUMAN)
    except (KeyError, IndexError, ValueError) as e:
        print(f"❌ {e}")
        return 1
    export_lesson(store, args.id)
    done = sum(v.teacher_verified for v in lesson.vocabulary)
    print(f"✅ Tasdiqlangan so'zlar: {done}/{len(lesson.vocabulary)}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    from balla.workflow import NotVerifiedError, approve

    try:
        approve(_store(), args.id, actor=HUMAN)
    except (NotVerifiedError, InvalidTransitionError, KeyError) as e:
        print(f"❌ {e}")
        return 1
    print(f"✅ #{args.id} tasdiqlandi.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="balla", description="Balla China AI Instagram menejeri")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="Sozlamalarni tekshirish").set_defaults(func=cmd_check)
    sub.add_parser("instagram", help="Instagram ulanishini tekshirish").set_defaults(func=cmd_instagram)
    sub.add_parser("list", help="Kontent ro'yxati").set_defaults(func=cmd_list)

    p = sub.add_parser("lesson", help="Yangi dars yaratish")
    p.add_argument("topic", help="Mavzu, masalan: \"Oila\"")
    p.add_argument("--level", type=int, default=1, choices=[1, 2, 3])
    p.add_argument("--words", type=int, default=6)
    p.set_defaults(func=cmd_lesson)

    for name, func, help_ in [
        ("show", cmd_show, "Kontentni ko'rsatish"),
        ("history", cmd_history, "Holatlar tarixi"),
        ("review", cmd_review, "Tekshiruvga yuborish"),
        ("approve", cmd_approve, "Tasdiqlash"),
    ]:
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("id", type=int)
        sp.set_defaults(func=func)

    v = sub.add_parser("verify", help="O'qituvchi so'zlarni tasdiqlaydi")
    v.add_argument("id", type=int)
    v.add_argument("--words", type=int, nargs="+", help="So'z raqamlari (bo'sh — hammasi)")
    v.set_defaults(func=cmd_verify)

    r = sub.add_parser("reject", help="Rad etish")
    r.add_argument("id", type=int)
    r.add_argument("--note", required=True, help="Rad etish sababi")
    r.set_defaults(func=cmd_reject)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
