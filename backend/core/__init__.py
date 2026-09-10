"""Core: interfaces, exceptions, logging — the seams the platform hangs on."""
from .exceptions import (
    DocumentError,
    NoScreenShared,
    ProviderError,
    SightMateError,
    VisionError,
)
from .logging import get_logger

__all__ = [
    "SightMateError",
    "NoScreenShared",
    "VisionError",
    "DocumentError",
    "ProviderError",
    "get_logger",
]
