"""2-bosqich testlari: o'qituvchi agenti va tekshiruv qavati (haqiqiy API chaqirilmaydi)."""

import pytest

from balla.agents.educator import EducatorAgent
from balla.agents.lesson_render import render_lesson
from balla.schemas import Confidence, ContentStatus, Lesson, PinyinCheck, VocabItem
from balla.schemas.lesson import ExampleSentence
from balla.storage.database import ContentStore
from balla.validation.hsk_list import HSKList, HSKWord
from balla.validation.pinyin_check import check_pinyin
from balla.workflow import NotVerifiedError, approve, save_lesson, teacher_verify


@pytest.fixture
def hsk():
    return HSKList([
        HSKWord("妈妈", ("mā ma",), ("mom",), ("n",), 1),
        HSKWord("爸爸", ("bà ba",), ("dad",), ("n",), 1),
        HSKWord("家", ("jiā",), ("home; family",), ("n",), 1),
        HSKWord("哥哥", ("gē ge",), ("older brother",), ("n",), 2),
    ])


class FakeLLM:
    def __init__(self, lesson):
        self.lesson = lesson
        self.calls = []

    def generate_structured(self, **kw):
        self.calls.append(kw)
        return self.lesson.model_copy(deep=True)


def _item(hanzi, pinyin, **kw):
    return VocabItem(hanzi=hanzi, pinyin=pinyin, uzbek="x", part_of_speech="ot", **kw)


# --- Pinyin tekshiruvi ---

def test_pinyin_check_against_list(hsk):
    assert check_pinyin("妈妈", "mā ma", hsk) == PinyinCheck.MATCH
    assert check_pinyin("妈妈", "māma", hsk) == PinyinCheck.MATCH      # bo'shliq ahamiyatsiz
    assert check_pinyin("妈妈", "mā mā", hsk) == PinyinCheck.TONE_DIFF
    assert check_pinyin("妈妈", "nǎi nai", hsk) == PinyinCheck.MISMATCH


def test_pinyin_check_with_pypinyin_for_words_outside_list():
    assert check_pinyin("你好", "nǐ hǎo") == PinyinCheck.MATCH
    assert check_pinyin("你好", "nǐ hāo") == PinyinCheck.TONE_DIFF
    assert check_pinyin("你好", "wǒ hǎo") == PinyinCheck.MISMATCH
    assert check_pinyin("hello", "hello") == PinyinCheck.NOT_CHECKED


# --- Agent ---

def test_prompt_contains_only_allowed_levels(hsk):
    agent = EducatorAgent(FakeLLM(None), hsk=hsk)
    prompt = agent.build_prompt("Oila", level=1, n_words=3)
    assert "妈妈" in prompt and "爸爸" in prompt
    assert "哥哥" not in prompt  # 2-daraja so'zi 1-daraja darsiga berilmaydi


def test_claude_output_is_corrected_and_flagged(hsk):
    claude_lesson = Lesson(title_uzbek="Oila", topic="Oila", level="?", vocabulary=[
        _item("妈妈", "mā mā", hsk_level=3),            # noto'g'ri ohang + noto'g'ri daraja
        _item("家", "jiā", examples=[ExampleSentence(hanzi="我家", pinyin="wǒ jiā", uzbek="uyim")]),
        _item("奶奶", "nǎi nai", hsk_level=1),           # ro'yxatda yo'q so'z
    ])
    lesson = EducatorAgent(FakeLLM(claude_lesson), hsk=hsk).create_lesson("Oila", 1, 3)
    mama, jia, nainai = lesson.vocabulary

    assert mama.pinyin == "mā ma" and mama.hsk_level == 1          # ro'yxatdan tuzatildi
    assert mama.pinyin_check == PinyinCheck.MATCH and "almashtirildi" in mama.notes
    assert jia.pinyin_check == PinyinCheck.MATCH and jia.notes is None
    assert nainai.confidence == Confidence.UNCERTAIN and nainai.hsk_level is None
    assert lesson.needs_attention == [nainai]
    assert not any(v.teacher_verified for v in lesson.vocabulary)


def test_claude_cannot_mark_words_as_teacher_verified(hsk):
    claude_lesson = Lesson(title_uzbek="t", topic="t", level="1",
                           vocabulary=[_item("家", "jiā", teacher_verified=True)])
    lesson = EducatorAgent(FakeLLM(claude_lesson), hsk=hsk).create_lesson("t", 1, 1)
    assert lesson.vocabulary[0].teacher_verified is False


def test_invalid_level_is_rejected(hsk):
    with pytest.raises(ValueError):
        EducatorAgent(FakeLLM(None), hsk=hsk).create_lesson("t", 6, 3)


# --- Tasdiqlash jarayoni ---

def test_lesson_cannot_be_approved_until_teacher_verifies_all_words(tmp_path, hsk):
    store = ContentStore(":memory:")
    lesson = Lesson(title_uzbek="t", topic="t", level="HSK 1",
                    vocabulary=[_item("家", "jiā"), _item("妈妈", "mā ma")])
    cid, path = save_lesson(store, lesson, out_dir=tmp_path)
    assert path.exists() and "家" in path.read_text(encoding="utf-8")

    store.set_status(cid, ContentStatus.IN_REVIEW, actor="bot")
    teacher_verify(store, cid, [1], actor="teacher")
    with pytest.raises(NotVerifiedError):
        approve(store, cid, actor="teacher")

    teacher_verify(store, cid, [2], actor="teacher")
    approve(store, cid, actor="teacher")
    assert store.get(cid)["status"] == "approved"

    with pytest.raises(ValueError):  # tasdiqlangan darsni jimgina o'zgartirib bo'lmaydi
        teacher_verify(store, cid, None, actor="teacher")


def test_render_shows_warnings(hsk):
    lesson = Lesson(title_uzbek="Sarlavha", topic="t", level="HSK 1", vocabulary=[
        _item("奶奶", "nǎi nai", confidence=Confidence.UNCERTAIN, pinyin_check=PinyinCheck.MISMATCH),
    ])
    text = render_lesson(lesson, 7)
    assert "#7" in text and "ISHONCH PAST" in text and "FARQ BOR" in text


def test_real_hsk_data_loads():
    h = HSKList.load()
    assert len(h.at_level(1)) > 400
    w = h.lookup("你")
    assert w is not None and w.level == 1 and w.pinyin == ("nǐ",)
