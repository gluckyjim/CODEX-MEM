from __future__ import annotations

from .store import MemoryStore, SearchResult, shorten


def render_search_results(results: list[SearchResult]) -> str:
    if not results:
        return "No matches found.\n"
    lines = ["# Search Results", ""]
    for item in results:
        label = f"{item.kind}"
        if item.record_id is not None:
            label = f"{label}#{item.record_id}"
        tags = f" [{', '.join(item.tags)}]" if item.tags else ""
        lines.append(f"- {label} [{item.project}] {item.title}{tags}")
        lines.append(f"  {shorten(item.snippet, 180)}")
    return "\n".join(lines) + "\n"


def render_preflight(
    store: MemoryStore,
    *,
    project: str | None,
    query: str,
    memory_limit: int = 8,
    capture_limit: int = 5,
) -> str:
    pinned = store.get_pinned_memories(limit=10)
    state = store.get_project_state(project) if project else None
    hits = store.search(query, project=project, limit=memory_limit) if query else []
    captures = store.get_recent_captures(project=project, limit=capture_limit)

    lines = [
        "# Codex-Mem Preflight",
        "",
        f"Store: {store.home}",
    ]
    if project:
        lines.append(f"Project: {project}")
    if query:
        lines.append(f"Query: {query}")

    lines.extend(["", "## Stable Rules"])
    if pinned:
        for memory in pinned:
            lines.append(f"- {memory['text']}")
    else:
        lines.append("- No pinned rules yet.")

    lines.extend(["", "## Project State"])
    if state:
        lines.append(state["summary"] or "No summary yet.")
        if state["open_loops"]:
            lines.append("")
            lines.append("Open loops:")
            lines.extend(f"- {item}" for item in state["open_loops"][:8])
        if state["decisions"]:
            lines.append("")
            lines.append("Recent decisions:")
            lines.extend(f"- {item}" for item in state["decisions"][:8])
    else:
        lines.append("- No saved project state yet.")

    lines.extend(["", "## Relevant Hits"])
    if hits:
        for item in hits:
            label = f"{item.kind}"
            if item.record_id is not None:
                label = f"{label}#{item.record_id}"
            lines.append(f"- {label} [{item.project}] {item.title}")
            lines.append(f"  {shorten(item.snippet, 160)}")
    else:
        lines.append("- No targeted hits yet.")

    lines.extend(["", "## Recent Captures"])
    if captures:
        for capture in captures:
            lines.append(f"- #{capture['id']} [{capture['project']}] {capture['title']}")
            if capture["decisions"]:
                lines.append(f"  decisions: {', '.join(capture['decisions'][:3])}")
            if capture["next_steps"]:
                lines.append(f"  next: {', '.join(capture['next_steps'][:3])}")
    else:
        lines.append("- No captures yet.")

    return "\n".join(lines) + "\n"
