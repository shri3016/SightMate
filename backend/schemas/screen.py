"""ScreenUnderstanding — the structured output the vision model produces.

This is the heart of SightMate. The vision model returns JSON matching this
shape; everything downstream (spoken overview, navigation, follow-up Q&A,
error explanation) reasons over it. Later features (PDF, charts, forms) emit
the *same* schema, so the reasoning and voice layers never change.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass
class Section:
    name: str
    purpose: str = ""
    location: str = ""


@dataclass
class Element:
    type: str
    label: str = ""
    location: str = ""
    state: str | None = None


@dataclass
class ScreenUnderstanding:
    page_type: str
    overview: str
    sections: list[Section] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    key_info: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScreenUnderstanding":
        """Build from loosely-typed JSON, tolerating missing/extra fields."""
        return cls(
            page_type=str(data.get("page_type", "unknown")),
            overview=str(data.get("overview", "")),
            sections=[
                Section(
                    name=str(s.get("name", "")),
                    purpose=str(s.get("purpose", "")),
                    location=str(s.get("location", "")),
                )
                for s in data.get("sections", [])
                if isinstance(s, dict)
            ],
            elements=[
                Element(
                    type=str(e.get("type", "other")),
                    label=str(e.get("label", "")),
                    location=str(e.get("location", "")),
                    state=(str(e["state"]) if e.get("state") else None),
                )
                for e in data.get("elements", [])
                if isinstance(e, dict)
            ],
            key_info=[str(k) for k in data.get("key_info", [])],
            suggested_actions=[str(a) for a in data.get("suggested_actions", [])],
        )
