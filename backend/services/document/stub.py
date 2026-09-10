"""Deterministic stub document provider for offline tests / sample mode."""
from __future__ import annotations

from ...schemas import Element, ScreenUnderstanding, Section


class StubDocumentProvider:
    name = "stub-document"

    def __init__(self, understanding: ScreenUnderstanding | None = None):
        self._understanding = understanding or _default()

    def analyze(self, pdf_b64: str, filename: str = "document.pdf") -> ScreenUnderstanding:
        return self._understanding


def _default() -> ScreenUnderstanding:
    return ScreenUnderstanding(
        page_type="invoice",
        overview=(
            "This is an invoice from Acme Corporation dated March 2026, "
            "with a total amount due of 1,250 dollars."
        ),
        sections=[
            Section(name="Header", purpose="Company and invoice number", location="page 1 top"),
            Section(name="Line items", purpose="Products and prices", location="page 1 middle"),
            Section(name="Total", purpose="Amount due", location="page 1 bottom"),
        ],
        elements=[
            Element(type="heading", label="Invoice #A-1042", location="page 1 top"),
            Element(type="table", label="Line items table", location="page 1 middle"),
        ],
        key_info=["Total due: 1,250 dollars", "Due date: 2026-03-31", "Vendor: Acme Corporation"],
        suggested_actions=["Ask me for the total, the due date, or the line items."],
    )
