"""Buyruq qatori (terminal) orqali boshqarish.

Ishlatish:
    balla check          — sozlamalarni tekshiradi (kalitlarni ko'rsatmaydi)
    balla list           — barcha kontent ro'yxati
    balla history ID     — kontent holatlari tarixi
"""

from __future__ import annotations

import argparse
import sys

from balla.config import get_settings
from balla.storage.database import ContentStore


def cmd_check(_: argparse.Namespace) -> int:
    s = get_settings()
    ok = "✅"
    no = "❌"
    print("Balla China AI — sozlamalar tekshiruvi\n")
    key_status = f"{ok} bor" if s.has_claude_key else f"{no} yo'q (.env faylini to'ldiring)"
    print(f"  Claude API kaliti:     {key_status}")
    print(f"  Claude modeli:         {s.claude_model}")
    print(f"  Fikrlash chuqurligi:   {s.claude_effort}")
    print(f"  Instagram API:         {ok + ' sozlangan' if s.instagram_configured else '⏸  sozlanmagan (quruq rejim)'}")
    print(f"  Ma'lumotlar bazasi:    {s.resolved_database_path}")
    return 0 if s.has_claude_key else 1


def _store() -> ContentStore:
    return ContentStore(get_settings().resolved_database_path)


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="balla", description="Balla China AI Instagram menejeri")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Sozlamalarni tekshirish").set_defaults(func=cmd_check)
    sub.add_parser("list", help="Kontent ro'yxati").set_defaults(func=cmd_list)
    h = sub.add_parser("history", help="Kontent holatlari tarixi")
    h.add_argument("id", type=int)
    h.set_defaults(func=cmd_history)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
