"""10. Analytics Agent — Instagram postlari statistikasidan haftalik hisobot tayyorlaydi.

1. Instagram Graph API'dan oxirgi postlar va ularning ko'rsatkichlari olinadi (faqat o'qish).
2. Raqamlar Python'da hisoblanadi (o'rtacha, eng yaxshi postlar) — Claude raqam o'ylab topmaydi.
3. Claude raqamlar asosida xulosa va tavsiyalar yozadi.
"""
from dataclasses import dataclass, field
from typing import List, Optional

from pydantic import BaseModel, Field

from agents.base import ask_claude, load_prompt

MIN_POSTS_FOR_AI = 3


@dataclass
class PostStats:
    caption: str
    kind: str                 # carousel / reels / rasm
    date: str
    permalink: str
    likes: int = 0
    comments: int = 0
    reach: int = 0
    saved: int = 0
    shares: int = 0

    @property
    def save_rate(self) -> float:
        return self.saved / self.reach * 100 if self.reach else 0.0

    @property
    def title(self) -> str:
        first = (self.caption or "").strip().splitlines()[0] if self.caption else "(captionsiz)"
        return first[:60]


@dataclass
class Summary:
    posts: List[PostStats]
    avg: dict = field(default_factory=dict)
    by_kind: dict = field(default_factory=dict)
    top: List[PostStats] = field(default_factory=list)


class AnalyticsInsights(BaseModel):
    xulosa: str = Field(description="2–3 gaplik umumiy xulosa")
    nima_ishladi: List[str] = Field(description="1–3 ta kuzatuv, raqamlarga tayanib")
    nima_ishlamadi: List[str] = Field(description="1–3 ta kuzatuv")
    tavsiyalar: List[str] = Field(description="3 ta aniq, amaliy tavsiya keyingi hafta uchun")


def _kind(media: dict) -> str:
    if media.get("media_product_type") == "REELS" or media.get("media_type") == "VIDEO":
        return "reels"
    if media.get("media_type") == "CAROUSEL_ALBUM":
        return "carousel"
    return "rasm"


def collect(client, limit: int = 12) -> List[PostStats]:
    posts = []
    for m in client.recent_media(limit):
        ins = client.media_insights(m["id"])
        posts.append(PostStats(
            caption=m.get("caption", ""), kind=_kind(m), date=(m.get("timestamp") or "")[:10],
            permalink=m.get("permalink", ""), likes=m.get("like_count", 0) or 0,
            comments=m.get("comments_count", 0) or 0, reach=ins.get("reach", 0) or 0,
            saved=ins.get("saved", 0) or 0, shares=ins.get("shares", 0) or 0))
    return posts


def summarize(posts: List[PostStats]) -> Summary:
    s = Summary(posts=posts)
    if not posts:
        return s
    keys = ["reach", "likes", "comments", "saved", "shares"]
    s.avg = {k: round(sum(getattr(p, k) for p in posts) / len(posts), 1) for k in keys}
    s.avg["save_rate"] = round(sum(p.save_rate for p in posts) / len(posts), 2)
    for kind in sorted({p.kind for p in posts}):
        group = [p for p in posts if p.kind == kind]
        s.by_kind[kind] = {"soni": len(group),
                           "ortacha_qamrov": round(sum(p.reach for p in group) / len(group), 1),
                           "ortacha_saqlash": round(sum(p.saved for p in group) / len(group), 1)}
    s.top = sorted(posts, key=lambda p: (p.saved, p.reach), reverse=True)[:3]
    return s


def summary_text(s: Summary) -> str:
    """Raqamlar — Claude'ga ham, Telegram'ga ham shu matn boradi."""
    if not s.posts:
        return "Hali postlar yo'q."
    a = s.avg
    lines = [f"Tahlil qilingan postlar: {len(s.posts)} ta",
             f"O'rtacha: qamrov {a['reach']}, layk {a['likes']}, izoh {a['comments']}, "
             f"saqlash {a['saved']}, ulashish {a['shares']}, saqlash darajasi {a['save_rate']}%",
             "Format bo'yicha:"]
    for kind, v in s.by_kind.items():
        lines.append(f"- {kind}: {v['soni']} ta, o'rtacha qamrov {v['ortacha_qamrov']}, "
                     f"o'rtacha saqlash {v['ortacha_saqlash']}")
    lines.append("Eng ko'p saqlangan postlar:")
    for p in s.top:
        lines.append(f"- [{p.kind}, {p.date}] «{p.title}» — saqlash {p.saved}, qamrov {p.reach}, "
                     f"izoh {p.comments}")
    lines.append("Barcha postlar:")
    for p in s.posts:
        lines.append(f"- [{p.kind}, {p.date}] «{p.title}»: qamrov {p.reach}, layk {p.likes}, "
                     f"izoh {p.comments}, saqlash {p.saved}, ulashish {p.shares}")
    return "\n".join(lines)


def analyze(s: Summary) -> Optional[AnalyticsInsights]:
    if len(s.posts) < MIN_POSTS_FOR_AI:
        return None
    return ask_claude(load_prompt("analytics"), summary_text(s), AnalyticsInsights, effort="medium")


def format_report(s: Summary, insights: Optional[AnalyticsInsights]) -> str:
    if not s.posts:
        return "📊 Hali Instagram'da postlar yo'q — hisobot uchun ma'lumot kam."
    a = s.avg
    lines = ["📊 HAFTALIK HISOBOT", f"Oxirgi {len(s.posts)} ta post bo'yicha o'rtacha:",
             f"👁 Qamrov: {a['reach']}   ❤️ Layk: {a['likes']}   💬 Izoh: {a['comments']}",
             f"📌 Saqlash: {a['saved']} ({a['save_rate']}%)   ↗️ Ulashish: {a['shares']}", "",
             "🏆 Eng ko'p saqlanganlar:"]
    for i, p in enumerate(s.top, 1):
        lines.append(f"{i}. «{p.title}» — 📌 {p.saved}, 👁 {p.reach}\n   {p.permalink}")
    if insights:
        lines += ["", f"🧠 {insights.xulosa}", "", "✅ Nima ishladi:"]
        lines += [f"• {x}" for x in insights.nima_ishladi]
        lines += ["", "⚠️ Nima ishlamadi:"] + [f"• {x}" for x in insights.nima_ishlamadi]
        lines += ["", "🎯 Tavsiyalar:"] + [f"{i}. {x}" for i, x in enumerate(insights.tavsiyalar, 1)]
    else:
        lines += ["", f"ℹ️ AI xulosasi uchun kamida {MIN_POSTS_FOR_AI} ta post kerak."]
    return "\n".join(lines)


def build_report(client, limit: int = 12):
    """(hisobot matni, Strategy uchun qisqa xulosa) qaytaradi."""
    s = summarize(collect(client, limit))
    insights = analyze(s)
    short = summary_text(s)
    if insights:
        short += "\nXulosa: " + insights.xulosa + "\nTavsiyalar: " + "; ".join(insights.tavsiyalar)
    return format_report(s, insights), short
