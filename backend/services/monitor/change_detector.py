"""Change detection for continuous monitoring.

Asks the model directly, and conservatively, whether something important
changed — comparing a short description of the previous state to the current
screenshot — rather than diffing text (which is noisy).

The active detector lives in ``services/openai_compat.py`` as
``OpenAICompatChangeDetector``. This module holds the shared ``ChangeResult``
shape and the ``StubChangeDetector`` used by offline tests / sample mode.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChangeResult:
    event: str | None  # one spoken sentence, or None if nothing important changed
    summary: str  # short description of the current screen (the new reference state)


class StubChangeDetector:
    """Deterministic detector for tests / sample mode. Optionally scripted."""

    name = "stub-change"

    def __init__(self, script: list[ChangeResult] | None = None):
        self._script = list(script) if script else None
        self._index = 0

    def detect(
        self, previous_summary: str, image_b64: str, media_type: str = "image/jpeg"
    ) -> ChangeResult:
        if self._script:
            item = self._script[min(self._index, len(self._script) - 1)]
            self._index += 1
            return item
        return ChangeResult(event=None, summary="the screen looks unchanged")
