from __future__ import annotations

import math
import re
from datetime import datetime, timezone


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def normalize_for_match(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def tokenize(text: str) -> set[str]:
    lowered = normalize_for_match(text)
    latin = re.findall(r"[a-z0-9_./:+-]+", lowered)
    cjk = re.findall(r"[\u4e00-\u9fff]", lowered)
    bigrams = ["".join(cjk[index : index + 2]) for index in range(len(cjk) - 1)]
    return set(latin + cjk + bigrams)


def similarity(a: str, b: str) -> float:
    left = tokenize(a)
    right = tokenize(b)
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def has_significant_match(query: str, haystack: str) -> bool:
    query_norm = normalize_for_match(query)
    hay_norm = normalize_for_match(haystack)
    if query_norm and query_norm in hay_norm:
        return True

    query_tokens = tokenize(query)
    latin_tokens = [token for token in query_tokens if any(ch.isalnum() and ch.isascii() for ch in token) and len(token) >= 3]
    if latin_tokens:
        return any(token in hay_norm for token in latin_tokens)

    cjk_tokens = [token for token in query_tokens if len(token) >= 2 and not any(ch.isascii() for ch in token)]
    return any(token in hay_norm for token in cjk_tokens)


def recency_boost(iso_value: str) -> float:
    try:
        age_seconds = max(
            1.0,
            (datetime.now(timezone.utc) - datetime.fromisoformat(iso_value)).total_seconds(),
        )
    except ValueError:
        return 0.0
    return max(0.0, 2.0 - math.log10(age_seconds / 3600 + 1.0))


def score_text(
    query: str,
    haystack: str,
    *,
    importance: int = 3,
    pinned: bool = False,
    created_at: str = "",
    project_match: bool = False,
) -> float:
    query_norm = normalize_for_match(query)
    hay_norm = normalize_for_match(haystack)
    query_tokens = tokenize(query)
    hay_tokens = tokenize(haystack)

    score = 0.0
    overlap = len(query_tokens & hay_tokens)
    score += overlap * 2.0

    if query_norm and query_norm in hay_norm:
        score += 6.0

    for token in query_tokens:
        if len(token) >= 2 and token in hay_norm:
            score += 0.8

    score += float(importance) * 0.6
    if pinned:
        score += 2.0
    if project_match:
        score += 2.0
    if created_at:
        score += recency_boost(created_at)
    return score
