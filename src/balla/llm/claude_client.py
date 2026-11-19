"""Claude API bilan yagona bog'lanish nuqtasi.

Barcha agentlar Claude'ga faqat shu fayl orqali murojaat qiladi. Afzalliklari:
  * Model, fikrlash chuqurligi va xatolarni qayta ishlash bir joyda boshqariladi.
  * Testlarda haqiqiy API o'rniga soxta (fake) mijoz qo'yish oson.

Asosiy funksiya `generate_structured`: Claude javobni Pydantic sxemasi
shaklida qaytaradi, SDK esa uni avtomatik tekshiradi. Kerakli maydon
tushib qolsa, xato beriladi va noto'g'ri ma'lumot jim o'tib ketmaydi.
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

import anthropic
from pydantic import BaseModel

from balla.config import Settings, get_settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

# Server tomonidagi zaxira: agar asosiy model so'rovni xavfsizlik sababli
# rad etsa, API uni avtomatik ravishda mos zaxira modelda qayta bajaradi.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class ClaudeError(RuntimeError):
    """Claude'dan foydalanib bo'lmaydigan javob kelganda."""


class MissingAPIKeyError(ClaudeError):
    pass


class ClaudeClient:
    def __init__(
        self,
        settings: Settings | None = None,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        if client is not None:
            self._client = client
        else:
            if not self.settings.has_claude_key:
                raise MissingAPIKeyError(
                    "ANTHROPIC_API_KEY topilmadi. `.env` faylini yarating "
                    "(`cp .env.example .env`) va kalitni o'sha yerga yozing."
                )
            self._client = anthropic.Anthropic(
                api_key=self.settings.anthropic_api_key.get_secret_value(),  # type: ignore[union-attr]
                max_retries=3,
            )

    def generate_structured(
        self,
        *,
        system: str,
        prompt: str,
        output_model: type[T],
        max_tokens: int = 16000,
        effort: str | None = None,
    ) -> T:
        """Claude'dan `output_model` shaklidagi tekshirilgan javob oladi."""
        try:
            response = self._client.beta.messages.parse(
                model=self.settings.claude_model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_format=output_model,
                output_config={"effort": effort or self.settings.claude_effort},
                betas=[FALLBACK_BETA],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as e:
            raise ClaudeError("API kaliti noto'g'ri yoki muddati o'tgan.") from e
        except anthropic.RateLimitError as e:
            raise ClaudeError("So'rovlar limiti oshib ketdi. Birozdan keyin qayta urining.") from e
        except anthropic.APIStatusError as e:
            raise ClaudeError(f"Claude API xatosi ({e.status_code}).") from e
        except anthropic.APIConnectionError as e:
            raise ClaudeError("Claude API bilan aloqa yo'q. Internetni tekshiring.") from e

        return self._extract(response, output_model)

    @staticmethod
    def _extract(response: Any, output_model: type[T]) -> T:
        if response.stop_reason == "refusal":
            raise ClaudeError("Claude bu so'rovni bajarishdan bosh tortdi.")
        if response.stop_reason == "max_tokens":
            raise ClaudeError("Javob juda uzun bo'lib, kesilib qoldi. `max_tokens`ni oshiring.")
        parsed = getattr(response, "parsed_output", None)
        if parsed is None:
            raise ClaudeError(f"Claude javobi {output_model.__name__} shakliga mos kelmadi.")
        return parsed
