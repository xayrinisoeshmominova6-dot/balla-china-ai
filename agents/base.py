"""Barcha agentlar uchun umumiy Claude API ulanishi.

Har bir agent shu yerdagi `ask_claude()` funksiyasini chaqiradi.
Javob oldindan belgilangan shaklda (Pydantic model) qaytadi, shuning uchun
matnni qo'lda "bo'laklash" kerak emas.
"""
from pathlib import Path
from typing import Type, TypeVar

import anthropic
from pydantic import BaseModel

from config import settings

PROMPTS_DIR = settings.ROOT_DIR / "prompts"
T = TypeVar("T", bound=BaseModel)

_client = None


class AgentError(Exception):
    """Agent ishida xato bo'lganda chiqadi (o'zbekcha tushuntirish bilan)."""


def _get_client() -> anthropic.Anthropic:
    global _client
    if not settings.ANTHROPIC_API_KEY:
        raise AgentError(
            "ANTHROPIC_API_KEY topilmadi. .env fayliga kalitni yozing (README'ga qarang)."
        )
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def load_prompt(name: str) -> str:
    """prompts/<name>.md faylini o'qiydi va brend ma'lumotlarini qo'shadi."""
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    brand = settings.load_brand()
    brand_block = (
        f"\n\n## Brend ma'lumotlari\n"
        f"- Brend: {brand['brand']['name']}\n"
        f"- Auditoriya: {brand['audience']['description']}\n"
        f"- Yozuv: faqat o'zbek LOTIN yozuvi (kirill harflari taqiqlangan)\n"
        f"- Ohang: {brand['tone']['style']}\n"
    )
    return text + brand_block


def ask_claude(system_prompt: str, user_message: str, output_model: Type[T]) -> T:
    """Claude'ga savol yuboradi va javobni `output_model` shaklida qaytaradi."""
    client = _get_client()
    try:
        response = client.beta.messages.parse(
            model=settings.CLAUDE_MODEL,
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            output_format=output_model,
            output_config={"effort": "medium"},
            # Agar model so'rovni rad etsa, server avtomatik zaxira modelga o'tadi
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError:
        raise AgentError("API kaliti noto'g'ri. .env faylidagi ANTHROPIC_API_KEY ni tekshiring.")
    except anthropic.RateLimitError:
        raise AgentError("So'rovlar chegarasiga yetildi. Bir daqiqadan so'ng qayta urinib ko'ring.")
    except anthropic.APIConnectionError:
        raise AgentError("Internetga ulanib bo'lmadi. Aloqani tekshiring.")
    except anthropic.APIStatusError as e:
        raise AgentError(f"Claude API xatosi ({e.status_code}): {e.message}")

    if response.stop_reason == "refusal":
        raise AgentError("Claude bu so'rovni bajarishdan bosh tortdi. Mavzuni o'zgartirib ko'ring.")
    if response.stop_reason == "max_tokens":
        raise AgentError("Javob juda uzun bo'lib ketdi va kesildi. Mavzuni toraytiring.")
    if response.parsed_output is None:
        raise AgentError("Claude javobini tushunib bo'lmadi. Qayta urinib ko'ring.")
    return response.parsed_output
