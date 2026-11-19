"""5. Carousel Design Agent — dars mazmunidan professional slaydlar yasaydi.

Qanday ishlaydi:
  1. design/templates/slide.html.j2 — HTML/CSS dizayn shabloni.
  2. Har bir slayd uchun shablon to'ldiriladi.
  3. Brauzer (Playwright + Chromium) sahifani ochib, 1080×1350 PNG rasmga aylantiradi.

Dizaynni o'zgartirish: shablon faylidagi CSS'ni tahrirlang. Ranglar — config/brand.yaml.

Carousel tuzilmasi:
  muqova → har bir so'z (田字格 katakda, ton ranglari bilan) → keng tarqalgan xato
  → test → takrorlash + CTA
Reels uchun: bitta 1080×1920 muqova rasmi.
"""
import os
import unicodedata
from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup, escape

from agents.education import LessonContent, Word
from config import settings

TEMPLATES_DIR = settings.ROOT_DIR / "design" / "templates"
CAROUSEL_SIZE = (1080, 1350)   # Instagram 4:5
REELS_SIZE = (1080, 1920)      # 9:16
MAX_WORDS = 6

TONE_MARKS = {
    1: "āēīōūǖĀĒĪŌŪǕ",
    2: "áéíóúǘÁÉÍÓÚǗ",
    3: "ǎěǐǒǔǚǍĚǏǑǓǙ",
    4: "àèìòùǜÀÈÌÒÙǛ",
}
DEFAULT_COLORS = {"primary": "#C8102E", "dark": "#7A0A1C", "secondary": "#F4B400",
                  "background": "#FFF7EC", "text": "#1C1B1F"}


class RenderError(Exception):
    """Slaydlarni chizishda xato (o'zbekcha tushuntirish bilan)."""




def is_hanzi(ch: str) -> bool:
    return "一" <= ch <= "鿿" or "㐀" <= ch <= "䶿"


def tone_of(syllable: str) -> int:
    """Pinyin bo'g'inining tonini aniqlaydi: 1–4, neytral bo'lsa 0."""
    s = unicodedata.normalize("NFC", syllable)
    for tone, marks in TONE_MARKS.items():
        if any(ch in marks for ch in s):
            return tone
    return 0


def char_cells(word: Word):
    """Ieroglif + uning pinyin bo'g'ini + toni. Bo'g'inlar soni mos kelmasa — pinyinsiz."""
    chars = [ch for ch in word.hanzi if is_hanzi(ch)]
    ok = len(chars) == len(word.bogin_pinyin) and len(chars) > 0
    cells = []
    for i, ch in enumerate(chars):
        syl = word.bogin_pinyin[i].strip() if ok else ""
        cells.append({"han": ch, "syl": syl, "tone": tone_of(syl) if ok else 0})
    return cells, ok


def highlight(sentence: str, word: str) -> Markup:
    """Misol gapdagi o'rganilayotgan so'zni ajratib ko'rsatadi (HTML xavfsiz)."""
    safe = str(escape(sentence))
    w = str(escape(word))
    if w and w in safe:
        safe = safe.replace(w, f"<mark>{w}</mark>", 1)
    return Markup(safe)


def title_html(title: str, accent: str) -> Markup:
    return highlight(title, accent.strip())


def box_size(n_chars: int, reels: bool = False) -> int:
    sizes = {1: 300, 2: 260, 3: 220, 4: 180}
    size = sizes.get(n_chars, 145)
    return int(size * 1.15) if reels else size


def build_slides(lesson: LessonContent) -> List[dict]:
    words = lesson.sozlar[:MAX_WORDS]
    total = len(words) + 4
    slides = [{"kind": "cover", "title": title_html(lesson.sarlavha, lesson.sarlavha_urgu)}]
    for i, w in enumerate(words, 1):
        cells, ok = char_cells(w)
        box = box_size(len(cells))
        slides.append({"kind": "word", "word": w, "index": i, "chars": cells,
                       "syllables_ok": ok, "box": box, "syl_size": max(30, int(box * 0.2)),
                       "example_html": highlight(w.misol_hanzi, w.hanzi)})
    slides += [{"kind": "mistake"}, {"kind": "quiz"}, {"kind": "final"}]
    for page, s in enumerate(slides, 1):
        s["page"], s["total"] = page, total
    return slides


def build_reels_cover(lesson: LessonContent) -> dict:
    cells, _ = char_cells(lesson.sozlar[0])
    box = box_size(len(cells), reels=True)
    return {"kind": "reels_cover", "title": title_html(lesson.sarlavha, lesson.sarlavha_urgu),
            "chars": cells, "box": box, "syl_size": max(34, int(box * 0.2)), "page": 1, "total": 1}


def _template():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)),
                      autoescape=select_autoescape(["html", "j2"]))
    return env.get_template("slide.html.j2")


def render_html(lesson: LessonContent, slide: dict, size=CAROUSEL_SIZE) -> str:
    brand = settings.load_brand()
    colors = {**DEFAULT_COLORS, **(brand.get("colors") or {})}
    b = {"name": brand["brand"]["name"], "instagram_handle": brand["brand"]["instagram_handle"]}
    return _template().render(lesson=lesson, slide=slide, brand=b, c=colors, W=size[0], H=size[1])


def _screenshot(pages: List[tuple], out_dir: Path) -> List[Path]:
    """pages: [(html, (w, h), fayl_nomi), ...] → PNG fayllar."""
    try:
        from playwright.sync_api import Error as PlaywrightError, sync_playwright
    except ImportError:
        raise RenderError("Playwright o'rnatilmagan. Buyruq: pip install -r requirements.txt "
                          "va keyin: playwright install chromium")
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    try:
        with sync_playwright() as p:
            exe = os.getenv("CHROMIUM_PATH") or None
            browser = p.chromium.launch(executable_path=exe)
            try:
                for html, (w, h), name in pages:
                    page = browser.new_page(viewport={"width": w, "height": h})
                    page.set_content(html, wait_until="networkidle", timeout=30000)
                    page.wait_for_function("window.__ready === true", timeout=15000)
                    path = out_dir / name
                    page.screenshot(path=str(path), type="png")
                    page.close()
                    paths.append(path)
            finally:
                browser.close()
    except PlaywrightError as e:
        if "Executable doesn't exist" in str(e):
            raise RenderError("Brauzer topilmadi. Buyruq: playwright install chromium")
        raise RenderError(f"Slaydlarni chizishda xato: {str(e).splitlines()[0]}")
    return paths


def render_carousel(lesson: LessonContent, out_dir: Path) -> List[Path]:
    """Barcha carousel slaydlarini out_dir ga PNG qilib saqlaydi."""
    pages = [(render_html(lesson, s), CAROUSEL_SIZE, f"slide_{s['page']:02d}.png")
             for s in build_slides(lesson)]
    return _screenshot(pages, out_dir)


def render_reels_cover(lesson: LessonContent, out_dir: Path) -> List[Path]:
    """Reels uchun 1080×1920 muqova rasmini yasaydi."""
    html = render_html(lesson, build_reels_cover(lesson), REELS_SIZE)
    return _screenshot([(html, REELS_SIZE, "reels_cover.png")], out_dir)
