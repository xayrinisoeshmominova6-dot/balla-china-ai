"""8. Telegram Approval Bot — qoralamalarni sizga yuboradi va tasdig'ingizni oladi.

XAVFSIZLIK:
- Bot FAQAT .env dagi TELEGRAM_ADMIN_CHAT_ID dan kelgan xabarlarga javob beradi.
- Tasdiqlash ikki bosqichli: "✅ Tasdiqlash" → "Ha, aniq tasdiqlayman".
- Tasdiqlangandan keyin alohida "🚀 Instagram'ga joylash" → "Ha, hozir joylansin" kerak.
- DRY_RUN=true bo'lsa — Instagram'ga hech narsa yuborilmaydi.

Buyruqlar:
  /start                        yordam
  /new <mavzu> [hsk]            carousel qoralama   (masalan: /new salomlashish 1)
  /reels <mavzu> [hsk]          reels ssenariy qoralama
  /list                         oxirgi 10 ta qoralama
  /show <id>                    qoralamani qayta ko'rish
"""
import asyncio
import logging
from typing import Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

from config import settings
from storage import database
from storage.database import STATUS_LABELS, DraftRecord, StatusError

log = logging.getLogger("balla.bot")
MAX_MSG = 4000

HELP = (
    "👋 BALLA CHINA AI MANAGER\n\n"
    "Buyruqlar:\n"
    "/new <mavzu> [hsk] — carousel qoralama\n"
    "   masalan: /new salomlashish 1\n"
    "/reels <mavzu> [hsk] — Reels ssenariysi\n"
    "/list — oxirgi qoralamalar\n"
    "/show <id> — qoralamani ko'rish\n\n"
    "ℹ️ Hech narsa sizning tasdig'ingizsiz joylanmaydi."
)


# ---------- yordamchi funksiyalar ----------

def parse_topic_args(args) -> Tuple[str, int]:
    """['restoranda', 'buyurtma', '3'] → ('restoranda buyurtma', 3). HSK bo'lmasa — 1."""
    words = list(args)
    hsk = 1
    if words and words[-1].isdigit() and 1 <= int(words[-1]) <= 6:
        hsk = int(words.pop())
    return " ".join(words).strip(), hsk


def is_admin(update: Update) -> bool:
    admin = str(settings.TELEGRAM_ADMIN_CHAT_ID).strip()
    chat = update.effective_chat
    user = update.effective_user
    return bool(admin) and chat is not None and str(chat.id) == admin and (
        user is None or chat.type != "private" or str(user.id) == admin)


def chunks(text: str, size: int = MAX_MSG):
    for i in range(0, len(text), size):
        yield text[i:i + size]


def approval_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"approve:{draft_id}"),
        InlineKeyboardButton("✏️ Tahrir", callback_data=f"edit:{draft_id}"),
        InlineKeyboardButton("❌ Rad etish", callback_data=f"reject:{draft_id}"),
    ]])


def confirm_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ha, aniq tasdiqlayman", callback_data=f"confirm:{draft_id}"),
        InlineKeyboardButton("↩️ Orqaga", callback_data=f"back:{draft_id}"),
    ]])


def publish_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Instagram'ga joylash", callback_data=f"publish:{draft_id}"),
    ]])


def publish_confirm_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🚀 Ha, hozir joylansin", callback_data=f"publish_go:{draft_id}"),
        InlineKeyboardButton("⏸ Keyinroq", callback_data=f"publish_later:{draft_id}"),
    ]])


def keyboard_for(rec: DraftRecord) -> Optional[InlineKeyboardMarkup]:
    if rec.status == "awaiting_approval":
        return approval_keyboard(rec.id)
    if rec.status == "approved" and rec.format == "carousel":
        return publish_keyboard(rec.id)
    return None


