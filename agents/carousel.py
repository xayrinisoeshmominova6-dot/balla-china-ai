"""5. Carousel Design Agent — dars mazmunidan Instagram carousel rasmlarini chizadi.

Bu agent Claude'ni chaqirmaydi: tayyor dars mazmunini brend ranglarida
1080x1350 o'lchamdagi PNG slaydlarga aylantiradi (Pillow kutubxonasi).

Slaydlar:  1) Muqova  →  2..N) Har bir so'z  →  oxirgi) Maslahat + CTA
"""
from pathlib import Path
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont

from agents.education import LessonContent, Word
from config import settings

W, H = 1080, 1350
MARGIN = 90

# Xitoycha ieroglif + lotin harflarini ko'rsata oladigan shriftlar.
# Eng yaxshisi: Noto Sans SC ni design/fonts/ papkasiga qo'yish (README'ga qarang).
SYSTEM_FONTS = [
    "C:/Windows/Fonts/msyh.ttc",                                   # Windows
    "C:/Windows/Fonts/simhei.ttf",
    "/System/Library/Fonts/PingFang.ttc",                          # Mac
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",      # Linux
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]


class FontNotFoundError(Exception):
    pass


def find_font() -> Path:
    fonts_dir = settings.ROOT_DIR / "design" / "fonts"
    for pattern in ("*.otf", "*.ttf", "*.ttc"):
        found = sorted(fonts_dir.glob(pattern))
        if found:
            return found[0]
    for path in SYSTEM_FONTS:
        if Path(path).exists():
            return Path(path)
    raise FontNotFoundError(
        "Xitoycha shrift topilmadi. Noto Sans SC shriftini yuklab olib, "
        "design/fonts/ papkasiga qo'ying (README'ga qarang)."
    )


class Renderer:
    def __init__(self, font_path: Optional[Path] = None):
        self.font_path = str(font_path or find_font())
        c = settings.load_brand()["colors"]
        self.primary, self.secondary = c["primary"], c["secondary"]
        self.bg, self.text = c["background"], c["text"]
        self.brand = settings.load_brand()["brand"]

    def font(self, size: int) -> ImageFont.FreeTypeFont:
        return ImageFont.truetype(self.font_path, size)

    def _canvas(self):
        img = Image.new("RGB", (W, H), self.bg)
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, W, 24], fill=self.primary)
        d.rectangle([0, H - 24, W, H], fill=self.primary)
        return img, d

    def _wrap(self, d, text: str, font, max_w: int) -> List[str]:
        words, lines, cur = text.split(), [], ""
        for w in words:
            test = f"{cur} {w}".strip()
            if d.textlength(test, font=font) <= max_w or not cur:
                cur = test
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        # Bo'shliqsiz uzun qatorlarni (masalan, xitoycha gap) belgi bo'yicha bo'lamiz
        result = []
        for line in lines:
            while d.textlength(line, font=font) > max_w and len(line) > 1:
                cut = len(line)
                while cut > 1 and d.textlength(line[:cut], font=font) > max_w:
                    cut -= 1
                result.append(line[:cut])
                line = line[cut:]
            result.append(line)
        return result

    def _text_block(self, d, text, size, y, color=None, max_lines=None) -> int:
        """Matnni markazga yozadi, kerak bo'lsa shriftni kichraytiradi. Yangi y ni qaytaradi."""
        max_w = W - 2 * MARGIN
        while True:
            f = self.font(size)
            lines = self._wrap(d, text, f, max_w)
            if not max_lines or len(lines) <= max_lines or size <= 24:
                break
            size -= 4
        for line in lines:
            tw = d.textlength(line, font=f)
            d.text(((W - tw) / 2, y), line, font=f, fill=color or self.text)
            y += int(size * 1.3)
        return y

    def _badge(self, d, text: str) -> None:
        f = self.font(40)
        tw = d.textlength(text, font=f)
        x, y = W - MARGIN - tw - 40, 70
        d.rounded_rectangle([x, y, x + tw + 40, y + 70], radius=35, fill=self.primary)
        d.text((x + 20, y + 10), text, font=f, fill="#FFFFFF")

    def _footer(self, d, page: int, total: int) -> None:
        f = self.font(32)
        d.text((MARGIN, H - 90), self.brand["instagram_handle"], font=f, fill=self.primary)
        p = f"{page}/{total}"
        d.text((W - MARGIN - d.textlength(p, font=f), H - 90), p, font=f, fill="#888888")

    def cover(self, lesson: LessonContent, total: int) -> Image.Image:
        img, d = self._canvas()
        self._badge(d, f"HSK {lesson.hsk_daraja}")
        y = self._text_block(d, lesson.sarlavha, 88, 420, color=self.primary, max_lines=4)
        d.rectangle([W / 2 - 80, y + 30, W / 2 + 80, y + 38], fill=self.secondary)
        self._text_block(d, "Varaqlang →", 44, y + 90, color="#666666")
        self._footer(d, 1, total)
        return img

    def word(self, w: Word, level: int, page: int, total: int) -> Image.Image:
        img, d = self._canvas()
        self._badge(d, f"HSK {level}")
        y = self._text_block(d, w.hanzi, 220, 230, color=self.primary, max_lines=2)
        y = self._text_block(d, w.pinyin, 64, y + 20, max_lines=2)
        y = self._text_block(d, w.tarjima, 56, y + 10, color="#444444", max_lines=3)
        d.line([MARGIN, y + 40, W - MARGIN, y + 40], fill=self.secondary, width=4)
        y = self._text_block(d, "Misol:", 38, y + 80, color="#888888")
        y = self._text_block(d, w.misol_hanzi, 54, y + 10, max_lines=2)
        y = self._text_block(d, w.misol_pinyin, 38, y + 5, color="#555555", max_lines=2)
        self._text_block(d, w.misol_tarjima, 38, y + 5, color="#555555", max_lines=3)
        self._footer(d, page, total)
        return img

    def final(self, lesson: LessonContent, total: int) -> Image.Image:
        img, d = self._canvas()
        y = self._text_block(d, "Maslahat", 64, 280, color=self.primary)
        y = self._text_block(d, lesson.maslahat, 50, y + 40, max_lines=8)
        d.rounded_rectangle([MARGIN + 80, y + 100, W - MARGIN - 80, y + 220],
                            radius=60, fill=self.primary)
        self._text_block(d, "Saqlab qo'ying!", 52, y + 128, color="#FFFFFF")
        self._footer(d, total, total)
        return img


def render_carousel(lesson: LessonContent, out_dir: Path) -> List[Path]:
    """Barcha slaydlarni out_dir ga PNG qilib saqlaydi va fayl yo'llarini qaytaradi."""
    r = Renderer()
    words = lesson.sozlar[:8]           # Instagram carousel: ko'pi bilan 10 ta slayd
    total = len(words) + 2
    slides = [r.cover(lesson, total)]
    slides += [r.word(w, lesson.hsk_daraja, i + 2, total) for i, w in enumerate(words)]
    slides.append(r.final(lesson, total))

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, img in enumerate(slides, 1):
        p = out_dir / f"slide_{i:02d}.png"
        img.save(p, "PNG")
        paths.append(p)
    return paths
