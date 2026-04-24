from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from codex_mem.legacy import import_legacy_store
from codex_mem.render import render_preflight
from codex_mem.store import MemoryStore


class CodexMemTests(unittest.TestCase):
    def make_store(self) -> tuple[tempfile.TemporaryDirectory[str], MemoryStore]:
        tmp = tempfile.TemporaryDirectory()
        store = MemoryStore(Path(tmp.name))
        store.init_db()
        return tmp, store

    def test_remember_and_search(self) -> None:
        tmp, store = self.make_store()
        self.addCleanup(tmp.cleanup)

        self.assertTrue(store.remember("Remember this: the user prefers concise answers.", source="test"))
        results = store.search("concise prefers", limit=5)
        self.assertTrue(results)
        self.assertEqual(results[0].kind, "memory")

    def test_capture_updates_project_state(self) -> None:
        tmp, store = self.make_store()
        self.addCleanup(tmp.cleanup)

        capture = store.add_capture(
            project="air-pricing",
            summary="Built the holiday segmentation logic and generated a new workbook.",
            decisions=["Segment Golden Week using day-level historical fare behavior."],
            next_steps=["Verify whether September 30 should merge into October 1 for this route."],
            changed_files=["build_group_fares_from_schedule.py"],
            rules=["Remember this: Golden Week group fares may merge September 30 into October 1 when history is similar."],
            source="test-capture",
        )
        state = store.get_project_state("air-pricing")
        self.assertIsNotNone(state)
        assert state is not None
        self.assertIn("Segment Golden Week using day-level historical fare behavior.", state["decisions"])
        brief = render_preflight(store, project="air-pricing", query="holiday fares")
        self.assertIn("Project State", brief)
        self.assertEqual(capture["rules_inserted"], 1)

    def test_import_legacy(self) -> None:
        tmp, store = self.make_store()
        self.addCleanup(tmp.cleanup)

        legacy_dir = Path(tmp.name) / "legacy"
        legacy_dir.mkdir()
        legacy_db = legacy_dir / "memory.db"
        conn = sqlite3.connect(legacy_db)
        conn.execute(
            """
            CREATE TABLE memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'general',
                tags_json TEXT NOT NULL DEFAULT '[]',
                importance INTEGER NOT NULL DEFAULT 3,
                pinned INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0,
                last_accessed_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO memories (
                created_at, updated_at, text, source, category, tags_json, importance, pinned, archived, last_accessed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                "2026-01-01T00:00:00+00:00",
                "2026-01-01T00:00:00+00:00",
                "The user prefers less repetition.",
                "legacy",
                "prefs",
                '["memory", "style"]',
                5,
                1,
                "2026-01-01T00:00:00+00:00",
            ),
        )
        conn.commit()
        conn.close()

        imported, skipped = import_legacy_store(store, legacy_dir)
        self.assertEqual(imported, 1)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(store.get_memories()), 1)


if __name__ == "__main__":
    unittest.main()
