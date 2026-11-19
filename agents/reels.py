"""4. Instagram Reels Agent — Reels uchun ssenariy yozadi (videoni siz suratga olasiz)."""
from typing import List

from pydantic import BaseModel

from agents.base import ask_claude, load_prompt
from agents.education import LessonContent


class Scene(BaseModel):
    vaqt: str             # masalan "0–3 s"
    kadr: str             # kamerada nima ko'rinadi
    gapiriladi: str       # ovozda nima aytiladi (xitoycha bo'lsa pinyin bilan)
    ekrandagi_matn: str   # ekranga chiqadigan yozuv


class ReelsScript(BaseModel):
    hook: str             # birinchi 3 soniyadagi gap
    davomiylik_soniya: int
    sahnalar: List[Scene]
    musiqa_tavsiya: str
    suratga_olish_maslahati: str

    def as_text(self) -> str:
        lines = [f"🎬 Hook: {self.hook}", f"⏱ Davomiyligi: ~{self.davomiylik_soniya} s", ""]
        for s in self.sahnalar:
            lines += [f"[{s.vaqt}] 🎥 {s.kadr}",
                      f"   🗣 {s.gapiriladi}",
                      f"   🔤 Ekranda: {s.ekrandagi_matn}", ""]
        lines += [f"🎵 Musiqa: {self.musiqa_tavsiya}",
                  f"💡 Maslahat: {self.suratga_olish_maslahati}"]
        return "\n".join(lines)


def write_script(lesson: LessonContent, feedback: str = "") -> ReelsScript:
    message = f"Dars mazmuni (JSON):\n{lesson.model_dump_json(indent=2)}\n"
    if feedback:
        message += f"\nTuzatish kerak bo'lgan narsalar:\n{feedback}\n"
    return ask_claude(load_prompt("reels"), message, ReelsScript)
