"""2-bosqich testlari: baza holatlari, carousel, bot yordamchilari. API va internet kerak emas.

Ishga tushirish:  python -m unittest discover tests
"""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from config import settings
from storage import database
from storage.database import StatusError
from tests.sample_lesson import SAMPLE_LESSON


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.db"

    def tearDown(self):
        self.tmp.cleanup()

    def new(self, status="qc_passed"):
        return database.save_draft("salom", 1, "carousel", status, {"x": 1}, db_path=self.db)

    def test_happy_path(self):
        i = self.new()
        database.set_status(i, "awaiting_approval", db_path=self.db)
        database.set_status(i, "approved", db_path=self.db)
        self.assertEqual(database.get_draft(i, db_path=self.db).status, "approved")

    def test_cannot_publish_without_approval(self):
        i = self.new()
        with self.assertRaises(StatusError):
            database.set_status(i, "published", db_path=self.db)
        database.set_status(i, "awaiting_approval", db_path=self.db)
        with self.assertRaises(StatusError):
            database.set_status(i, "published", db_path=self.db)

    def test_rejected_is_final(self):
        i = self.new()
        database.set_status(i, "awaiting_approval", db_path=self.db)
        database.set_status(i, "rejected", db_path=self.db)
        with self.assertRaises(StatusError):
            database.set_status(i, "approved", db_path=self.db)

    def test_new_draft_cannot_start_approved(self):
        with self.assertRaises(StatusError):
            self.new(status="approved")

    def test_list_newest_first(self):
        a, b = self.new(), self.new()
        self.assertEqual([d.id for d in database.list_drafts(db_path=self.db)], [b, a])


class CarouselTest(unittest.TestCase):
    def test_tone_detection(self):
        from agents.carousel import tone_of
        self.assertEqual([tone_of(x) for x in ["mā", "má", "mǎ", "mà", "ma", "lǜ"]], [1, 2, 3, 4, 0, 4])

    def test_char_cells_pair_syllables(self):
        from agents.carousel import char_cells
        cells, ok = char_cells(SAMPLE_LESSON.sozlar[0])
        self.assertTrue(ok)
        self.assertEqual([(c["han"], c["syl"], c["tone"]) for c in cells],
                         [("服", "fú", 2), ("务", "wù", 4), ("员", "yuán", 2)])

    def test_highlight_escapes_html(self):
        from agents.carousel import highlight
        self.assertEqual(str(highlight("<b>我要</b>", "我要")), "&lt;b&gt;<mark>我要</mark>&lt;/b&gt;")

    def test_slide_structure(self):
        from agents.carousel import build_slides
        kinds = [s["kind"] for s in build_slides(SAMPLE_LESSON)]
        self.assertEqual(kinds, ["cover"] + ["word"] * 6 + ["mistake", "quiz", "final"])

    def test_html_renders_all_slides(self):
        from agents.carousel import build_slides, render_html
        for s in build_slides(SAMPLE_LESSON):
            html = render_html(SAMPLE_LESSON, s)
            self.assertIn("window.__ready", html)
        self.assertIn("<mark>6 ta ibora</mark>", render_html(SAMPLE_LESSON, build_slides(SAMPLE_LESSON)[0]))

    def test_renders_png(self):
        """Brauzer o'rnatilgan bo'lsa — haqiqiy PNG yasaladi, bo'lmasa o'tkazib yuboriladi."""
        from agents.carousel import RenderError, render_reels_cover
        try:
            with tempfile.TemporaryDirectory() as tmp:
                paths = render_reels_cover(SAMPLE_LESSON, Path(tmp))
                from PIL import Image
                with Image.open(paths[0]) as im:
                    self.assertEqual(im.size, (1080, 1920))
        except RenderError as e:
            self.skipTest(f"Brauzer yo'q: {e}")


class BotHelpersTest(unittest.TestCase):
    def test_parse_topic_args(self):
        from integrations.telegram_bot import parse_topic_args
        self.assertEqual(parse_topic_args(["restoranda", "buyurtma", "3"]), ("restoranda buyurtma", 3))
        self.assertEqual(parse_topic_args(["salomlashish"]), ("salomlashish", 1))
        self.assertEqual(parse_topic_args(["2026", "yil"]), ("2026 yil", 1))
        self.assertEqual(parse_topic_args(["raqamlar", "9"]), ("raqamlar 9", 1))

    def test_is_admin(self):
        from integrations import telegram_bot as tb
        old = settings.TELEGRAM_ADMIN_CHAT_ID
        try:
            settings.TELEGRAM_ADMIN_CHAT_ID = "111"
            upd = lambda cid, uid: SimpleNamespace(
                effective_chat=SimpleNamespace(id=cid, type="private"),
                effective_user=SimpleNamespace(id=uid))
            self.assertTrue(tb.is_admin(upd(111, 111)))
            self.assertFalse(tb.is_admin(upd(222, 222)))
            settings.TELEGRAM_ADMIN_CHAT_ID = ""
            self.assertFalse(tb.is_admin(upd(111, 111)))   # admin sozlanmagan — hech kim
        finally:
            settings.TELEGRAM_ADMIN_CHAT_ID = old

    def test_build_app_requires_admin(self):
        from integrations.telegram_bot import build_app
        with self.assertRaises(SystemExit):
            build_app("123:abc", "")
        app = build_app("123:abc", "111")
        self.assertTrue(app.handlers)


if __name__ == "__main__":
    unittest.main()
