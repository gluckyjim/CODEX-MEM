from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .legacy import import_legacy_store
from .render import render_preflight, render_search_results
from .store import MemoryStore, infer_project, parse_tags


def read_text_input(args: argparse.Namespace) -> str:
    if getattr(args, "text", ""):
        return args.text
    if getattr(args, "file", ""):
        return Path(args.file).read_text(encoding="utf-8")
    return ""


def build_store(args: argparse.Namespace) -> MemoryStore:
    store = MemoryStore(home=args.home)
    store.init_db()
    return store


def cmd_init(args: argparse.Namespace) -> int:
    store = build_store(args)
    store.refresh_views()
    print(f"Initialized codex-mem at {store.home}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    store = build_store(args)
    store.refresh_views()
    print(f"home={store.home}")
    print(f"db={store.db_path}")
    print(f"profile={store.profile_path}")
    print(f"context={store.context_path}")
    print(f"memories={len(store.get_memories())}")
    print(f"captures={len(store.get_recent_captures(limit=9999))}")
    print(f"project_states={len(store.list_project_states(limit=9999))}")
    return 0


def cmd_remember(args: argparse.Namespace) -> int:
    store = build_store(args)
    project = infer_project(args.project, args.cwd)
    text = read_text_input(args)
    if not text.strip():
        raise SystemExit("Provide --text or --file for remember.")
    ok = store.remember(text, source=args.source, project=project)
    store.refresh_views()
    print("Remembered." if ok else "Memory already exists. Skipped.")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    store = build_store(args)
    project = infer_project(args.project, args.cwd) if args.project or args.cwd else None
    results = store.search(args.query, project=project, limit=args.limit)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "kind": item.kind,
                        "id": item.record_id,
                        "project": item.project,
                        "title": item.title,
                        "snippet": item.snippet,
                        "score": round(item.score, 3),
                        "source": item.source,
                        "tags": item.tags,
                    }
                    for item in results
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(render_search_results(results), end="")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    store = build_store(args)
    project = infer_project(args.project, args.cwd) if args.project or args.cwd else None
    print(
        render_preflight(
            store,
            project=project,
            query=args.query.strip(),
            memory_limit=args.limit,
            capture_limit=args.captures,
        ),
        end="",
    )
    return 0


