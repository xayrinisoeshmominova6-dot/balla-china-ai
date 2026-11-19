"""HSK so'zlar ro'yxatini ochiq manbadan import qilish.

Manba: https://github.com/drkameleon/complete-hsk-vocabulary (MIT litsenziyasi)
  - HSK 3.0 ro'yxatlari: https://github.com/elkmovie/hsk30
  - Inglizcha ta'riflar: CC-CEDICT (CC BY-SA 4.0)

Ishlatish (yuklab olingan fayllar papkasi bilan):
    python scripts/import_hsk.py YUKLANGAN_PAPKA

Natija: data/hsk/hsk3_level{1,2,3}.json — ixcham shakl.
Diqqat: bu ro'yxat ochiq manbadan olingan va hali o'qituvchi tomonidan
tekshirilmagan (data/hsk/SOURCE.md ga qarang).
"""

from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "hsk"


def convert(entry: dict, level: int) -> dict:
    forms = entry.get("forms") or []
    pinyins: list[str] = []
    meanings: list[str] = []
    for f in forms:
        p = unicodedata.normalize("NFC", f["transcriptions"]["pinyin"])
        if p not in pinyins:
            pinyins.append(p)
        meanings.extend(m for m in f.get("meanings", []) if m not in meanings)
    return {
        "hanzi": unicodedata.normalize("NFC", entry["simplified"]),
        "pinyin": pinyins,
        "meanings_en": meanings[:4],
        "pos": entry.get("pos", []),
        "level": level,
    }


def main(src: Path) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for level in (1, 2, 3):
        raw = json.loads((src / f"new_{level}.json").read_text(encoding="utf-8"))
        items = [convert(e, level) for e in raw]
        out = OUT_DIR / f"hsk3_level{level}.json"
        out.write_text(json.dumps(items, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"HSK {level}: {len(items)} so'z -> {out.name}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
