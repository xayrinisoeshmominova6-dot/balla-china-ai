"""Barcha agentlar uchun umumiy asos.

Har bir agent:
  * o'z prompt faylini (`prompt_name`) va umumiy qoidalarni (`shared_rules`) birlashtiradi;
  * Claude'ga `ClaudeClient` orqali murojaat qiladi.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from balla.llm.claude_client import ClaudeClient
from balla.prompts import load_prompt

T = TypeVar("T", bound=BaseModel)


class BaseAgent:
    prompt_name: str = ""

    def __init__(self, llm: ClaudeClient) -> None:
        self.llm = llm

    @property
    def system_prompt(self) -> str:
        parts = [load_prompt("shared_rules")]
        if self.prompt_name:
            parts.append(load_prompt(self.prompt_name))
        return "\n\n".join(parts)

    def ask(self, prompt: str, output_model: type[T], **kwargs) -> T:
        return self.llm.generate_structured(
            system=self.system_prompt, prompt=prompt, output_model=output_model, **kwargs
        )
