"""Haftalik ishlar: kontent rejasi va statistika hisoboti.

Telegram bot (/plan, /report) ham, n8n jadvali (python main.py --plan --notify) ham
shu funksiyalarni chaqiradi. Bu yerda HECH NARSA joylanmaydi.
"""
import logging
from typing import Tuple

from agents.strategy import WeekPlan, create_week_plan, format_plan
from config import settings
from storage import database

log = logging.getLogger("balla.weekly")


def instagram_configured() -> bool:
    return bool(settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_BUSINESS_ACCOUNT_ID)


def make_report() -> Tuple[str, str]:
    """(Telegram uchun hisobot, Strategy uchun qisqa xulosa)."""
    from agents.analytics import build_report
    from integrations.instagram import InstagramClient
    if not instagram_configured():
        return ("📊 Hisobot uchun Instagram ulanmagan (.env: INSTAGRAM_ACCESS_TOKEN, "
                "INSTAGRAM_BUSINESS_ACCOUNT_ID). README'ning 8-bo'limiga qarang.", "")
    return build_report(InstagramClient())


def make_plan() -> Tuple[int, WeekPlan, str]:
    """Reja tuzadi va bazaga saqlaydi. Statistika bo'lsa — uni ham hisobga oladi."""
    analytics = ""
    if instagram_configured():
        try:
            _, analytics = make_report()
        except Exception as e:          # statistika bo'lmasa ham reja tuziladi
            log.warning("Statistika olinmadi: %s", e)
    plan = create_week_plan(database.recent_topics(), analytics)
    plan_id = database.save_plan(plan.model_dump())
    return plan_id, plan, format_plan(plan)
