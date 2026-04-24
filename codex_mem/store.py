from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .scoring import has_significant_match, normalize_for_match, score_text, similarity, tokenize, utc_now


DEFAULT_HOME = Path(__file__).resolve().parents[1] / "state"


def ensure_list(values: list[str] | tuple[str, ...] | None) -> list[str]:
    if not values:
        return []
    seen: set[str] = set()
    cleaned: list[str] = []
    for value in values:
        item = str(value).strip()
        if not item or item in seen:
            continue
        seen.add(item)
        cleaned.append(item)
    return cleaned


def parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return ensure_list(part.strip() for part in raw.split(","))


def infer_project(project: str | None = None, cwd: str | None = None) -> str:
    if project and project.strip():
        return project.strip()
    if cwd and cwd.strip():
        name = Path(cwd).resolve().name.strip()
        if name:
            return name
    return "global"


def shorten(text: str, limit: int = 120) -> str:
    compact = re.sub(r"\s+", " ", (text or "").strip())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"


def normalize_sentence(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^\s*(user|assistant|system|用户|助手|系统)\s*[:：]\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -\t\r\n")


def split_sentences(text: str) -> list[str]:
    prepared = (text or "").replace("\r\n", "\n")
    parts = re.split(r"[\n。！？!?；;]+", prepared)
    return [normalize_sentence(part) for part in parts if normalize_sentence(part)]


def infer_category(sentence: str) -> str:
    if re.search(r"记忆|记住|工作流|开工前|读取|检索|总结|preflight|capture", sentence, re.I):
        return "workflow"
    if re.search(r"偏好|希望|要求|请用|不要|尽量|优先|中文|简洁|直接|风格", sentence, re.I):
        return "prefs"
    if re.search(r"项目|运价|航空|航班|DCP|航线|模型|规则|数据", sentence, re.I):
        return "project"
    return "general"


def infer_tags(sentence: str, category: str) -> list[str]:
    tags = {category}
    keyword_map = {
        "中文": "language",
        "英文": "language",
        "直接": "style",
        "简洁": "style",
        "上下文": "context",
        "Codex": "codex",
        "codex": "codex",
        "记忆": "memory",
        "记住": "memory",
        "工作流": "workflow",
        "本地": "local",
        "航空": "aviation",
        "航班": "aviation",
        "运价": "pricing",
        "DCP": "dcp",
    }
    lowered = sentence.lower()
    for needle, tag in keyword_map.items():
        if needle.lower() in lowered:
            tags.add(tag)
    return sorted(tags)


def infer_importance(sentence: str, category: str) -> int:
    if re.search(r"记住这条|必须|总是|始终|长期|以后|默认|不要|优先", sentence, re.I):
        return 5 if category in {"prefs", "workflow"} else 4
    if category in {"prefs", "workflow", "project"}:
        return 4
    return 3


def infer_pinned(sentence: str, category: str, importance: int) -> bool:
    if "记住这条" in sentence:
        return True
    return category in {"prefs", "workflow"} and importance >= 4


def is_stable_candidate(sentence: str) -> bool:
    patterns = [
        r"记住这条",
        r"用户.*(偏好|希望|要求|习惯|长期)",
        r"(请用|不要|尽量|优先).{0,20}(中文|英文|直接|简洁|上下文|延续)",
        r"(长期|以后|未来|默认|始终|总是).{0,30}(规则|流程|偏好|项目|工作流)",
        r"(项目|工作区).{0,30}(背景|事实|规则|约定)",
        r"(回答|沟通).{0,20}(直接|简洁|可执行)",
    ]
    return any(re.search(pattern, sentence, re.I) for pattern in patterns)


def strip_remember_trigger(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^(请)?记住这条[：:\s-]*", "", cleaned)
    cleaned = re.sub(r"^这条是(长期)?规则[：:\s-]*", "", cleaned)
    return cleaned.strip()


def is_duplicate_candidate(candidate_text: str, existing_texts: list[str]) -> bool:
    candidate_norm = normalize_for_match(candidate_text)
    for existing_text in existing_texts:
        existing_norm = normalize_for_match(existing_text)
        if not existing_norm:
            continue
        if candidate_norm == existing_norm:
            return True
        if len(candidate_norm) >= 16 and (candidate_norm in existing_norm or existing_norm in candidate_norm):
            return True
        if similarity(candidate_text, existing_text) >= 0.93:
            return True
    return False


def extract_candidates(text: str, existing_texts: list[str]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for sentence in split_sentences(text):
        sentence = strip_remember_trigger(sentence)
        if len(sentence) < 8 or len(sentence) > 220:
            continue
        if "记住这条" not in text and not is_stable_candidate(sentence):
            continue
        dedupe_key = normalize_for_match(sentence)
        if dedupe_key in seen:
            continue
        if is_duplicate_candidate(sentence, existing_texts + [item["text"] for item in candidates]):
            continue
        category = infer_category(sentence)
        importance = infer_importance(sentence, category)
        candidates.append(
            {
                "text": sentence,
                "category": category,
                "tags": infer_tags(sentence, category),
                "importance": importance,
                "pinned": infer_pinned(sentence, category, importance),
            }
        )
        seen.add(dedupe_key)
    return candidates


@dataclass
class SearchResult:
    kind: str
    record_id: int | None
    project: str
    title: str
    snippet: str
    score: float
    created_at: str
    source: str
    tags: list[str]


class MemoryStore:
    def __init__(self, home: str | Path | None = None) -> None:
        self.home = Path(home) if home else DEFAULT_HOME
        self.db_path = self.home / "memory.db"
        self.profile_path = self.home / "profile.md"
        self.context_path = self.home / "context.md"

    def connect(self) -> sqlite3.Connection:
        self.home.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def session(self) -> Any:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.session() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    project TEXT NOT NULL DEFAULT 'global',
                    text TEXT NOT NULL,
                    normalized_text TEXT NOT NULL,
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
                CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_normalized
                ON memories(normalized_text)
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS captures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    project TEXT NOT NULL DEFAULT 'global',
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    decisions_json TEXT NOT NULL DEFAULT '[]',
                    next_steps_json TEXT NOT NULL DEFAULT '[]',
                    changed_files_json TEXT NOT NULL DEFAULT '[]',
                    source TEXT NOT NULL DEFAULT '',
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    raw_text TEXT NOT NULL DEFAULT ''
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_states (
                    project TEXT PRIMARY KEY,
                    updated_at TEXT NOT NULL,
                    summary TEXT NOT NULL DEFAULT '',
                    open_loops_json TEXT NOT NULL DEFAULT '[]',
                    decisions_json TEXT NOT NULL DEFAULT '[]',
                    changed_files_json TEXT NOT NULL DEFAULT '[]',
                    source TEXT NOT NULL DEFAULT '',
                    last_capture_id INTEGER
                )
                """
            )

    def row_to_memory(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "project": row["project"],
            "text": row["text"],
            "source": row["source"],
            "category": row["category"],
            "tags": json.loads(row["tags_json"] or "[]"),
            "importance": int(row["importance"]),
            "pinned": bool(row["pinned"]),
            "archived": bool(row["archived"]),
            "last_accessed_at": row["last_accessed_at"],
        }

    def row_to_capture(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "project": row["project"],
            "title": row["title"],
            "summary": row["summary"],
            "decisions": json.loads(row["decisions_json"] or "[]"),
            "next_steps": json.loads(row["next_steps_json"] or "[]"),
            "changed_files": json.loads(row["changed_files_json"] or "[]"),
            "source": row["source"],
            "tags": json.loads(row["tags_json"] or "[]"),
            "raw_text": row["raw_text"] or "",
        }

    def get_memories(self, include_archived: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM memories"
        if not include_archived:
            query += " WHERE archived = 0"
        query += " ORDER BY pinned DESC, importance DESC, id DESC"
        with self.session() as conn:
            rows = conn.execute(query).fetchall()
        return [self.row_to_memory(row) for row in rows]

    def get_pinned_memories(self, limit: int = 12) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute(
                "SELECT * FROM memories WHERE archived = 0 AND pinned = 1 ORDER BY importance DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self.row_to_memory(row) for row in rows]

    def get_recent_captures(self, project: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
        query = "SELECT * FROM captures"
        params: list[Any] = []
        if project:
            query += " WHERE project = ?"
            params.append(project)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        with self.session() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self.row_to_capture(row) for row in rows]

    def get_project_state(self, project: str) -> dict[str, Any] | None:
        with self.session() as conn:
            row = conn.execute("SELECT * FROM project_states WHERE project = ?", (project,)).fetchone()
        if row is None:
            return None
        return {
            "project": row["project"],
            "updated_at": row["updated_at"],
            "summary": row["summary"],
            "open_loops": json.loads(row["open_loops_json"] or "[]"),
            "decisions": json.loads(row["decisions_json"] or "[]"),
            "changed_files": json.loads(row["changed_files_json"] or "[]"),
            "source": row["source"],
            "last_capture_id": row["last_capture_id"],
        }

    def add_memory(
        self,
        *,
        text: str,
        category: str = "general",
        tags: list[str] | None = None,
        source: str = "",
        importance: int = 3,
        pinned: bool = False,
        project: str = "global",
        created_at: str | None = None,
        updated_at: str | None = None,
    ) -> bool:
        now = utc_now()
        created = created_at or now
        updated = updated_at or now
        normalized = normalize_for_match(text)
        if not normalized:
            return False
        with self.session() as conn:
            exists = conn.execute(
                "SELECT 1 FROM memories WHERE normalized_text = ?",
                (normalized,),
            ).fetchone()
            if exists:
                return False
            conn.execute(
                """
                INSERT INTO memories (
                    created_at, updated_at, project, text, normalized_text, source,
                    category, tags_json, importance, pinned, archived, last_accessed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    created,
                    updated,
                    project,
                    text.strip(),
                    normalized,
                    source.strip(),
                    category.strip(),
                    json.dumps(ensure_list(tags), ensure_ascii=False),
                    int(importance),
                    1 if pinned else 0,
                    updated,
                ),
            )
        return True

    def remember(self, text: str, *, source: str = "remember-trigger", project: str = "global") -> bool:
        clean = strip_remember_trigger(text)
        category = infer_category(clean)
        return self.add_memory(
            text=clean,
            category=category,
            tags=infer_tags(clean, category),
            source=source,
            importance=max(4, infer_importance(clean, category)),
            pinned=True,
            project=project,
        )

    def update_project_state(
        self,
        *,
        project: str,
        summary: str | None = None,
        open_loops: list[str] | None = None,
        decisions: list[str] | None = None,
        changed_files: list[str] | None = None,
        source: str = "",
        last_capture_id: int | None = None,
        replace: bool = False,
    ) -> dict[str, Any]:
        current = self.get_project_state(project) or {
            "project": project,
            "summary": "",
            "open_loops": [],
            "decisions": [],
            "changed_files": [],
            "source": "",
            "last_capture_id": None,
        }
        summary_text = (summary or "").strip()
        merged = {
            "summary": summary_text if summary_text else current["summary"],
            "open_loops": ensure_list(open_loops if replace else [*(open_loops or []), *current["open_loops"]]),
            "decisions": ensure_list(decisions if replace else [*(decisions or []), *current["decisions"]]),
            "changed_files": ensure_list(changed_files if replace else [*(changed_files or []), *current["changed_files"]]),
            "source": source.strip() or current["source"],
            "last_capture_id": last_capture_id or current["last_capture_id"],
        }
        with self.session() as conn:
            conn.execute(
                """
                INSERT INTO project_states (
                    project, updated_at, summary, open_loops_json, decisions_json,
                    changed_files_json, source, last_capture_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project) DO UPDATE SET
                    updated_at = excluded.updated_at,
                    summary = excluded.summary,
                    open_loops_json = excluded.open_loops_json,
                    decisions_json = excluded.decisions_json,
                    changed_files_json = excluded.changed_files_json,
                    source = excluded.source,
                    last_capture_id = excluded.last_capture_id
                """,
                (
                    project,
                    utc_now(),
                    merged["summary"],
                    json.dumps(merged["open_loops"], ensure_ascii=False),
                    json.dumps(merged["decisions"], ensure_ascii=False),
                    json.dumps(merged["changed_files"], ensure_ascii=False),
                    merged["source"],
                    merged["last_capture_id"],
                ),
            )
        return self.get_project_state(project) or merged

    def add_capture(
        self,
        *,
        project: str,
        summary: str,
        decisions: list[str] | None = None,
        next_steps: list[str] | None = None,
        changed_files: list[str] | None = None,
        source: str = "codex-session",
        tags: list[str] | None = None,
        raw_text: str = "",
        rules: list[str] | None = None,
        apply_extract: bool = False,
        update_state: bool = True,
    ) -> dict[str, Any]:
        now = utc_now()
        decisions = ensure_list(decisions)
        next_steps = ensure_list(next_steps)
        changed_files = ensure_list(changed_files)
        tags = ensure_list(tags)
        rules = ensure_list(rules)
        title = shorten(summary, 72) or "Session capture"

        with self.session() as conn:
            cursor = conn.execute(
                """
                INSERT INTO captures (
                    created_at, updated_at, project, title, summary, decisions_json,
                    next_steps_json, changed_files_json, source, tags_json, raw_text
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now,
                    now,
                    project,
                    title,
                    summary.strip(),
                    json.dumps(decisions, ensure_ascii=False),
                    json.dumps(next_steps, ensure_ascii=False),
                    json.dumps(changed_files, ensure_ascii=False),
                    source.strip(),
                    json.dumps(tags, ensure_ascii=False),
                    raw_text,
                ),
            )
            capture_id = int(cursor.lastrowid)

        inserted_rules = 0
        for rule in rules:
            if self.remember(rule, source=f"{source}:rule", project=project):
                inserted_rules += 1

        extracted = 0
        if apply_extract and raw_text.strip():
            existing = [item["text"] for item in self.get_memories(include_archived=False)]
            for candidate in extract_candidates(raw_text, existing):
                if self.add_memory(
                    text=candidate["text"],
                    category=candidate["category"],
                    tags=candidate["tags"],
                    source=f"{source}:extract",
                    importance=candidate["importance"],
                    pinned=candidate["pinned"],
                    project=project,
                ):
                    extracted += 1

        if update_state:
            self.update_project_state(
                project=project,
                summary=summary,
                open_loops=next_steps,
                decisions=decisions,
                changed_files=changed_files,
                source=source,
                last_capture_id=capture_id,
                replace=False,
            )

        capture = {
            "id": capture_id,
            "project": project,
            "summary": summary.strip(),
            "decisions": decisions,
            "next_steps": next_steps,
            "changed_files": changed_files,
            "source": source,
            "rules_inserted": inserted_rules,
            "extracted_inserted": extracted,
        }
        self.refresh_views()
        return capture

    def search(self, query: str, *, project: str | None = None, limit: int = 8) -> list[SearchResult]:
        query = query.strip()
        if not query:
            return []
        results: list[SearchResult] = []

        for memory in self.get_memories(include_archived=False):
            haystack = " ".join(
                [
                    memory["text"],
                    memory["project"],
                    memory["category"],
                    " ".join(memory["tags"]),
                    memory["source"],
                ]
            )
            score = score_text(
                query,
                haystack,
                importance=memory["importance"],
                pinned=memory["pinned"],
                created_at=memory["created_at"],
                project_match=bool(project and memory["project"] == project),
            )
            if score <= 0 or not has_significant_match(query, haystack):
                continue
            results.append(
                SearchResult(
                    kind="memory",
                    record_id=memory["id"],
                    project=memory["project"],
                    title=shorten(memory["text"], 72),
                    snippet=memory["text"],
                    score=score,
                    created_at=memory["created_at"],
                    source=memory["source"],
                    tags=memory["tags"],
                )
            )

        for capture in self.get_recent_captures(project=None, limit=200):
            haystack = " ".join(
                [
                    capture["project"],
                    capture["title"],
                    capture["summary"],
                    " ".join(capture["decisions"]),
                    " ".join(capture["next_steps"]),
                    " ".join(capture["changed_files"]),
                    " ".join(capture["tags"]),
                    capture["source"],
                ]
            )
            score = score_text(
                query,
                haystack,
                importance=4,
                pinned=False,
                created_at=capture["created_at"],
                project_match=bool(project and capture["project"] == project),
            )
            if score <= 0 or not has_significant_match(query, haystack):
                continue
            results.append(
                SearchResult(
                    kind="capture",
                    record_id=capture["id"],
                    project=capture["project"],
                    title=capture["title"],
                    snippet=shorten(capture["summary"], 180),
                    score=score,
                    created_at=capture["created_at"],
                    source=capture["source"],
                    tags=capture["tags"],
                )
            )

        if project:
            state = self.get_project_state(project)
            if state:
                haystack = " ".join(
                    [
                        state["project"],
                        state["summary"],
                        " ".join(state["open_loops"]),
                        " ".join(state["decisions"]),
                        " ".join(state["changed_files"]),
                        state["source"],
                    ]
                )
                score = score_text(
                    query,
                    haystack,
                    importance=5,
                    pinned=True,
                    created_at=state["updated_at"],
                    project_match=True,
                )
                if score > 0 and has_significant_match(query, haystack):
                    results.append(
                        SearchResult(
                            kind="project_state",
                            record_id=None,
                            project=state["project"],
                            title=f"Project state: {state['project']}",
                            snippet=shorten(state["summary"], 180),
                            score=score,
                            created_at=state["updated_at"],
                            source=state["source"],
                            tags=["project-state"],
                        )
                    )

        results.sort(key=lambda item: (-item.score, item.kind, -(item.record_id or 0)))
        return results[:limit]

    def render_profile_markdown(self) -> str:
        pinned = self.get_pinned_memories(limit=20)
        recent_captures = self.get_recent_captures(limit=10)
        lines = [
            "# Codex-Mem Profile",
            "",
            f"Updated: {utc_now()}",
            "",
            "## Stable Rules",
        ]
        if pinned:
            for memory in pinned:
                tags = f" [{', '.join(memory['tags'])}]" if memory["tags"] else ""
                lines.append(f"- #{memory['id']} {memory['text']}{tags}")
        else:
            lines.append("- No pinned memories yet.")

        lines.extend(["", "## Recent Captures"])
        if recent_captures:
            for capture in recent_captures[:8]:
                lines.append(f"- #{capture['id']} [{capture['project']}] {capture['title']}")
        else:
            lines.append("- No captures yet.")
        return "\n".join(lines) + "\n"

    def render_context_markdown(self) -> str:
        pinned = self.get_pinned_memories(limit=8)
        states = self.list_project_states(limit=8)
        lines = [
            "# Codex-Mem Context",
            "",
            f"Updated: {utc_now()}",
            "",
            "## Immediate Rules",
        ]
        if pinned:
            for memory in pinned:
                lines.append(f"- {memory['text']}")
        else:
            lines.append("- No pinned rules yet.")

        lines.extend(["", "## Active Project Snapshots"])
        if states:
            for state in states:
                lines.append(f"- [{state['project']}] {shorten(state['summary'], 120)}")
        else:
            lines.append("- No project states yet.")
        return "\n".join(lines) + "\n"

    def list_project_states(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.session() as conn:
            rows = conn.execute(
                "SELECT * FROM project_states ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "project": row["project"],
                "updated_at": row["updated_at"],
                "summary": row["summary"],
                "open_loops": json.loads(row["open_loops_json"] or "[]"),
                "decisions": json.loads(row["decisions_json"] or "[]"),
                "changed_files": json.loads(row["changed_files_json"] or "[]"),
                "source": row["source"],
                "last_capture_id": row["last_capture_id"],
            }
            for row in rows
        ]

    def refresh_views(self) -> None:
        self.home.mkdir(parents=True, exist_ok=True)
        self.profile_path.write_text(self.render_profile_markdown(), encoding="utf-8-sig")
        self.context_path.write_text(self.render_context_markdown(), encoding="utf-8-sig")

    def render_project_state(self, project: str) -> str:
        state = self.get_project_state(project)
        if not state:
            return f"# Project State\n\nProject: {project}\n\nNo saved state yet.\n"

        lines = [
            "# Project State",
            "",
            f"Project: {state['project']}",
            f"Updated: {state['updated_at']}",
            "",
            "## Summary",
            state["summary"] or "No summary yet.",
            "",
            "## Open Loops",
        ]
        if state["open_loops"]:
            lines.extend(f"- {item}" for item in state["open_loops"])
        else:
            lines.append("- None.")

        lines.extend(["", "## Decisions"])
        if state["decisions"]:
            lines.extend(f"- {item}" for item in state["decisions"])
        else:
            lines.append("- None.")

        lines.extend(["", "## Changed Files"])
        if state["changed_files"]:
            lines.extend(f"- {item}" for item in state["changed_files"])
        else:
            lines.append("- None.")
        return "\n".join(lines) + "\n"
