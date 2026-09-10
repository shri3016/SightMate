"""Provider interfaces — the extension seams.

Adding a new vision/reasoning/STT/TTS backend means implementing one of these
Protocols and wiring it in. No caller changes. (Open/Closed principle.)
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..schemas import ScreenUnderstanding

# A single conversation turn: {"role": "user"|"assistant", "content": str}
Message = dict[str, str]


@runtime_checkable
class VisionProvider(Protocol):
    name: str

    def analyze(self, image_b64: str, media_type: str = "image/jpeg") -> ScreenUnderstanding:
        """Turn a screenshot into a structured ScreenUnderstanding."""
        ...


@runtime_checkable
class DocumentProvider(Protocol):
    name: str

    def analyze(self, pdf_b64: str, filename: str = "document.pdf") -> ScreenUnderstanding:
        """Turn a PDF into the same ScreenUnderstanding shape a screen produces."""
        ...


@runtime_checkable
class ReasoningProvider(Protocol):
    name: str

    def answer(
        self,
        question: str,
        understanding: ScreenUnderstanding,
        history: list[Message],
    ) -> str:
        """Answer a question from the cached understanding + conversation history."""
        ...
