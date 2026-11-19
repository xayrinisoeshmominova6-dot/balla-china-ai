"""Promptlar (AI uchun ko'rsatmalar) `.md` fayllarda saqlanadi.

Ularni dasturlashni bilmasdan ham tahrirlash mumkin.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


@lru_cache
def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt topilmadi: {path.name}")
    return path.read_text(encoding="utf-8").strip()
