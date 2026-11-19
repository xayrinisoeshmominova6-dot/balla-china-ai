"""BALLA CHINA AI MANAGER — ishga tushirish nuqtasi.

Foydalanish:
  python main.py --check                      # sozlamalarni tekshirish
  python main.py "salomlashish" --hsk 1       # yangi kontent qoralamasi yaratish

Eslatma: bu dastur hech narsani Instagram'ga JOYLAMAYDI.
"""
import argparse
import sys

from config import settings


def check() -> None:
    print("=== BALLA CHINA AI MANAGER: tekshiruv ===\n")
    brand = settings.load_brand()
    print(f"Brend: {brand['brand']['name']}")
    print(f"Yozuv: {brand['audience']['script']}")
    print(f"HSK darajalari: {brand['content']['hsk_levels']}")
    print(f"Model: {settings.CLAUDE_MODEL}\n")
    print(".env fayli:", "topildi" if settings.ENV_FILE.exists() else "YO'Q (README'ga qarang)")
    print("Kalitlar holati (qiymatlar ko'rsatilmaydi):")
    for name, is_set in settings.key_status().items():
        print(f"  {'✅' if is_set else '⬜'} {name}")
    mode = "YOQIQ — Instagram'ga hech narsa yuborilmaydi" if settings.DRY_RUN else "O'CHIQ"
    print(f"\nSinov rejimi (DRY_RUN): {mode}")


def show(draft) -> None:
    lesson, caption, qc = draft.lesson, draft.caption, draft.qc
    line = "─" * 50
    print(f"\n{line}\n📌 {lesson.sarlavha}   [HSK {lesson.hsk_daraja}]\n{line}")
    for i, w in enumerate(lesson.sozlar, 1):
        print(f"\n{i}. {w.hanzi}  ({w.pinyin}) — {w.tarjima}")
        print(f"   Misol: {w.misol_hanzi}")
        print(f"          {w.misol_pinyin}")
        print(f"          {w.misol_tarjima}")
    print(f"\n💡 {lesson.maslahat}")
    print(f"\n{line}\n📝 CAPTION\n{line}\n{caption.full_text()}")
    print(f"\n{line}\n🔍 SIFAT NAZORATI: {qc.ball}/100 — "
          f"{'✅ o‘tdi' if qc.passed else '❌ xatolar bor'}\n{line}")
    for issue in qc.muammolar:
        icon = "❌" if issue.jiddiylik == "xato" else "⚠️"
        print(f"{icon} [{issue.joy}] {issue.muammo}\n   → {issue.taklif}")
    if not qc.muammolar:
        print("Muammo topilmadi.")
    print(f"\n💾 Saqlandi: {draft.file.relative_to(settings.ROOT_DIR)}")
    print("ℹ️  Bu faqat qoralama. Instagram'ga hech narsa joylanmadi.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Balla China kontent qoralamasi yaratish")
    parser.add_argument("mavzu", nargs="?", help="Post mavzusi, masalan: \"salomlashish\"")
    parser.add_argument("--hsk", type=int, default=1, choices=range(1, 7), help="HSK darajasi (1–6)")
    parser.add_argument("--check", action="store_true", help="Faqat sozlamalarni tekshirish")
    args = parser.parse_args()

    if args.check or not args.mavzu:
        check()
        if not args.mavzu:
            print('\nKontent yaratish uchun: python main.py "mavzu" --hsk 1')
        return

    from agents.base import AgentError
    from agents.manager import create_draft

    try:
        draft = create_draft(args.mavzu, args.hsk)
    except AgentError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    show(draft)


if __name__ == "__main__":
    main()
