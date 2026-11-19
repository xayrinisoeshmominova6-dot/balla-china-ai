"""Instagram Graph API bilan bog'lanish.

Hozircha bu modul FAQAT O'QIYDI: akkaunt ma'lumotlarini oladi va ulanish
ishlayotganini tekshiradi. Post joylash funksiyasi 5- va 7-bosqichlarda
qo'shiladi va faqat TASDIQLANGAN kontent uchun ishlaydi.

Xavfsizlik: token hech qachon xato xabarlariga yoki logga yozilmaydi.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from balla.config import Settings, get_settings

PROFILE_FIELDS = "id,username,name,followers_count,follows_count,media_count"


class InstagramError(RuntimeError):
    pass


class InstagramNotConfiguredError(InstagramError):
    pass


@dataclass
class InstagramProfile:
    id: str
    username: str
    name: str | None
    followers_count: int | None
    follows_count: int | None
    media_count: int | None


# (url, headers) -> (status_code, body_text). Testlarda soxta funksiya bilan almashtiriladi.
HttpGet = Callable[[str, dict[str, str]], tuple[int, str]]


def _urllib_get(url: str, headers: dict[str, str]) -> tuple[int, str]:
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        # e.reason ichida token yo'q (token URL'da emas, sarlavhada yuboriladi)
        raise InstagramError(f"Instagram serveriga ulanib bo'lmadi: {e.reason}") from None


class InstagramClient:
    def __init__(self, settings: Settings | None = None, http_get: HttpGet | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.instagram_configured:
            raise InstagramNotConfiguredError(
                "Instagram sozlanmagan. `.env` faylida INSTAGRAM_ACCESS_TOKEN va "
                "INSTAGRAM_BUSINESS_ACCOUNT_ID ni to'ldiring (docs/instagram_ulash.md)."
            )
        self._token = self.settings.instagram_access_token.get_secret_value()  # type: ignore[union-attr]
        self._account_id = self.settings.instagram_business_account_id
        self._http_get = http_get or _urllib_get

    @property
    def base_url(self) -> str:
        s = self.settings
        return f"https://{s.instagram_api_host}/{s.instagram_api_version}"

    def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        query = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.base_url}/{path}{query}"
        # Token URL'da emas, Authorization sarlavhasida yuboriladi — loglarga tushmaydi.
        status, body = self._http_get(url, {"Authorization": f"Bearer {self._token}"})
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            raise InstagramError(f"Instagram tushunarsiz javob qaytardi (HTTP {status}).") from None
        if status >= 400 or "error" in data:
            raise InstagramError(self._explain_error(status, data.get("error") or {}))
        return data

    def _explain_error(self, status: int, err: dict[str, Any]) -> str:
        code = err.get("code")
        msg = str(err.get("message", "")).replace(self._token, "***")
        if code == 190:
            hint = "Token noto'g'ri yoki muddati o'tgan. Yangi token oling."
        elif code in (10, 200) or status == 403:
            hint = "Ruxsat yetarli emas. Token olishda kerakli ruxsatlar (permissions) belgilanganini tekshiring."
        elif code == 100:
            hint = "Akkaunt ID noto'g'ri yoki API_HOST token turiga mos emas."
        elif code in (4, 17, 32, 613):
            hint = "So'rovlar limiti oshib ketdi. Birozdan keyin qayta urining."
        else:
            hint = "Noma'lum xato."
        return f"{hint} (HTTP {status}, kod {code}: {msg})"

    def get_profile(self) -> InstagramProfile:
        d = self._get(str(self._account_id), {"fields": PROFILE_FIELDS})
        return InstagramProfile(
            id=str(d.get("id", self._account_id)),
            username=d.get("username", "?"),
            name=d.get("name"),
            followers_count=d.get("followers_count"),
            follows_count=d.get("follows_count"),
            media_count=d.get("media_count"),
        )
