from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from time import perf_counter

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from codex_mem.render import render_preflight
from codex_mem.store import MemoryStore


TOPICS = [
    "fare_floor",
    "yield_guard",
    "weekend_smoothing",
    "event_spike",
    "reopen_window",
    "family_travel",
    "red_eye_bias",
    "connection_shield",
    "golden_week_peak",
    "late_booking",
    "od_gate",
    "recapture_bias",
]

SEASONS = ["spring", "summer", "shoulder", "golden_week", "late_october"]
NOTES = [
    ("优先午班", "prefer-noon"),
    ("控制夜航", "cap-red-eye"),
    ("保商务流", "protect-business"),
    ("节中加价", "raise-mid-holiday"),
    ("节后回落", "soften-post-peak"),
    ("周末抬价", "lift-weekend"),
]


@dataclass
class MemoryRecord:
    index: int
    key: str
    topic: str
    owner: str
    route: str
    season: str
    threshold: int
    note_cn: str
    note_en: str
    text: str


@dataclass
class QueryOutcome:
    query: str
    expected_key: str
    top1_hit: bool
    top5_hit: bool
    latency_ms: float


def airport_code(index: int) -> str:
    value = index % (26 * 26 * 26)
    chars: list[str] = []
    for _ in range(3):
        chars.append(chr(ord("A") + (value % 26)))
        value //= 26
    return "".join(reversed(chars))


def make_record(index: int) -> MemoryRecord:
    key = f"MEM-{index:05d}"
    topic = TOPICS[index % len(TOPICS)]
    owner = f"owner{index:05d}"
    route = f"{airport_code(index)}-{airport_code(index + 137)}"
    season = SEASONS[index % len(SEASONS)]
    threshold = 10 + (index % 71)
    note_cn, note_en = NOTES[index % len(NOTES)]
    text = (
        f"{key} 主题={topic} 阈值={threshold} 负责人={owner} 城市对={route} "
        f"季节={season} 策略={note_cn} note={note_en}"
    )
    return MemoryRecord(
        index=index,
        key=key,
        topic=topic,
        owner=owner,
        route=route,
        season=season,
        threshold=threshold,
        note_cn=note_cn,
        note_en=note_en,
        text=text,
    )


def percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * ratio)))
    return ordered[idx]


def summarize_outcomes(outcomes: list[QueryOutcome]) -> dict[str, float | int]:
    if not outcomes:
        return {
            "queries": 0,
            "top1_hits": 0,
            "top5_hits": 0,
            "top1_accuracy": 0.0,
            "top5_accuracy": 0.0,
            "mean_latency_ms": 0.0,
            "p50_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "max_latency_ms": 0.0,
        }
    latencies = [item.latency_ms for item in outcomes]
    top1_hits = sum(1 for item in outcomes if item.top1_hit)
    top5_hits = sum(1 for item in outcomes if item.top5_hit)
    return {
        "queries": len(outcomes),
        "top1_hits": top1_hits,
        "top5_hits": top5_hits,
        "top1_accuracy": round(top1_hits / len(outcomes), 4),
        "top5_accuracy": round(top5_hits / len(outcomes), 4),
        "mean_latency_ms": round(statistics.fmean(latencies), 3),
        "p50_latency_ms": round(percentile(latencies, 0.50), 3),
        "p95_latency_ms": round(percentile(latencies, 0.95), 3),
        "max_latency_ms": round(max(latencies), 3),
    }


def pick_indices(size: int, count: int) -> list[int]:
    if size <= 0 or count <= 0:
        return []
    if count >= size:
        return list(range(size))
    step = size / count
    result: list[int] = []
    for pos in range(count):
        idx = min(size - 1, int(pos * step))
        if idx not in result:
            result.append(idx)
    while len(result) < count:
        candidate = len(result) % size
        if candidate not in result:
            result.append(candidate)
    return result[:count]


def run_queries(store: MemoryStore, records: list[MemoryRecord], queries: list[str]) -> list[QueryOutcome]:
    outcomes: list[QueryOutcome] = []
    for record, query in zip(records, queries, strict=True):
        started = perf_counter()
        results = store.search(query, project="extreme-self-test", limit=5)
        latency_ms = (perf_counter() - started) * 1000
        snippets = [item.snippet for item in results]
        top1_hit = bool(snippets and record.key in snippets[0])
        top5_hit = any(record.key in snippet for snippet in snippets)
        outcomes.append(
            QueryOutcome(
                query=query,
                expected_key=record.key,
                top1_hit=top1_hit,
                top5_hit=top5_hit,
                latency_ms=round(latency_ms, 3),
            )
        )
    return outcomes


def exact_query(record: MemoryRecord) -> str:
    return f"{record.key} {record.owner} {record.route}"


def bilingual_query(record: MemoryRecord) -> str:
    return f"哪个规则提到 {record.owner} 的 {record.route} 在 {record.season} 要 {record.note_cn} 并且主题是 {record.topic}"