def format_lesson(rec: DraftRecord) -> str:
    d = rec.data
    lesson = d["lesson"]
    lines = [f"📄 Qoralama #{rec.id} · {rec.format} · HSK {rec.hsk_level}",
             f"Holat: {STATUS_LABELS.get(rec.status, rec.status)}", "",
             f"📌 {lesson['sarlavha']}", ""]
    for i, w in enumerate(lesson["sozlar"], 1):
        lines += [f"{i}. {w['hanzi']} ({w['pinyin']}) — {w['tarjima']}",
                  f"   🧠 {w['eslab_qolish']}",
                  f"   {w['misol_hanzi']} / {w['misol_pinyin']}",
                  f"   {w['misol_tarjima']}"]
    m, q = lesson["keng_xato"], lesson["test"]
    answer = q["variantlar"][q["togri_javob"]] if 0 <= q["togri_javob"] < len(q["variantlar"]) else "?"
    lines += ["", f"⚠️ Xato: {m['xato']}", f"✅ To'g'ri: {m['togri']}", f"   {m['izoh']}",
              "", f"🎯 Test: {q['savol']}", f"   Javob: {answer} — {q['izoh']}",
              "   (javobni izohlarda o'zingiz pin qilib qo'ying)",
              "", f"💡 {lesson['maslahat']}"]

    qc = d["qc"]
    errors = [m for m in qc["muammolar"] if m["jiddiylik"] == "xato"]
    lines += ["", f"🔍 Sifat nazorati: {qc['ball']}/100"]
    for m in qc["muammolar"]:
        icon = "❌" if m["jiddiylik"] == "xato" else "⚠️"
        lines.append(f"{icon} [{m['joy']}] {m['muammo']} → {m['taklif']}")
    if errors:
        lines.append("\n⚠️ QC xatolar topdi. Tasdiqlashdan oldin diqqat bilan tekshiring!")
    if d.get("feedback"):
        lines.append(f"\n✏️ Sizning izohingiz: {d['feedback']}")
    return "\n".join(lines)


def format_script(script: dict) -> str:
    lines = ["🎬 REELS SSENARIYSI", f"Hook: {script['hook']}",
             f"Davomiyligi: ~{script['davomiylik_soniya']} s", ""]
    for s in script["sahnalar"]:
        lines += [f"[{s['vaqt']}] 🎥 {s['kadr']}", f"   🗣 {s['gapiriladi']}",
                  f"   🔤 {s['ekrandagi_matn']}", ""]
    lines += [f"🎵 {script['musiqa_tavsiya']}", f"💡 {script['suratga_olish_maslahati']}"]
    return "\n".join(lines)


async def send_draft(bot, chat_id: int, rec: DraftRecord) -> None:
    """Qoralamani to'liq yuboradi: rasmlar/ssenariy → mazmun → caption + tugmalar."""
    slides = rec.data.get("slides") or []
    if len(slides) == 1:
        with open(settings.ROOT_DIR / slides[0], "rb") as f:
            await bot.send_photo(chat_id, photo=f)
    elif slides:
        files = [open(settings.ROOT_DIR / p, "rb") for p in slides[:10]]
        try:
            await bot.send_media_group(chat_id, media=[InputMediaPhoto(f) for f in files])
        finally:
            for f in files:
                f.close()
    if rec.data.get("script"):
        for part in chunks(format_script(rec.data["script"])):
            await bot.send_message(chat_id, part)
    for part in chunks(format_lesson(rec)):
        await bot.send_message(chat_id, part)

    caption_msg = "📝 CAPTION:\n\n" + rec.data["caption_full"]
    parts = list(chunks(caption_msg))
    for part in parts[:-1]:
        await bot.send_message(chat_id, part)
    if rec.data.get("permalink"):
        parts[-1] += f"\n\n🔗 {rec.data['permalink']}"
    await bot.send_message(chat_id, parts[-1], reply_markup=keyboard_for(rec))


async def generate_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE,
                            topic: str, hsk: int, fmt: str, feedback: str = "") -> None:
    from agents.base import AgentError
    from agents.carousel import RenderError
    from agents.manager import create_draft

    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id, f"⏳ Tayyorlanmoqda: «{topic}» (HSK {hsk}, {fmt}). Bu 1–3 daqiqa olishi mumkin...")
    try:
        draft = await asyncio.to_thread(create_draft, topic, hsk, fmt, feedback, log.info)
        database.set_status(draft.id, "awaiting_approval")
        rec = database.get_draft(draft.id)
    except (AgentError, RenderError) as e:
        await context.bot.send_message(chat_id, f"❌ {e}")
        return
    except Exception:
        log.exception("Qoralama yaratishda kutilmagan xato")
        await context.bot.send_message(chat_id, "❌ Kutilmagan xato yuz berdi. Terminaldagi logni tekshiring.")
        return
    await send_draft(context.bot, chat_id, rec)


