"""Shared helper: pull a JSON object out of a model reply.

Tolerates code fences and surrounding prose. Raises ValueError on failure;
each provider wraps that in its own typed error.
"""
from __future__ import annotations

import json
from typing import Any


def extract_json(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"no JSON object found in model reply: {text[:200]!r}")
    return json.loads(text[start : end + 1])
