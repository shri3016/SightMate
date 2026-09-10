"""Deterministic stub vision provider — the testing linchpin.

Returns a canned ScreenUnderstanding so the whole pipeline runs offline,
free, and deterministically in CI with no API key.
"""
from __future__ import annotations

from ...schemas import Element, ScreenUnderstanding, Section


class StubVisionProvider:
    name = "stub-vision"

    def __init__(
        self,
        understanding: ScreenUnderstanding | None = None,
        sequence: list[ScreenUnderstanding] | None = None,
    ):
        # `sequence` returns a different understanding per call (staying on the
        # last one) — used to test continuous monitoring / screen changes.
        self._sequence = list(sequence) if sequence else None
        self._index = 0
        self._understanding = understanding or _default_understanding()

    def analyze(self, image_b64: str, media_type: str = "image/jpeg") -> ScreenUnderstanding:
        if self._sequence:
            item = self._sequence[min(self._index, len(self._sequence) - 1)]
            self._index += 1
            return item
        return self._understanding


def _default_understanding() -> ScreenUnderstanding:
    return ScreenUnderstanding(
        page_type="online shopping page",
        overview=(
            "You are viewing an online shopping page for Sony wireless headphones "
            "priced at 29,990 rupees, with customer reviews below."
        ),
        sections=[
            Section(name="product", purpose="Shows the product for sale", location="center"),
            Section(name="reviews", purpose="Customer reviews", location="below the product"),
        ],
        elements=[
            Element(type="heading", label="Sony Wireless Headphones", location="top center"),
            Element(
                type="button",
                label="Add to Cart",
                location="below the product image",
                state=None,
            ),
            Element(type="button", label="Buy Now", location="below Add to Cart", state=None),
        ],
        key_info=["Price: 29,990 rupees", "Product: Sony Wireless Headphones"],
        suggested_actions=["Click Add to Cart below the product image to purchase."],
    )
