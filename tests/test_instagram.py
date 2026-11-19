"""Instagram moduli testlari — haqiqiy Instagram'ga murojaat qilmaydi."""

import json

import pytest

from balla.config import Settings
from balla.integrations.instagram import (
    InstagramClient, InstagramError, InstagramNotConfiguredError,
)

TOKEN = "IGAA-super-secret-token"


def _settings(**kw):
    base = {"INSTAGRAM_ACCESS_TOKEN": TOKEN, "INSTAGRAM_BUSINESS_ACCOUNT_ID": "1784"}
    base.update(kw)
    return Settings(_env_file=None, **base)


def test_not_configured(monkeypatch):
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    with pytest.raises(InstagramNotConfiguredError):
        InstagramClient(settings=Settings(_env_file=None))


def test_profile_and_token_stays_out_of_url():
    seen = {}

    def fake_get(url, headers):
        seen["url"], seen["headers"] = url, headers
        return 200, json.dumps({"id": "1784", "username": "ballachina",
                                "followers_count": 1200, "media_count": 85})

    p = InstagramClient(settings=_settings(), http_get=fake_get).get_profile()
    assert p.username == "ballachina" and p.followers_count == 1200
    assert seen["url"].startswith("https://graph.instagram.com/v23.0/1784?fields=")
    assert TOKEN not in seen["url"]
    assert seen["headers"]["Authorization"] == f"Bearer {TOKEN}"


def test_facebook_host_can_be_selected():
    seen = {}

    def fake_get(url, headers):
        seen["url"] = url
        return 200, json.dumps({"id": "1784", "username": "x"})

    InstagramClient(settings=_settings(INSTAGRAM_API_HOST="graph.facebook.com"),
                    http_get=fake_get).get_profile()
    assert seen["url"].startswith("https://graph.facebook.com/")


def test_expired_token_error_is_explained_without_leaking_token():
    def fake_get(url, headers):
        return 400, json.dumps({"error": {"code": 190, "message": f"bad token {TOKEN}"}})

    with pytest.raises(InstagramError) as exc:
        InstagramClient(settings=_settings(), http_get=fake_get).get_profile()
    assert "muddati o'tgan" in str(exc.value)
    assert TOKEN not in str(exc.value)
