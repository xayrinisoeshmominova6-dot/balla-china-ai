"""BALLA CHINA AI MANAGER — ishga tushirish nuqtasi.

Foydalanish:
  python main.py --check                              # sozlamalarni tekshirish
  python main.py "salomlashish" --hsk 1               # carousel qoralama (terminalda)
  python main.py "salomlashish" --hsk 1 --format reels  # reels ssenariy (terminalda)
  python main.py --bot                                # Telegram botni ishga tushirish

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
    print(f"\n{line}\n📄 Qoralama #{draft.id}\n📌 {lesson.sarlavha}   [HSK {lesson.hsk_daraja}]\n{line}")
    for i, w in enumerate(lesson.sozlar, 1):
        print(f"\n{i}. {w.hanzi}  ({w.pinyin}) — {w.tarjima}")
        print(f"   🧠 {w.eslab_qolish}")
        print(f"   Misol: {w.misol_hanzi}")
        print(f"          {w.misol_pinyin}")
        print(f"          {w.misol_tarjima}")
    print(f"\n⚠️  Xato: {lesson.keng_xato.xato}  →  ✅ {lesson.keng_xato.togri}")
    print(f"🎯 Test: {lesson.test.savol} {lesson.test.variantlar} (javob: {lesson.test.togri_javob + 1})")
    print(f"💡 {lesson.maslahat}")
    if draft.script:
        print(f"\n{line}\n🎬 REELS SSENARIYSI\n{line}\n{draft.script.as_text()}")
    print(f"\n{line}\n📝 CAPTION\n{line}\n{caption.full_text()}")
    print(f"\n{line}\n🔍 SIFAT NAZORATI: {qc.ball}/100 — "
          f"{'✅ o‘tdi' if qc.passed else '❌ xatolar bor'}\n{line}")
    for issue in qc.muammolar:
        icon = "❌" if issue.jiddiylik == "xato" else "⚠️"
        print(f"{icon} [{issue.joy}] {issue.muammo}\n   → {issue.taklif}")
    if not qc.muammolar:
        print("Muammo topilmadi.")
    if draft.slides:
        print(f"\n🖼  Rasmlar: {draft.slides[0].parent.relative_to(settings.ROOT_DIR)}/ ({len(draft.slides)} ta)")
    print("💾 Bazaga saqlandi (data/balla.db). Telegram'da ko'rish: /show", draft.id)
    print("ℹ️  Bu faqat qoralama. Instagram'ga hech narsa joylanmadi.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Balla China kontent qoralamasi yaratish")
    parser.add_argument("mavzu", nargs="?", help="Post mavzusi, masalan: \"salomlashish\"")
    parser.add_argument("--hsk", type=int, default=1, choices=range(1, 7), help="HSK darajasi (1–6)")
    parser.add_argument("--format", default="carousel", choices=["carousel", "reels"])
    parser.add_argument("--check", action="store_true", help="Faqat sozlamalarni tekshirish")
    parser.add_argument("--bot", action="store_true", help="Telegram botni ishga tushirish")
    args = parser.parse_args()

    if args.bot:
        from integrations.telegram_bot import run
        run()
        return

    if args.check or not args.mavzu:
        check()
        if not args.mavzu:
            print('\nKontent yaratish uchun: python main.py "mavzu" --hsk 1')
        return

    from agents.base import AgentError
    from agents.carousel import RenderError
    from agents.manager import create_draft

    try:
        draft = create_draft(args.mavzu, args.hsk, args.format)
    except (AgentError, RenderError) as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    show(draft)


if __name__ == "__main__":
    main()
