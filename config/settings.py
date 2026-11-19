"""Sozlamalarni .env va brand.yaml fayllaridan o'qiydi.

Kalitlar faqat shu yerda o'qiladi va hech qachon ekranga chiqarilmaydi.
"""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"
BRAND_FILE = ROOT_DIR / "config" / "brand.yaml"

load_dotenv(ENV_FILE)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_CHAT_ID = os.getenv("TELEGRAM_ADMIN_CHAT_ID", "")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "")
INSTAGRAM_GRAPH_VERSION = os.getenv("INSTAGRAM_GRAPH_VERSION", "v21.0")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")

# Xavfsiz standart: agar aniq "false" yozilmagan bo'lsa, sinov rejimi yoqiq.
DRY_RUN = os.getenv("DRY_RUN", "true").strip().lower() != "false"


def load_brand() -> dict:
    """brand.yaml faylini o'qib, lug'at (dict) ko'rinishida qaytaradi."""
    with open(BRAND_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def key_status() -> dict:
    """Qaysi kalitlar to'ldirilganini ko'rsatadi (qiymatlarini EMAS)."""
    return {
        "ANTHROPIC_API_KEY": bool(ANTHROPIC_API_KEY),
        "TELEGRAM_BOT_TOKEN": bool(TELEGRAM_BOT_TOKEN),
        "TELEGRAM_ADMIN_CHAT_ID": bool(TELEGRAM_ADMIN_CHAT_ID),
        "INSTAGRAM_ACCESS_TOKEN": bool(INSTAGRAM_ACCESS_TOKEN),
        "INSTAGRAM_BUSINESS_ACCOUNT_ID": bool(INSTAGRAM_BUSINESS_ACCOUNT_ID),
        "IMGBB_API_KEY": bool(IMGBB_API_KEY),
    }
