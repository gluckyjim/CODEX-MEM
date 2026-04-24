# Extreme Self-Test

Generated: 2026-04-24T15:02:44+08:00

## Summary

- Store implementation: `MemoryStore` from `codex_mem.store`
- Python: `3.12.10`
- Platform: `Windows-11-10.0.26200-SP0`
- Query modes: exact key lookup and bilingual natural-language lookup

## Results

| Corpus | Ingest (s) | Ingest/s | DB size (KB) | Exact Top1 | Exact P95 (ms) | Bilingual Top1 | Bilingual P95 (ms) | Preflight (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1000 | 4.381 | 228.28 | 656.0 | 100.00% | 55.011 | 100.00% | 95.802 | 64.699 |
| 5000 | 21.793 | 229.43 | 3160.0 | 100.00% | 276.247 | 100.00% | 556.352 | 325.463 |
| 10000 | 50.191 | 199.24 | 6284.0 | 100.00% | 683.75 | 100.00% | 1078.634 | 589.234 |
| 20000 | 113.097 | 176.84 | 12540.0 | 100.00% | 1093.513 | 100.00% | 1954.526 | 1281.19 |

## Interpretation

- The largest verified corpus in this run was `20000` synthetic memories, which is far beyond a normal active chat context window.
- Exact retrieval stayed at `100.00%` top-1 accuracy on the largest corpus.
- Bilingual natural-language retrieval stayed at `100.00%` top-1 accuracy on the largest corpus.
- Largest-corpus search latency stayed under `1954.526` ms at p95 for bilingual lookups in this environment.

## Limits

- This benchmark uses synthetic but structured memories, not messy real transcripts.
- The current write path inserts one memory at a time, so ingest speed is a conservative real-world number rather than a bulk-load maximum.
- Search is still an MVP full-scan ranking path; if the corpus grows much larger, indexing or retrieval prefilters will likely be the next optimization.

## Reproduce

```bash
python scripts/run_extreme_self_test.py \
  --sizes 1000 5000 10000 \
  --query-count 120 \
  --output-json docs/benchmarks/extreme-self-test.json \
  --output-md docs/benchmarks/extreme-self-test.md
```
