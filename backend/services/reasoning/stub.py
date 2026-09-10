"""Deterministic stub reasoning provider for offline tests.

Answers common intents (price, location, charts, forms, next-action) from the
understanding with simple keyword matching, so integration tests can assert
real behavior without an API key.
"""
from __future__ import annotations

from ...core.interfaces import Message
from ...schemas import ScreenUnderstanding


class StubReasoningProvider:
    name = "stub-reasoning"

    def answer(
        self,
        question: str,
        understanding: ScreenUnderstanding,
        history: list[Message],
    ) -> str:
        q = question.lower()

        if any(w in q for w in ("chart", "graph", "trend", "plot")):
            trend = _find(understanding.key_info, ("chart", "trend", "rose", "increase", "revenue"))
            if trend:
                return trend
            chart = _first_element(understanding, "chart")
            if chart:
                return f"There is a chart labelled {chart.label}."

        if any(w in q for w in ("form", "field", "fields")):
            fields = [e for e in understanding.elements if e.type == "form_field"]
            if fields:
                labels = ", ".join(e.label for e in fields)
                nxt = understanding.suggested_actions[0] if understanding.suggested_actions else ""
                return f"There are {len(fields)} fields: {labels}. {nxt}".strip()

        if any(w in q for w in ("price", "cost", "how much", "total", "due", "amount")):
            money = _find(understanding.key_info, ("price", "rupee", "total", "due", "amount", "$"))
            if money:
                return money

        if any(w in q for w in ("next", "click", "where", "buy", "do i")):
            if understanding.suggested_actions:
                return understanding.suggested_actions[0]

        return understanding.overview

    def answer_live(
        self,
        question: str,
        image_b64: str,
        history: list[Message],
        media_type: str = "image/jpeg",
    ) -> str:
        # Test double: "analyze" the stub image, then answer from it — same
        # deterministic behavior as the two-step path, but one method.
        from ..vision.stub import StubVisionProvider

        understanding = StubVisionProvider().analyze(image_b64, media_type)
        return self.answer(question, understanding, history)


def _find(items, needles):
    for item in items:
        low = item.lower()
        if any(n in low for n in needles):
            return item
    return None


def _first_element(understanding: ScreenUnderstanding, type_: str):
    for e in understanding.elements:
        if e.type == type_:
            return e
    return None