# ---------- buyruqlar ----------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP)


async def _cmd_create(update, context, fmt):
    topic, hsk = parse_topic_args(context.args)
    if not topic:
        await update.message.reply_text(f"Mavzuni yozing. Masalan: /{'new' if fmt == 'carousel' else 'reels'} salomlashish 1")
        return
    await generate_and_send(update, context, topic, hsk, fmt)


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _cmd_create(update, context, "carousel")


async def cmd_reels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _cmd_create(update, context, "reels")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    drafts = database.list_drafts(10)
    if not drafts:
        await update.message.reply_text("Hali qoralamalar yo'q. /new bilan boshlang.")
        return
    lines = [f"#{d.id} · {STATUS_LABELS.get(d.status, d.status)} · {d.format} · HSK {d.hsk_level} · {d.topic}"
             for d in drafts]
    await update.message.reply_text("📋 Oxirgi qoralamalar:\n\n" + "\n".join(lines) + "\n\nKo'rish: /show <id>")


async def cmd_show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Masalan: /show 3")
        return
    rec = database.get_draft(int(context.args[0]))
    if rec is None:
        await update.message.reply_text("Bunday qoralama topilmadi.")
        return
    await send_draft(context.bot, update.effective_chat.id, rec)


# ---------- tugmalar ----------

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not is_admin(update):
        await query.answer("Ruxsat yo'q.", show_alert=True)
        log.warning("Begona foydalanuvchi tugma bosdi: %s", update.effective_user.id if update.effective_user else "?")
        return
    await query.answer()

    action, _, raw_id = (query.data or "").partition(":")
    if not raw_id.isdigit():
        return
    draft_id = int(raw_id)
    rec = database.get_draft(draft_id)
    if rec is None:
        await query.message.reply_text("Qoralama topilmadi.")
        return
    needed = "approved" if action.startswith("publish") else "awaiting_approval"
    if rec.status != needed:
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"#{draft_id} holati: {STATUS_LABELS.get(rec.status, rec.status)}")
        return

    if action.startswith("publish"):
        await handle_publish(query, action, rec)
        return

    try:
        if action == "approve":
            await query.edit_message_reply_markup(reply_markup=confirm_keyboard(draft_id))
        elif action == "back":
            await query.edit_message_reply_markup(reply_markup=approval_keyboard(draft_id))
        elif action == "confirm":
            database.set_status(draft_id, "approved")
            await query.edit_message_reply_markup(reply_markup=None)
            if rec.format == "carousel":
                mode = "🧪 Sinov rejimi (DRY_RUN): haqiqiy joylash bo'lmaydi." if settings.DRY_RUN else ""
                await query.message.reply_text(
                    f"✅ #{draft_id} tasdiqlandi. Hali hech narsa joylanmadi.\n{mode}".strip(),
                    reply_markup=publish_keyboard(draft_id))
            else:
                await query.message.reply_text(
                    f"✅ #{draft_id} tasdiqlandi. Reels'ni video suratga olgach, o'zingiz joylaysiz.")
        elif action == "reject":
            database.set_status(draft_id, "rejected")
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"❌ #{draft_id} rad etildi.")
        elif action == "edit":
            context.user_data["edit_id"] = draft_id
            await query.message.reply_text(
                f"✏️ #{draft_id}: nimani o'zgartirish kerak? Bitta xabarda yozing.\n"
                "Masalan: «3-so'zni boshqasiga almashtiring, caption qisqaroq bo'lsin».\n"
                "Bekor qilish: /cancel")
    except StatusError as e:
        await query.message.reply_text(f"⚠️ {e}")


