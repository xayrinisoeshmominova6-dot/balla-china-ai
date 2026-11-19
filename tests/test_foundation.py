"""1-bosqich testlari: haqiqiy API'ga murojaat qilmaydi (pul sarflanmaydi)."""

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from balla.config import Settings
from balla.llm.claude_client import ClaudeClient, ClaudeError, MissingAPIKeyError
from balla.schemas import (
    Confidence, ContentStatus, ContentType, InvalidTransitionError,
    Lesson, PinyinCheck, VocabItem,
)
from balla.storage.database import ContentStore


def _settings(**kw):
    return Settings(_env_file=None, **kw)


# --- Kalitlar xavfsizligi ---

def test_secret_is_hidden_when_printed():
    s = _settings(ANTHROPIC_API_KEY="sk-ant-very-secret")
    assert "very-secret" not in repr(s)
    assert "very-secret" not in str(s.anthropic_api_key)


def test_missing_key_gives_clear_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError):
        ClaudeClient(settings=_settings())


# --- Tasdiqlash qoidalari ---

@pytest.fixture
def store():
    s = ContentStore(":memory:")
    yield s
    s.close()


def test_draft_cannot_be_published_directly(store):
    cid = store.add(ContentType.LESSON, "Salomlashish", {})
    with pytest.raises(InvalidTransitionError):
        store.set_status(cid, ContentStatus.PUBLISHED, actor="bot")


def test_in_review_cannot_be_published_without_approval(store):
    cid = store.add(ContentType.LESSON, "Salomlashish", {})
    store.set_status(cid, ContentStatus.IN_REVIEW, actor="bot")
    with pytest.raises(InvalidTransitionError):
        store.set_status(cid, ContentStatus.PUBLISHED, actor="bot")


def test_full_approval_flow_is_logged(store):
    cid = store.add(ContentType.LESSON, "Salomlashish", {"a": "你好"})
    store.set_status(cid, ContentStatus.IN_REVIEW, actor="bot")
    store.set_status(cid, ContentStatus.APPROVED, actor="human:admin")
    store.set_status(cid, ContentStatus.PUBLISHED, actor="publisher")
    assert store.get(cid)["status"] == "published"
    assert store.get(cid)["payload"] == {"a": "你好"}  # xitoycha belgilar saqlanadi
    assert [h["to_status"] for h in store.history(cid)] == [
        "draft", "in_review", "approved", "published"]


# --- Dars sxemasi ---

def test_lesson_flags_items_needing_attention():
    ok = VocabItem(hanzi="A", pinyin="a", uzbek="a", part_of_speech="ot",
                   pinyin_check=PinyinCheck.MATCH)
    unsure = VocabItem(hanzi="B", pinyin="b", uzbek="b", part_of_speech="ot",
                       confidence=Confidence.UNCERTAIN)
    lesson = Lesson(title_uzbek="t", topic="t", level="HSK 1", vocabulary=[ok, unsure])
    assert lesson.needs_attention == [unsure]
    assert not lesson.fully_verified  # hech kim tasdiqlamagan


# --- Claude javoblarini qayta ishlash ---

def _fake_client(response):
    beta = SimpleNamespace(messages=SimpleNamespace(parse=lambda **kw: response))
    return SimpleNamespace(beta=beta)


def test_refusal_is_reported():
    c = ClaudeClient(settings=_settings(),
                     client=_fake_client(SimpleNamespace(stop_reason="refusal", parsed_output=None)))
    with pytest.raises(ClaudeError):
        c.generate_structured(system="s", prompt="p", output_model=Lesson)


def test_truncated_output_is_reported():
    c = ClaudeClient(settings=_settings(),
                     client=_fake_client(SimpleNamespace(stop_reason="max_tokens", parsed_output=None)))
    with pytest.raises(ClaudeError):
        c.generate_structured(system="s", prompt="p", output_model=Lesson)


def test_parsed_output_is_returned_and_request_is_configured():
    lesson = Lesson(title_uzbek="t", topic="t", level="HSK 1", vocabulary=[])
    captured = {}

    def parse(**kw):
        captured.update(kw)
        return SimpleNamespace(stop_reason="end_turn", parsed_output=lesson)

    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse)))
    c = ClaudeClient(settings=_settings(), client=client)
    assert c.generate_structured(system="s", prompt="p", output_model=Lesson) is lesson
    assert captured["model"] == "claude-opus-5-5"
    assert captured["output_format"] is Lesson
    assert captured["fallbacks"] == "default"
