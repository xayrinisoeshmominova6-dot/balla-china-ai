"""Sifat nazorati qoidalarini API'siz tekshiradi.

Ishga tushirish:  python -m unittest discover tests
"""
import unittest

from agents.caption import Caption
from agents.quality import rule_checks
from tests.sample_lesson import SAMPLE_LESSON

TAGS = ["#xitoytili", "#xitoytilinioʻrganamiz", "#hsk", "#ballachina"]


def make_lesson(**changes):
    return SAMPLE_LESSON.model_copy(deep=True, update=changes)


def make_caption(matn="Bugun restoranda kerak bo'ladigan iboralarni o'rganamiz.", tags=TAGS):
    return Caption(hook="Xitoy restoranida menyuni tushunmay qoldingizmi?", matn=matn,
                   cta="Saqlab qo'ying 📌", heshteglar=list(tags))


def errors(issues):
    return [i for i in issues if i.jiddiylik == "xato"]


class RuleChecksTest(unittest.TestCase):
    def test_sample_content_is_clean(self):
        self.assertEqual(rule_checks(make_lesson(), make_caption()), [])

    def test_cyrillic_in_word_is_error(self):
        lesson = make_lesson()
        lesson.sozlar[0].tarjima = "официант"
        self.assertTrue(any("Kirill" in i.muammo for i in errors(rule_checks(lesson, make_caption()))))

    def test_cyrillic_in_caption_is_error(self):
        issues = rule_checks(make_lesson(), make_caption(matn="Бугун"))
        self.assertTrue(any(i.joy == "caption" for i in errors(issues)))

    def test_syllable_count_mismatch_is_error(self):
        lesson = make_lesson()
        lesson.sozlar[0].bogin_pinyin = ["fúwù", "yuán"]   # 3 ieroglif, 2 bo'g'in
        self.assertTrue(any("bogin_pinyin" in i.joy for i in errors(rule_checks(lesson, make_caption()))))

    def test_bad_quiz_answer_is_error(self):
        lesson = make_lesson()
        lesson.test.togri_javob = 5
        self.assertTrue(any(i.joy == "test" for i in errors(rule_checks(lesson, make_caption()))))

    def test_too_long_caption_is_error(self):
        issues = rule_checks(make_lesson(), make_caption(matn="a" * 3000))
        self.assertTrue(any("uzun" in i.muammo for i in errors(issues)))

    def test_missing_hashtag_is_only_warning(self):
        issues = rule_checks(make_lesson(), make_caption(tags=TAGS[:2]))
        self.assertTrue(issues)
        self.assertEqual(errors(issues), [])


if __name__ == "__main__":
    unittest.main()