async def handle_publish(query, action: str, rec: DraftRecord) -> None:
    """🚀 tugmalari. Joylash faqat 'approved' holatidan va ikkinchi tasdiqdan keyin."""
    from integrations.instagram import PublishError, publish_carousel

    if rec.format != "carousel":
        await query.message.reply_text("Hozircha faqat carousel joylanadi.")
        return
    if action == "publish":
        target = "🧪 DRY_RUN (sinov)" if settings.DRY_RUN else f"@{settings.load_brand()['brand']['instagram_handle'].lstrip('@')}"
        await query.edit_message_reply_markup(reply_markup=publish_confirm_keyboard(rec.id))
        await query.message.reply_text(
            f"⚠️ #{rec.id} ni Instagram'ga joylaysizmi?\nAkkaunt: {target}\n"
            f"Rasmlar: {len(rec.data.get('slides') or [])} ta\n"
            "Joylangan postni faqat Instagram ilovasida o'chirish mumkin.")
        return
    if action == "publish_later":
        await query.edit_message_reply_markup(reply_markup=publish_keyboard(rec.id))
        return
    if action != "publish_go":
        return

    try:
        database.set_status(rec.id, "publishing")    # ikki marta bosilsa — ikkinchisi to'xtaydi
    except StatusError as e:
        await query.message.reply_text(f"⚠️ {e}")
        return
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text("📤 Joylanmoqda... (1–2 daqiqa)")

    slides = [settings.ROOT_DIR / p for p in rec.data.get("slides") or []]
    try:
        result = await asyncio.to_thread(publish_carousel, slides, rec.data["caption_full"], log.info)
    except PublishError as e:
        database.set_status(rec.id, "approved")
        await query.message.reply_text(f"❌ Joylanmadi: {e}", reply_markup=publish_keyboard(rec.id))
        return
    except Exception:
        database.set_status(rec.id, "approved")
        log.exception("Joylashda kutilmagan xato")
        await query.message.reply_text("❌ Kutilmagan xato. Terminaldagi logni tekshiring.",
                                       reply_markup=publish_keyboard(rec.id))
        return

    if result.dry_run:
        database.set_status(rec.id, "approved")
        await query.message.reply_text(result.message, reply_markup=publish_keyboard(rec.id))
        return
    data = dict(rec.data, media_id=result.media_id, permalink=result.permalink)
    database.update_data(rec.id, data)
    database.set_status(rec.id, "published")
    await query.message.reply_text(f"🎉 #{rec.id} {result.message}!\n🔗 {result.permalink or ''}".strip())


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("edit_id", None)
    await update.message.reply_text("Bekor qilindi.")


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    edit_id: Optional[int] = context.user_data.pop("edit_id", None)
    if edit_id is None:
        await update.message.reply_text(HELP)
        return
    rec = database.get_draft(edit_id)
    try:
        database.set_status(edit_id, "revised")
    except StatusError as e:
        await update.message.reply_text(f"⚠️ {e}")
        return
    await update.message.reply_text(f"✏️ #{edit_id} izohingiz bilan qayta tayyorlanadi.")
    await generate_and_send(update, context, rec.topic, rec.hsk_level, rec.format,
                            feedback=update.message.text)


# ---------- ishga tushirish ----------

def build_app(token: str, admin_chat_id: str) -> Application:
    if not token:
        raise SystemExit("❌ TELEGRAM_BOT_TOKEN .env faylida yo'q.")
    if not str(admin_chat_id).strip().lstrip("-").isdigit():
        raise SystemExit("❌ TELEGRAM_ADMIN_CHAT_ID .env faylida yo'q yoki noto'g'ri (faqat raqam).")

    admin = filters.Chat(chat_id=int(admin_chat_id))
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start, filters=admin))
    app.add_handler(CommandHandler("help", cmd_start, filters=admin))
    app.add_handler(CommandHandler("new", cmd_new, filters=admin))
    app.add_handler(CommandHandler("reels", cmd_reels, filters=admin))
    app.add_handler(CommandHandler("list", cmd_list, filters=admin))
    app.add_handler(CommandHandler("show", cmd_show, filters=admin))
    app.add_handler(CommandHandler("cancel", cmd_cancel, filters=admin))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(admin & filters.TEXT & ~filters.COMMAND, on_text))
    # Admin bo'lmagan barcha xabarlar e'tiborsiz qoldiriladi (javob ham berilmaydi).
    return app


def run() -> None:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)  # token URL'da bo'ladi — logga chiqarmaymiz
    database.init_db()
    app = build_app(settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_ADMIN_CHAT_ID)
    print("🤖 Bot ishga tushdi. To'xtatish: Ctrl+C")
    app.run_polling()
