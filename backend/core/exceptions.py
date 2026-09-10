"""Typed exceptions.

Each carries a `speakable` message — plain language safe to read aloud to a
visually impaired user — plus an HTTP status the API layer maps it to.
"""
from __future__ import annotations


class SightMateError(Exception):
    """Base class for all SightMate errors."""

    http_status = 500
    speakable = "Something went wrong. Please try again."

    def __init__(self, message: str | None = None, *, speakable: str | None = None):
        super().__init__(message or self.speakable)
        if speakable is not None:
            self.speakable = speakable


class NoScreenShared(SightMateError):
    """Raised when a question arrives before any screen has been analyzed."""

    http_status = 400
    speakable = "I haven't seen your screen yet. Please share your screen first."


class VisionError(SightMateError):
    """Raised when the vision model fails to read the screen."""

    http_status = 502
    speakable = "I couldn't read your screen just now. Please try again."


class DocumentError(SightMateError):
    """Raised when a document (PDF) cannot be read."""

    http_status = 502
    speakable = "I couldn't read that document. Please try a different file."


class ProviderError(SightMateError):
    """Raised when an underlying AI provider call fails."""

    http_status = 502
    speakable = "The assistant is having trouble right now. Please try again."
