"""3-bosqich testlari: Instagram'ga joylash. Haqiqiy tarmoq so'rovi YUBORILMAYDI.

Ishga tushirish:  python -m unittest discover tests
"""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from config import settings
from integrations import instagram
from integrations.instagram import InstagramClient, PublishError, publish_carousel

TOKEN = "SECRET_TOKEN_123"


class FakeResponse:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body


class FakeSession:
    """Instagram va imgbb o'rniga ishlaydi, barcha so'rovlarni yozib boradi."""

    def __init__(self, username="balla_china_language", status_seq=("IN_PROGRESS", "FINISHED")):
        self.calls, self.username, self.status_seq, self.n = [], username, list(status_seq), 0

    def _id(self):
        self.n += 1
        return f"id{self.n}"

    def get(self, url, params=None, timeout=None):
        self.calls.append(("GET", url, params))
        fields = params.get("fields")
        if fields == "username":
            return FakeResponse({"username": self.username})
        if fields == "status_code":
            return FakeResponse({"status_code": self.status_seq.pop(0)})
        if fields == "permalink":
            return FakeResponse({"permalink": "https://www.instagram.com/p/TEST/"})
        return FakeResponse({}, 404)

    def post(self, url, params=None, data=None, timeout=None):
        self.calls.append(("POST", url, data))
        if "imgbb" in url:
            return FakeResponse({"data": {"url": f"https://i.ibb.co/{self._id()}.jpg"}})
        if url.endswith("/media_publish"):
            return FakeResponse({"id": "MEDIA_1"})
        return FakeResponse({"id": self._id()})


class InstagramTest(unittest.TestCase):
    def setUp(self):
        self.old = {k: getattr(settings, k) for k in
                    ("DRY_RUN", "INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID", "IMGBB_API_KEY")}
        settings.INSTAGRAM_ACCESS_TOKEN = TOKEN
        settings.INSTAGRAM_BUSINESS_ACCOUNT_ID = "17841400000000000"
        settings.IMGBB_API_KEY = "IMGBB_KEY"
        self.tmp = tempfile.TemporaryDirectory()
        self.slides = []
        for i in range(3):
            p = Path(self.tmp.name) / f"slide_{i}.png"
            Image.new("RGB", (1080, 1350), "red").save(p)
            self.slides.append(p)

    def tearDown(self):
        for k, v in self.old.items():
            setattr(settings, k, v)
        self.tmp.cleanup()

    def client(self, session):
        return lambda: InstagramClient(session=session, sleep=lambda s: None)

    def test_dry_run_sends_nothing(self):
        settings.DRY_RUN = True
        session = FakeSession()
        result = publish_carousel(self.slides, "caption", client_factory=self.client(session))
        self.assertTrue(result.dry_run)
        self.assertEqual(session.calls, [])

    def test_full_publish_flow(self):
        settings.DRY_RUN = False
        session = FakeSession()
        result = publish_carousel(self.slides, "Salom", log=lambda m: None,
                                  client_factory=self.client(session))
        self.assertFalse(result.dry_run)
        self.assertEqual(result.permalink, "https://www.instagram.com/p/TEST/")
        posts = [c for c in session.calls if c[0] == "POST"]
        # 3 ta rasm yuklash → 3 ta item → 1 ta CAROUSEL → 1 ta publish
        self.assertEqual(sum("imgbb" in c[1] for c in posts), 3)
        items = [c for c in posts if c[2].get("is_carousel_item") == "true"]
        self.assertEqual(len(items), 3)
        carousel = [c for c in posts if c[2].get("media_type") == "CAROUSEL"][0]
        self.assertEqual(carousel[2]["caption"], "Salom")
        self.assertEqual(len(carousel[2]["children"].split(",")), 3)
        self.assertTrue(posts[-1][1].endswith("/media_publish"))

    def test_wrong_account_publishes_nothing(self):
        settings.DRY_RUN = False
        session = FakeSession(username="boshqa_akkaunt")
        with self.assertRaises(PublishError) as ctx:
            publish_carousel(self.slides, "x", log=lambda m: None, client_factory=self.client(session))
        self.assertIn("mos emas", str(ctx.exception))
        self.assertFalse(any(c[0] == "POST" for c in session.calls))

    def test_error_message_hides_token(self):
        settings.DRY_RUN = False

        class BadSession(FakeSession):
            def get(self, url, params=None, timeout=None):
                return FakeResponse({"error": {"message": f"Invalid token {TOKEN}"}}, 400)

        with self.assertRaises(PublishError) as ctx:
            publish_carousel(self.slides, "x", log=lambda m: None, client_factory=self.client(BadSession()))
        self.assertNotIn(TOKEN, str(ctx.exception))
        self.assertIn("***", str(ctx.exception))

    def test_container_error_stops(self):
        settings.DRY_RUN = False
        session = FakeSession(status_seq=("ERROR",))
        with self.assertRaises(PublishError):
            publish_carousel(self.slides, "x", log=lambda m: None, client_factory=self.client(session))
        self.assertFalse(any(c[1].endswith("/media_publish") for c in session.calls))

    def test_validation(self):
        settings.DRY_RUN = True
        with self.assertRaises(PublishError):
            publish_carousel(self.slides[:1], "x")                  # 1 ta rasm — kam
        with self.assertRaises(PublishError):
            publish_carousel(self.slides, "a" * 2300)               # caption uzun

    def test_jpeg_conversion(self):
        data = instagram.to_jpeg(self.slides[0])
        self.assertEqual(data[:2], b"\xff\xd8")                     # JPEG belgisi


class PublishStatusTest(unittest.TestCase):
    def test_publish_requires_approval(self):
        from storage import database
        from storage.database import StatusError
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.db"
            i = database.save_draft("t", 1, "carousel", "qc_passed", {}, db_path=db)
            database.set_status(i, "awaiting_approval", db_path=db)
            with self.assertRaises(StatusError):
                database.set_status(i, "publishing", db_path=db)   # tasdiqsiz — mumkin emas
            database.set_status(i, "approved", db_path=db)
            database.set_status(i, "publishing", db_path=db)
            with self.assertRaises(StatusError):
                database.set_status(i, "publishing", db_path=db)   # ikki marta — mumkin emas
            database.set_status(i, "published", db_path=db)


if __name__ == "__main__":
    unittest.main()
