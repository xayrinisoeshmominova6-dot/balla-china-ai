"""SQLite ma'lumotlar bazasi.

SQLite — bitta fayldan iborat ma'lumotlar bazasi, alohida o'rnatish shart emas.
Bu yerda yaratilgan barcha kontent va uning holati (qoralama, tasdiqlangan...)
saqlanadi.

Holat faqat `set_status` orqali o'zgartiriladi va u tasdiqlash
qoidalarini tekshiradi.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from balla.schemas.content import ContentStatus, ContentType, check_transition

SCHEMA = """
CREATE TABLE IF NOT EXISTS content (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'draft',
    payload     TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS status_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id  INTEGER NOT NULL REFERENCES content(id),
    from_status TEXT,
    to_status   TEXT NOT NULL,
    actor       TEXT NOT NULL,
    note        TEXT,
    at          TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ContentStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def add(self, type_: ContentType, title: str, payload: dict[str, Any]) -> int:
        now = _now()
        cur = self.conn.execute(
            "INSERT INTO content (type, title, status, payload, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (type_.value, title, ContentStatus.DRAFT.value,
             json.dumps(payload, ensure_ascii=False), now, now),
        )
        content_id = int(cur.lastrowid)
        self._log(content_id, None, ContentStatus.DRAFT, actor="system", note="yaratildi")
        self.conn.commit()
        return content_id

    def get(self, content_id: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM content WHERE id = ?", (content_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item

    def list(self, status: ContentStatus | None = None) -> list[dict[str, Any]]:
        if status:
            rows = self.conn.execute(
                "SELECT id, type, title, status, updated_at FROM content "
                "WHERE status = ? ORDER BY id", (status.value,))
        else:
            rows = self.conn.execute(
                "SELECT id, type, title, status, updated_at FROM content ORDER BY id")
        return [dict(r) for r in rows]

    def set_status(
        self, content_id: int, new: ContentStatus, *, actor: str, note: str | None = None
    ) -> None:
        item = self.get(content_id)
        if item is None:
            raise KeyError(f"{content_id} raqamli kontent topilmadi.")
        current = ContentStatus(item["status"])
        check_transition(current, new)
        self.conn.execute(
            "UPDATE content SET status = ?, updated_at = ? WHERE id = ?",
            (new.value, _now(), content_id),
        )
        self._log(content_id, current, new, actor=actor, note=note)
        self.conn.commit()

    def update_payload(
        self, content_id: int, payload: dict[str, Any], *, actor: str, note: str | None = None
    ) -> None:
        """Mazmunni yangilaydi. Tasdiqlangan yoki joylangan kontentni o'zgartirib bo'lmaydi."""
        item = self.get(content_id)
        if item is None:
            raise KeyError(f"{content_id} raqamli kontent topilmadi.")
        current = ContentStatus(item["status"])
        if current in (ContentStatus.APPROVED, ContentStatus.PUBLISHED):
            raise ValueError(
                f"'{current.value}' holatidagi kontentni o'zgartirib bo'lmaydi. "
                "Avval uni qayta tekshiruvga qaytaring."
            )
        self.conn.execute(
            "UPDATE content SET payload = ?, updated_at = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), _now(), content_id),
        )
        self._log(content_id, current, current, actor=actor, note=note or "mazmun yangilandi")
        self.conn.commit()

    def history(self, content_id: int) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT from_status, to_status, actor, note, at FROM status_history "
            "WHERE content_id = ? ORDER BY id", (content_id,))
        return [dict(r) for r in rows]

    def _log(self, content_id: int, frm: ContentStatus | None, to: ContentStatus,
             *, actor: str, note: str | None) -> None:
        self.conn.execute(
            "INSERT INTO status_history (content_id, from_status, to_status, actor, note, at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (content_id, frm.value if frm else None, to.value, actor, note, _now()),
        )

    def close(self) -> None:
        self.conn.close()
