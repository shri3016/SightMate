"""Speech seams: server-side STT / TTS.

In the default "browser" voice backend, speech-to-text and text-to-speech run
in the browser via the Web Speech API and these providers are unused. Set
SIGHTMATE_VOICE=server to route audio through server-side providers instead.

A real deployment implements the two Protocols below with Whisper (STT) and
Piper / OpenAI TTS (TTS); the `/api/speech-to-text` and `/api/text-to-speech`
endpoints already call them. The Stub* providers here prove the wiring offline.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class STTProvider(Protocol):
    name: str

    def transcribe(self, audio: bytes) -> str:
        ...


@runtime_checkable
class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str) -> bytes:
        ...


class StubSTTProvider:
    """Deterministic STT for tests / offline server-voice sample mode."""

    name = "stub-stt"

    def transcribe(self, audio: bytes) -> str:
        return "transcribed speech"


class StubTTSProvider:
    """Deterministic TTS for tests / offline server-voice sample mode."""

    name = "stub-tts"

    def synthesize(self, text: str) -> bytes:
        return b"SAMPLE_AUDIO::" + text.encode("utf-8")


__all__ = ["STTProvider", "TTSProvider", "StubSTTProvider", "StubTTSProvider"]
