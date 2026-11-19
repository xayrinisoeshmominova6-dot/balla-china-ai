"""9. Instagram Publishing — tasdiqlangan carousel'ni Instagram Graph API orqali joylaydi.

XAVFSIZLIK QAVATLARI:
  1. Faqat bazada "approved" holatidagi qoralama joylanadi (storage/database.py).
  2. Joylashdan oldin akkaunt nomi tekshiriladi: brand.yaml dagi instagram_handle
     bilan mos kelmasa — hech narsa joylanmaydi.
  3. DRY_RUN=true bo'lsa — Instagram'ga ham, rasm hostingiga ham hech narsa yuborilmaydi.
  4. Kalitlar logga va xato xabarlariga chiqmaydi.

Instagram Graph API rasmni faqat ochiq internet havolasi (URL) orqali va faqat JPEG
formatida qabul qiladi. Shuning uchun slaydlar avval JPEG'ga aylantirilib, imgbb.com'ga
vaqtincha (24 soat) yuklanadi.

Joylash bosqichlari (Instagram talabi):
  har bir rasm → "carousel item" konteyner → CAROUSEL konteyner → tayyor bo'lishini kutish
  → media_publish → post havolasi (permalink)
"""
import base64
import io
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

import requests
from PIL import Image

from config import settings

TIMEOUT = 60
IMGBB_URL = "https://api.imgbb.com/1/upload"
IMGBB_EXPIRATION = 86400          # rasm 24 soatdan keyin hostingdan o'chadi
MAX_CAPTION = 2200
MAX_ITEMS = 10


class PublishError(Exception):
    """Joylashdagi xato (o'zbekcha tushuntirish bilan, kalitlarsiz)."""


@dataclass
class PublishResult:
    dry_run: bool
    media_id: Optional[str] = None
    permalink: Optional[str] = None
    message: str = ""


def _hide_secrets(text: str) -> str:
    for secret in (settings.INSTAGRAM_ACCESS_TOKEN, settings.IMGBB_API_KEY):
        if secret:
            text = text.replace(secret, "***")
    return text


def expected_username() -> str:
    handle = settings.load_brand()["brand"]["instagram_handle"]
    return handle.strip().lstrip("@").lower()


def to_jpeg(path: Path) -> bytes:
    """PNG → JPEG (Instagram faqat JPEG qabul qiladi)."""
    with Image.open(path) as im:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=95, optimize=True)
        return buf.getvalue()


