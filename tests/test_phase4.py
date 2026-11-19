"""4-bosqich testlari: Strategy, Analytics, haftalik ishlar. API va tarmoq kerak emas.

Ishga tushirish:  python -m unittest discover tests
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agents import analytics, strategy
from agents.strategy import PlanItem, WeekPlan, plan_issues
from config import settings
from storage import database


def item(kun="Dushanba", fmt="carousel", mavzu="Taksida manzil aytish", hsk=1):
    return PlanItem(kun=kun, format=fmt, mavzu=mavzu, hsk_daraja=hsk, rukn="Real vaziyatlar",
                    maqsad="saqlash", sabab="Ko'p so'raladi")


def good_plan():
    return WeekPlan(hafta_goyasi="Xitoyda birinchi hafta", postlar=[
        item("Dushanba", "carousel", "Taksida manzil aytish", 1),
        item("Seshanba", "reels", "Raqamlarni to'g'ri talaffuz qilish", 1),
        item("Chorshanba", "carousel", "HSK 2 dagi 5 ta chalkash so'z", 2),
        item("Payshanba", "reels", "Bozorda narx so'rash", 2),
        item("Juma", "carousel", "Xitoyda mehmonga borish odobi", 4),
    ])


class StrategyTest(unittest.TestCase):
    def test_good_plan_has_no_issues(self):
        self.assertEqual(plan_issues(good_plan()), [])

    def test_wrong_counts_and_duplicates(self):
        plan = good_plan()
        plan.postlar[1].format = "carousel"
        plan.postlar[4].mavzu = plan.postlar[0].mavzu
        plan.postlar[2].hsk_daraja = 9
        issues = " | ".join(plan_issues(plan))
        self.assertIn("Reels", issues)
        self.assertIn("takrorlangan", issues)
        self.assertIn("HSK 9", issues)

    def test_retries_once_when_plan_is_bad(self):
        bad = good_plan()
        bad.postlar = bad.postlar[:3]
        with mock.patch.object(strategy, "ask_claude", side_effect=[bad, good_plan()]) as m:
            plan = strategy.create_week_plan(["restoranda buyurtma berish"])
        self.assertEqual(m.call_count, 2)
        self.assertIn("muammolar", m.call_args_list[1].args[1])
        self.assertIn("restoranda buyurtma berish", m.call_args_list[0].args[1])
        self.assertEqual(len(plan.postlar), 5)

    def test_plan_keyboard(self):
        from integrations.telegram_bot import plan_keyboard
        kb = plan_keyboard(7, good_plan())
        data = [b.callback_data for row in kb.inline_keyboard for b in row]
        self.assertEqual(data, [f"plan:7:{i}" for i in range(5)])


class PlanStorageTest(unittest.TestCase):
    def test_save_and_recent_topics(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "t.db"
            database.save_draft("Restoranda buyurtma", 2, "carousel", "qc_passed", {}, db_path=db)
            pid = database.save_plan(good_plan().model_dump(), db_path=db)
            self.assertEqual(database.get_plan(pid, db_path=db)["postlar"][0]["mavzu"], "Taksida manzil aytish")
            topics = database.recent_topics(db_path=db)
            self.assertIn("Restoranda buyurtma", topics)
            self.assertIn("Bozorda narx so'rash", topics)
            self.assertEqual(len(topics), len({t.lower() for t in topics}))


class FakeInsightsClient:
    def recent_media(self, limit=12):
        return [
            {"id": "1", "caption": "Restoranda 6 ta ibora\nbatafsil", "media_type": "CAROUSEL_ALBUM",
             "timestamp": "2026-11-10T09:00:00+0000", "permalink": "https://instagram.com/p/1", "like_count": 40,
             "comments_count": 12},
            {"id": "2", "caption": "Ton xatosi", "media_type": "VIDEO", "media_product_type": "REELS",
             "timestamp": "2026-11-11T09:00:00+0000", "permalink": "https://instagram.com/p/2", "like_count": 90,
             "comments_count": 5},
            {"id": "3", "caption": "", "media_type": "CAROUSEL_ALBUM",
             "timestamp": "2026-11-12T09:00:00+0000", "permalink": "https://instagram.com/p/3", "like_count": 10,
             "comments_count": 1},
        ]

    def media_insights(self, media_id):
        return {"1": {"reach": 1000, "saved": 120, "shares": 30},
                "2": {"reach": 3000, "saved": 45, "shares": 60},
                "3": {}}[media_id]


class AnalyticsTest(unittest.TestCase):
    def test_summary_numbers(self):
        s = analytics.summarize(analytics.collect(FakeInsightsClient()))
        self.assertEqual(len(s.posts), 3)
        self.assertEqual(s.top[0].permalink, "https://instagram.com/p/1")       # eng ko'p saqlangan
        self.assertEqual(s.avg["saved"], 55.0)
        self.assertEqual(s.by_kind["reels"]["soni"], 1)
        self.assertAlmostEqual(s.posts[0].save_rate, 12.0)
        self.assertEqual(s.posts[2].title, "(captionsiz)")

    def test_report_with_ai(self):
        fake = analytics.AnalyticsInsights(xulosa="Carousel'lar yaxshi saqlanmoqda.",
                                           nima_ishladi=["Real vaziyatlar"], nima_ishlamadi=["Captionsiz post"],
                                           tavsiyalar=["A", "B", "C"])
        with mock.patch.object(analytics, "ask_claude", return_value=fake) as m:
            text, short = analytics.build_report(FakeInsightsClient())
        self.assertIn("saqlash darajasi", m.call_args.args[1])
        self.assertIn("HAFTALIK HISOBOT", text)
        self.assertIn("🎯 Tavsiyalar", text)
        self.assertIn("Tavsiyalar: A; B; C", short)

    def test_few_posts_skip_ai(self):
        client = FakeInsightsClient()
        client.recent_media = lambda limit=12: FakeInsightsClient().recent_media()[:2]
        with mock.patch.object(analytics, "ask_claude") as m:
            text, _ = analytics.build_report(client)
        m.assert_not_called()
        self.assertIn("kamida 3 ta post", text)

    def test_empty(self):
        s = analytics.summarize([])
        self.assertIn("Hali", analytics.format_report(s, None))


class WeeklyTest(unittest.TestCase):
    def test_report_without_instagram(self):
        from agents import weekly
        with mock.patch.object(settings, "INSTAGRAM_ACCESS_TOKEN", ""):
            text, short = weekly.make_report()
        self.assertIn("ulanmagan", text)
        self.assertEqual(short, "")

    def test_make_plan_saves(self):
        from agents import weekly
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(database, "DB_PATH", Path(tmp) / "t.db"), \
                mock.patch.object(settings, "INSTAGRAM_ACCESS_TOKEN", ""), \
                mock.patch.object(weekly, "create_week_plan", return_value=good_plan()):
            plan_id, plan, text = weekly.make_plan()
            self.assertIsNotNone(database.get_plan(plan_id))
        self.assertIn("HAFTALIK KONTENT REJASI", text)
        self.assertIn("Hech narsa avtomatik joylanmaydi", text)


if __name__ == "__main__":
    unittest.main()