def cmd_capture(args: argparse.Namespace) -> int:
    store = build_store(args)
    project = infer_project(args.project, args.cwd)
    raw_text = read_text_input(args)
    capture = store.add_capture(
        project=project,
        summary=args.summary,
        decisions=args.decision,
        next_steps=args.next_step,
        changed_files=args.changed_file,
        source=args.source,
        tags=args.tag,
        raw_text=raw_text,
        rules=args.rule,
        apply_extract=args.apply_extract,
        update_state=not args.skip_state,
    )
    print(
        json.dumps(
            {
                "capture_id": capture["id"],
                "project": capture["project"],
                "rules_inserted": capture["rules_inserted"],
                "extracted_inserted": capture["extracted_inserted"],
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_project_state_show(args: argparse.Namespace) -> int:
    store = build_store(args)
    project = infer_project(args.project, args.cwd)
    print(store.render_project_state(project), end="")
    return 0


def cmd_project_state_update(args: argparse.Namespace) -> int:
    store = build_store(args)
    project = infer_project(args.project, args.cwd)
    state = store.update_project_state(
        project=project,
        summary=args.summary,
        open_loops=args.open_loop,
        decisions=args.decision,
        changed_files=args.changed_file,
        source=args.source,
        replace=args.replace,
    )
    store.refresh_views()
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
    else:
        print(store.render_project_state(project), end="")
    return 0


def cmd_import_legacy(args: argparse.Namespace) -> int:
    store = build_store(args)
    imported, skipped = import_legacy_store(store, args.path)
    print(json.dumps({"imported": imported, "skipped": skipped}, ensure_ascii=False))
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    store = build_store(args)
    store.refresh_views()
    print(f"Refreshed {store.profile_path} and {store.context_path}")
    return 0


def add_common_store_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--home",
        default="",
        help="codex-mem home directory. Defaults to repo-local ./state.",
    )


def add_project_arguments(parser: argparse.ArgumentParser, *, optional: bool = True) -> None:
    parser.add_argument("--project", default="", required=not optional, help="Project name.")
    parser.add_argument("--cwd", default="", help="Working directory to infer the project from.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local-first persistent memory workflow for Codex.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize the codex-mem store.")
    add_common_store_argument(init_parser)
    init_parser.set_defaults(func=cmd_init)

    doctor_parser = subparsers.add_parser("doctor", help="Show store paths and counts.")
    add_common_store_argument(doctor_parser)
    doctor_parser.set_defaults(func=cmd_doctor)

    remember_parser = subparsers.add_parser("remember", help="Store a stable rule or preference.")
    add_common_store_argument(remember_parser)
    add_project_arguments(remember_parser)
    remember_parser.add_argument("--text", default="", help="Inline memory text.")
    remember_parser.add_argument("--file", default="", help="Path to a UTF-8 text file.")
    remember_parser.add_argument("--source", default="remember-trigger", help="Source label.")
    remember_parser.set_defaults(func=cmd_remember)

    search_parser = subparsers.add_parser("search", help="Search across memories, captures, and project state.")
    add_common_store_argument(search_parser)
    add_project_arguments(search_parser)
    search_parser.add_argument("--query", required=True, help="Search query.")
    search_parser.add_argument("--limit", type=int, default=8, help="Result limit.")
    search_parser.add_argument("--json", action="store_true", help="Emit JSON.")
    search_parser.set_defaults(func=cmd_search)

    preflight_parser = subparsers.add_parser("preflight", help="Render a compact pre-work context brief.")
    add_common_store_argument(preflight_parser)
    add_project_arguments(preflight_parser)
    preflight_parser.add_argument("--query", default="", help="Optional query to target the context pack.")
    preflight_parser.add_argument("--limit", type=int, default=8, help="Relevant hit limit.")
    preflight_parser.add_argument("--captures", type=int, default=5, help="Recent capture limit.")
    preflight_parser.set_defaults(func=cmd_preflight)

    capture_parser = subparsers.add_parser("capture", help="Store a session summary and refresh project state.")
    add_common_store_argument(capture_parser)
    add_project_arguments(capture_parser, optional=False)
    capture_parser.add_argument("--summary", required=True, help="Short summary of the work completed.")
    capture_parser.add_argument("--decision", action="append", default=[], help="Key decision to retain.")
    capture_parser.add_argument("--next-step", action="append", default=[], help="Open loop or next step.")
    capture_parser.add_argument("--changed-file", action="append", default=[], help="Changed file path.")
    capture_parser.add_argument("--tag", action="append", default=[], help="Tag for the capture.")
    capture_parser.add_argument("--rule", action="append", default=[], help="Stable rule to also save as memory.")
    capture_parser.add_argument("--text", default="", help="Transcript or summary text to mine.")
    capture_parser.add_argument("--file", default="", help="Path to a UTF-8 transcript file.")
    capture_parser.add_argument("--source", default="codex-session", help="Source label.")
    capture_parser.add_argument("--apply-extract", action="store_true", help="Extract stable memories from --text/--file.")
    capture_parser.add_argument("--skip-state", action="store_true", help="Do not update project state.")
    capture_parser.set_defaults(func=cmd_capture)

    project_state_parser = subparsers.add_parser("project-state", help="Show or update a rolling project snapshot.")
    add_common_store_argument(project_state_parser)
    state_subparsers = project_state_parser.add_subparsers(dest="state_command", required=True)

    state_show = state_subparsers.add_parser("show", help="Show project state.")
    add_project_arguments(state_show, optional=False)
    state_show.set_defaults(func=cmd_project_state_show)

    state_update = state_subparsers.add_parser("update", help="Update project state.")
    add_project_arguments(state_update, optional=False)
    state_update.add_argument("--summary", default="", help="Latest summary.")
    state_update.add_argument("--open-loop", action="append", default=[], help="Open loop or pending item.")
    state_update.add_argument("--decision", action="append", default=[], help="Key project decision.")
    state_update.add_argument("--changed-file", action="append", default=[], help="Changed file path.")
    state_update.add_argument("--source", default="manual-update", help="Source label.")
    state_update.add_argument("--replace", action="store_true", help="Replace list fields instead of merging.")
    state_update.add_argument("--json", action="store_true", help="Emit JSON.")
    state_update.set_defaults(func=cmd_project_state_update)

    legacy_parser = subparsers.add_parser("import-legacy", help="Import the older memory.db schema into codex-mem.")
    add_common_store_argument(legacy_parser)
    legacy_parser.add_argument("--path", required=True, help="Path to a legacy memory.db or its parent directory.")
    legacy_parser.set_defaults(func=cmd_import_legacy)

    refresh_parser = subparsers.add_parser("refresh", help="Rebuild profile.md and context.md.")
    add_common_store_argument(refresh_parser)
    refresh_parser.set_defaults(func=cmd_refresh)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.home == "":
        args.home = ""
    return args.func(args)
