from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .store import MemoryStore


def resolve_legacy_db(path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_dir():
        return candidate / "memory.db"
    return candidate


def import_legacy_store(store: MemoryStore, path: str | Path) -> tuple[int, int]:
    legacy_db = resolve_legacy_db(path)
    if not legacy_db.exists():
        raise FileNotFoundError(f"Legacy memory database not found: {legacy_db}")

    conn = sqlite3.connect(legacy_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT created_at, updated_at, text, source, category, tags_json, importance, pinned
            FROM memories
            WHERE archived = 0
            ORDER BY id ASC
            """
        ).fetchall()
    finally:
        conn.close()

    imported = 0
    skipped = 0
    for row in rows:
        ok = store.add_memory(
            text=row["text"],
            category=row["category"] or "general",
            tags=[] if not row["tags_json"] else json.loads(row["tags_json"]),
            source=row["source"] or "legacy-import",
            importance=int(row["importance"] or 3),
            pinned=bool(row["pinned"]),
            project="global",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        if ok:
            imported += 1
        else:
            skipped += 1
    store.refresh_views()
    return imported, skipped
