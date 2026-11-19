"""SQLite baza — qoralamalar va ularning holati (status).

Holatlar va ruxsat etilgan o'tishlar:

  qc_passed / qc_failed ──► awaiting_approval ──► approved ──► publishing ──► published
                                                                 │
                                                  xato bo'lsa ◄──┘ (approved ga qaytadi)
                                     │
                                     ├──► rejected
                                     └──► revised   (tahrir so'raldi, yangi qoralama yaratildi)

Ruxsat etilmagan o'tish xato beradi. Masalan, tasdiqlanmagan qoralamani
"published" qilib bo'lmaydi — bu xavfsizlikning asosiy qavati.
"""
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import settings

DB_PATH = settings.ROOT_DIR / "data" / "balla.db"

TRANSITIONS = {
    "qc_passed": {"awaiting_approval", "rejected"},
    "qc_failed": {"awaiting_approval", "rejected"},
    "awaiting_approval": {"approved", "rejected", "revised"},
    "approved": {"publishing"},
    "publishing": {"published", "approved"},
    "rejected": set(),
    "revised": set(),
    "published": set(),
}

STATUS_LABELS = {
    "qc_passed": "🟢 QC o'tdi",
    "qc_failed": "🟠 QC xatolari bor",
    "awaiting_approval": "⏳ Tasdiq kutilmoqda",
    "approved": "✅ Tasdiqlangan",
    "publishing": "📤 Joylanmoqda",
    "rejected": "❌ Rad etilgan",
    "revised": "✏️ Qayta ishlangan",
    "published": "🚀 Joylangan",
}


class StatusError(Exception):
    """Ruxsat etilmagan holat o'zgarishi."""


@dataclass
class DraftRecord:
    id: int
    topic: str
    hsk_level: int
    format: str
    status: str
    data: dict
    created_at: str
    updated_at: str


@contextmanager
def _connect(db_path: Optional[Path] = None):
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: Optional[Path] = None) -> None:
    with _connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                hsk_level INTEGER NOT NULL,
                format TEXT NOT NULL,
                status TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _row(r: sqlite3.Row) -> DraftRecord:
    return DraftRecord(r["id"], r["topic"], r["hsk_level"], r["format"], r["status"],
                       json.loads(r["data"]), r["created_at"], r["updated_at"])


def save_draft(topic: str, hsk_level: int, fmt: str, status: str, data: dict,
               db_path: Optional[Path] = None) -> int:
    if status not in ("qc_passed", "qc_failed"):
        raise StatusError(f"Yangi qoralama faqat qc_passed/qc_failed bo'lishi mumkin, {status} emas")
    init_db(db_path)
    with _connect(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO drafts (topic, hsk_level, format, status, data, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (topic, hsk_level, fmt, status, json.dumps(data, ensure_ascii=False), _now(), _now()),
        )
        return cur.lastrowid


def update_data(draft_id: int, data: dict, db_path: Optional[Path] = None) -> None:
    with _connect(db_path) as conn:
        conn.execute("UPDATE drafts SET data = ?, updated_at = ? WHERE id = ?",
                     (json.dumps(data, ensure_ascii=False), _now(), draft_id))


def get_draft(draft_id: int, db_path: Optional[Path] = None) -> Optional[DraftRecord]:
    init_db(db_path)
    with _connect(db_path) as conn:
        r = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        return _row(r) if r else None


def list_drafts(limit: int = 10, db_path: Optional[Path] = None) -> List[DraftRecord]:
    init_db(db_path)
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM drafts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [_row(r) for r in rows]


def set_status(draft_id: int, new_status: str, db_path: Optional[Path] = None) -> None:
    """Holatni o'zgartiradi — faqat TRANSITIONS ruxsat bergan bo'lsa."""
    draft = get_draft(draft_id, db_path)
    if draft is None:
        raise StatusError(f"#{draft_id} qoralama topilmadi")
    if new_status not in TRANSITIONS.get(draft.status, set()):
        raise StatusError(
            f"#{draft_id}: '{draft.status}' holatidan '{new_status}' holatiga o'tish mumkin emas"
        )
    with _connect(db_path) as conn:
        # WHERE status = ? — bir vaqtda ikki marta bosilsa ham faqat bittasi o'tadi
        cur = conn.execute("UPDATE drafts SET status = ?, updated_at = ? WHERE id = ? AND status = ?",
                           (new_status, _now(), draft_id, draft.status))
        if cur.rowcount != 1:
            raise StatusError(f"#{draft_id} holati boshqa joyda o'zgartirildi, qayta urinib ko'ring")