def run_suite(size: int, query_count: int) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="codex_mem_extreme_") as tmpdir:
        store = MemoryStore(Path(tmpdir))
        store.init_db()

        records = [make_record(index) for index in range(size)]
        started = perf_counter()
        inserted = 0
        for record in records:
            inserted += 1 if store.add_memory(
                text=record.text,
                category="benchmark",
                tags=["benchmark", record.topic, record.season],
                source="extreme-self-test",
                importance=4,
                pinned=False,
                project="extreme-self-test",
            ) else 0
        ingest_seconds = perf_counter() - started

        store.update_project_state(
            project="extreme-self-test",
            summary=f"Loaded {inserted} synthetic memories for an extreme retrieval self-test.",
            open_loops=["Review the largest latency bucket.", "Consider indexing if search latency climbs too far."],
            decisions=["Keep the benchmark synthetic and deterministic.", "Measure both exact and bilingual retrieval paths."],
            changed_files=["scripts/run_extreme_self_test.py"],
            source="extreme-self-test",
            replace=True,
        )

        sample_indices = pick_indices(size, query_count)
        sample_records = [records[idx] for idx in sample_indices]
        exact_outcomes = run_queries(store, sample_records, [exact_query(item) for item in sample_records])
        bilingual_outcomes = run_queries(store, sample_records, [bilingual_query(item) for item in sample_records])

        preflight_started = perf_counter()
        preflight_text = render_preflight(
            store,
            project="extreme-self-test",
            query="golden week owner noon",
            memory_limit=8,
            capture_limit=5,
        )
        preflight_ms = (perf_counter() - preflight_started) * 1000
        db_size_kb = round(store.db_path.stat().st_size / 1024, 2)

    return {
        "size": size,
        "inserted": inserted,
        "ingest_seconds": round(ingest_seconds, 3),
        "ingest_per_second": round(inserted / ingest_seconds, 2) if ingest_seconds else 0.0,
        "db_size_kb": db_size_kb,
        "preflight_ms": round(preflight_ms, 3),
        "preflight_lines": len(preflight_text.splitlines()),
        "exact": summarize_outcomes(exact_outcomes),
        "bilingual": summarize_outcomes(bilingual_outcomes),
        "samples": {
            "exact_top1_first3": [asdict(item) for item in exact_outcomes[:3]],
            "bilingual_top1_first3": [asdict(item) for item in bilingual_outcomes[:3]],
        },
    }


def build_markdown(results: dict[str, object]) -> str:
    suites = results["suites"]
    lines = [
        "# Extreme Self-Test",
        "",
        f"Generated: {results['generated_at']}",
        "",
        "## Summary",
        "",
        f"- Store implementation: `MemoryStore` from `codex_mem.store`",
        f"- Python: `{results['python']}`",
        f"- Platform: `{results['platform']}`",
        f"- Query modes: exact key lookup and bilingual natural-language lookup",
        "",
        "## Results",
        "",
        "| Corpus | Ingest (s) | Ingest/s | DB size (KB) | Exact Top1 | Exact P95 (ms) | Bilingual Top1 | Bilingual P95 (ms) | Preflight (ms) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for suite in suites:
        lines.append(
            "| {size} | {ingest_seconds} | {ingest_per_second} | {db_size_kb} | {exact_top1:.2%} | {exact_p95} | {bilingual_top1:.2%} | {bilingual_p95} | {preflight_ms} |".format(
                size=suite["size"],
                ingest_seconds=suite["ingest_seconds"],
                ingest_per_second=suite["ingest_per_second"],
                db_size_kb=suite["db_size_kb"],
                exact_top1=suite["exact"]["top1_accuracy"],
                exact_p95=suite["exact"]["p95_latency_ms"],
                bilingual_top1=suite["bilingual"]["top1_accuracy"],
                bilingual_p95=suite["bilingual"]["p95_latency_ms"],
                preflight_ms=suite["preflight_ms"],
            )
        )

    largest = suites[-1]
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- The largest verified corpus in this run was `{largest['size']}` synthetic memories, which is far beyond a normal active chat context window.",
            f"- Exact retrieval stayed at `{largest['exact']['top1_accuracy']:.2%}` top-1 accuracy on the largest corpus.",
            f"- Bilingual natural-language retrieval stayed at `{largest['bilingual']['top1_accuracy']:.2%}` top-1 accuracy on the largest corpus.",
            f"- Largest-corpus search latency stayed under `{largest['bilingual']['p95_latency_ms']}` ms at p95 for bilingual lookups in this environment.",
            "",
            "## Limits",
            "",
            "- This benchmark uses synthetic but structured memories, not messy real transcripts.",
            "- The current write path inserts one memory at a time, so ingest speed is a conservative real-world number rather than a bulk-load maximum.",
            "- Search is still an MVP full-scan ranking path; if the corpus grows much larger, indexing or retrieval prefilters will likely be the next optimization.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "python scripts/run_extreme_self_test.py \\",
            "  --sizes 1000 5000 10000 \\",
            "  --query-count 120 \\",
            "  --output-json docs/benchmarks/extreme-self-test.json \\",
            "  --output-md docs/benchmarks/extreme-self-test.md",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a reproducible extreme self-test for codex-mem.")
    parser.add_argument("--sizes", nargs="+", type=int, default=[1000, 5000, 10000], help="Corpus sizes to benchmark.")
    parser.add_argument("--query-count", type=int, default=120, help="Queries per retrieval mode for each corpus size.")
    parser.add_argument("--output-json", default="", help="Optional path for raw JSON results.")
    parser.add_argument("--output-md", default="", help="Optional path for a Markdown report.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    suites = [run_suite(size, args.query_count) for size in args.sizes]
    results = {
        "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "sizes": args.sizes,
        "query_count": args.query_count,
        "suites": suites,
    }

    raw_json = json.dumps(results, ensure_ascii=False, indent=2)
    markdown = build_markdown(results)

    if args.output_json:
        output_json_path = Path(args.output_json)
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(raw_json, encoding="utf-8")
    if args.output_md:
        output_md_path = Path(args.output_md)
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.write_text(markdown, encoding="utf-8")

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
