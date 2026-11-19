"""Sifat nazorati qoidalarini API'siz tekshiradi.

Ishga tushirish:  python -m unittest discover tests
"""
import unittest

from agents.caption import Caption
from agents.education import LessonContent, Word
from agents.quality import rule_checks

TAGS = ["#xitoytili", "#xitoytilinioʻrganamiz", "#hsk", "#ballachina"]


def make_lesson(tarjima="salom"):
    word = Word(hanzi="你好", pinyin="nǐ hǎo", tarjima=tarjima,
                misol_hanzi="你好！", misol_pinyin="Nǐ hǎo!", misol_tarjima="Salom!")
    return LessonContent(mavzu="salomlashish", hsk_daraja=1, sarlavha="Salomlashish",
                         sozlar=[word], maslahat="Har kuni takrorlang.")


def make_caption(matn="Bugun salomlashishni o'rganamiz.", tags=TAGS):
    return Caption(hook="Xitoycha salom deyishni bilasizmi?", matn=matn,
                   cta="Saqlab qo'ying 📌", heshteglar=list(tags))


class RuleChecksTest(unittest.TestCase):
    def test_clean_content_has_no_errors(self):
        self.assertEqual(rule_checks(make_lesson(), make_caption()), [])

    def test_cyrillic_in_translation_is_error(self):
        issues = rule_checks(make_lesson(tarjima="салом"), make_caption())
        self.assertTrue(any(i.jiddiylik == "xato" and "Kirill" in i.muammo for i in issues))

    def test_cyrillic_in_caption_is_error(self):
        issues = rule_checks(make_lesson(), make_caption(matn="Бугун"))
        self.assertTrue(any(i.joy == "caption" for i in issues))

    def test_too_long_caption_is_error(self):
        issues = rule_checks(make_lesson(), make_caption(matn="a" * 3000))
        self.assertTrue(any("uzun" in i.muammo for i in issues))

    def test_missing_hashtag_is_warning(self):
        issues = rule_checks(make_lesson(), make_caption(tags=TAGS[:2]))
        self.assertTrue(issues)
        self.assertTrue(all(i.jiddiylik == "ogohlantirish" for i in issues))


if __name__ == "__main__":
    unittest.main()
