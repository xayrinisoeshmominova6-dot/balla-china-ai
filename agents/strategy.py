"""3. Content Strategy Agent — haftalik kontent rejasini tuzadi.

Hisobga oladi: brand.yaml dagi ruknlar va post soni, oxirgi mavzular (takrorlanmasligi uchun),
va bo'lsa — Analytics hisobotidagi xulosalar.
Reja faqat TAKLIF: har bir postni siz Telegram'da "▶️ Yaratish" bilan boshlaysiz.
"""
from typing import List, Literal

from pydantic import BaseModel, Field

from agents.base import ask_claude, load_prompt
from config import settings

DAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


class PlanItem(BaseModel):
    kun: str = Field(description="Hafta kuni o'zbekcha: Dushanba ... Yakshanba")
    format: Literal["carousel", "reels"]
    mavzu: str = Field(description="Aniq mavzu, 3–8 so'z (masalan: 'Taksida manzil aytish')")
    hsk_daraja: int = Field(description="1–6")
    rukn: str = Field(description="Qaysi kontent rukniga tegishli")
    maqsad: Literal["saqlash", "izoh", "ulashish", "obuna"]
    sabab: str = Field(description="Nega aynan shu mavzu — 1 gap")


class WeekPlan(BaseModel):
    hafta_goyasi: str = Field(description="Haftaning umumiy g'oyasi, 1 gap")
    postlar: List[PlanItem]


def plan_issues(plan: WeekPlan) -> List[str]:
    """Rejani oddiy qoidalar bilan tekshiradi."""
    cfg = settings.load_brand()["strategy"]
    issues = []
    if len(plan.postlar) != cfg["posts_per_week"]:
        issues.append(f"{len(plan.postlar)} ta post (kerak: {cfg['posts_per_week']})")
    reels = sum(1 for p in plan.postlar if p.format == "reels")
    if reels != cfg["reels_per_week"]:
        issues.append(f"{reels} ta Reels (kerak: {cfg['reels_per_week']})")
    for p in plan.postlar:
        if not 1 <= p.hsk_daraja <= 6:
            issues.append(f"«{p.mavzu}»: HSK {p.hsk_daraja} noto'g'ri")
        if p.kun not in DAYS:
            issues.append(f"«{p.mavzu}»: kun noto'g'ri ({p.kun})")
    if len({p.mavzu.lower() for p in plan.postlar}) != len(plan.postlar):
        issues.append("Bir xil mavzular takrorlangan")
    return issues


def create_week_plan(recent_topics: List[str], analytics_summary: str = "") -> WeekPlan:
    cfg = settings.load_brand()["strategy"]
    levels = settings.load_brand()["content"]["hsk_levels"]
    message = (
        f"Haftasiga postlar: {cfg['posts_per_week']} ta, shundan Reels: {cfg['reels_per_week']} ta.\n"
        f"HSK darajalari: {levels} (aralash).\n"
        f"Ruknlar:\n" + "\n".join(f"- {p}" for p in cfg["pillars"]) + "\n\n"
        "Oxirgi mavzular (TAKRORLAMANG):\n" + ("\n".join(f"- {t}" for t in recent_topics) or "- hali yo'q") + "\n"
    )
    if analytics_summary:
        message += f"\nO'tgan postlar statistikasi xulosasi:\n{analytics_summary}\n"
    plan = ask_claude(load_prompt("strategy"), message, WeekPlan, effort="medium")
    issues = plan_issues(plan)
    if issues:
        message += "\nOldingi variantdagi muammolar — tuzating:\n" + "\n".join(f"- {i}" for i in issues)
        plan = ask_claude(load_prompt("strategy"), message, WeekPlan, effort="medium")
    return plan


def format_plan(plan: WeekPlan) -> str:
    icons = {"carousel": "🖼", "reels": "🎬"}
    lines = ["🗓 HAFTALIK KONTENT REJASI", f"💡 {plan.hafta_goyasi}", ""]
    for i, p in enumerate(plan.postlar, 1):
        lines += [f"{i}. {p.kun} · {icons.get(p.format, '')} {p.format} · HSK {p.hsk_daraja}",
                  f"   «{p.mavzu}»",
                  f"   Rukn: {p.rukn} · Maqsad: {p.maqsad}",
                  f"   {p.sabab}", ""]
    lines.append("Post yaratish uchun pastdagi tugmani bosing. Hech narsa avtomatik joylanmaydi.")
    return "\n".join(lines)