class InstagramClient:
    def __init__(self, session: Optional[requests.Session] = None,
                 sleep: Callable[[float], None] = time.sleep):
        if not settings.INSTAGRAM_ACCESS_TOKEN or not settings.INSTAGRAM_BUSINESS_ACCOUNT_ID:
            raise PublishError("INSTAGRAM_ACCESS_TOKEN yoki INSTAGRAM_BUSINESS_ACCOUNT_ID .env faylida yo'q.")
        if not settings.IMGBB_API_KEY:
            raise PublishError("IMGBB_API_KEY .env faylida yo'q (rasmlarni vaqtincha joylash uchun kerak).")
        self.http = session or requests.Session()
        self.sleep = sleep
        self.base = f"https://graph.facebook.com/{settings.INSTAGRAM_GRAPH_VERSION}"
        self.user_id = settings.INSTAGRAM_BUSINESS_ACCOUNT_ID

    # --- past darajadagi so'rovlar ---
    def _call(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        payload = dict(data or {}, access_token=settings.INSTAGRAM_ACCESS_TOKEN)
        try:
            if method == "GET":
                r = self.http.get(f"{self.base}/{path}", params=payload, timeout=TIMEOUT)
            else:
                r = self.http.post(f"{self.base}/{path}", data=payload, timeout=TIMEOUT)
        except requests.RequestException as e:
            raise PublishError(_hide_secrets(f"Instagram'ga ulanib bo'lmadi: {e}"))
        try:
            body = r.json()
        except ValueError:
            body = {}
        if r.status_code >= 400 or "error" in body:
            err = body.get("error", {})
            msg = err.get("error_user_msg") or err.get("message") or f"HTTP {r.status_code}"
            raise PublishError(_hide_secrets(f"Instagram xatosi: {msg}"))
        return body

    # --- qadamlar ---
    def check_account(self) -> str:
        """Token qaysi akkauntga tegishli ekanini tekshiradi."""
        username = (self._call("GET", self.user_id, {"fields": "username"}).get("username") or "").lower()
        if username != expected_username():
            raise PublishError(
                f"Akkaunt mos emas: token @{username} ga tegishli, lekin brand.yaml da "
                f"@{expected_username()} yozilgan. Hech narsa joylanmadi.")
        return username

    def upload_image(self, path: Path) -> str:
        data = base64.b64encode(to_jpeg(path)).decode()
        try:
            r = self.http.post(IMGBB_URL, params={"key": settings.IMGBB_API_KEY, "expiration": IMGBB_EXPIRATION},
                               data={"image": data, "name": path.stem}, timeout=TIMEOUT)
            body = r.json()
        except (requests.RequestException, ValueError) as e:
            raise PublishError(_hide_secrets(f"Rasmni yuklab bo'lmadi: {e}"))
        url = (body.get("data") or {}).get("url")
        if r.status_code >= 400 or not url:
            raise PublishError("Rasm hostingi (imgbb) xato qaytardi. IMGBB_API_KEY ni tekshiring.")
        return url

    def wait_ready(self, container_id: str, attempts: int = 30, delay: float = 3) -> None:
        for _ in range(attempts):
            status = self._call("GET", container_id, {"fields": "status_code"}).get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise PublishError(f"Instagram rasmlarni qayta ishlay olmadi (holat: {status}).")
            self.sleep(delay)
        raise PublishError("Instagram rasmlarni juda uzoq qayta ishlayapti. Keyinroq urinib ko'ring.")

    def publish_carousel(self, image_paths: List[Path], caption: str, log=print) -> PublishResult:
        log("🔐 Akkaunt tekshirilmoqda...")
        username = self.check_account()
        log("☁️ Rasmlar yuklanmoqda...")
        urls = [self.upload_image(p) for p in image_paths]
        log("📦 Instagram konteynerlari yaratilmoqda...")
        children = [self._call("POST", f"{self.user_id}/media",
                               {"image_url": u, "is_carousel_item": "true"})["id"] for u in urls]
        container = self._call("POST", f"{self.user_id}/media",
                               {"media_type": "CAROUSEL", "children": ",".join(children),
                                "caption": caption})["id"]
        self.wait_ready(container)
        log("🚀 Joylanmoqda...")
        media_id = self._call("POST", f"{self.user_id}/media_publish", {"creation_id": container})["id"]
        permalink = self._call("GET", media_id, {"fields": "permalink"}).get("permalink")
        return PublishResult(False, media_id, permalink, f"@{username} ga joylandi")


def validate(image_paths: List[Path], caption: str) -> None:
    if not 2 <= len(image_paths) <= MAX_ITEMS:
        raise PublishError(f"Carousel 2–{MAX_ITEMS} ta rasmdan iborat bo'lishi kerak ({len(image_paths)} ta bor).")
    missing = [p.name for p in image_paths if not p.exists()]
    if missing:
        raise PublishError(f"Rasm fayllari topilmadi: {', '.join(missing)}")
    if len(caption) > MAX_CAPTION:
        raise PublishError(f"Caption {MAX_CAPTION} belgidan uzun.")


def publish_carousel(image_paths: List[Path], caption: str, log=print,
                     client_factory=InstagramClient) -> PublishResult:
    """Asosiy funksiya. DRY_RUN yoqilgan bo'lsa — faqat tekshiradi, hech narsa yubormaydi."""
    validate(image_paths, caption)
    if settings.DRY_RUN:
        return PublishResult(True, message=(
            f"🧪 DRY_RUN rejimi: {len(image_paths)} ta rasm va caption tekshirildi, "
            "lekin Instagram'ga HECH NARSA yuborilmadi. Haqiqiy joylash uchun .env da DRY_RUN=false qiling."))
    return client_factory().publish_carousel(image_paths, caption, log)
