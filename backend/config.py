"""Environment-based configuration for SightMate.

Supported backends:
- "local" : any OpenAI-compatible server — Ollama / vLLM / LM Studio / OpenAI /
            Gemini / OpenRouter (OPENAI_BASE_URL + OPENAI_MODEL, vision-capable)
- "sample": deterministic stub providers 

"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional at runtime
    pass

_BACKEND_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    """Immutable runtime configuration."""

    backend: str
    db_path: str
    host: str
    port: int
    voice_backend: str = "browser"  # "browser" (Web Speech) or "server" (Whisper/TTS)
    # Local / OpenAI-compatible backend (Ollama defaults):
    openai_base_url: str = "http://localhost:11434/v1"
    openai_api_key: str = "ollama"  
    openai_model: str = "qwen3-vl:8b"  # must be VISION-capable

    @property
    def resolved_backend(self) -> str:
        """The backend actually in effect."""
        if self.backend != "auto":
            return self.backend
        return "local"


def load_config() -> Config:
    """Build a Config from the current environment."""
    return Config(
        backend=os.getenv("SIGHTMATE_BACKEND", "auto").lower(),
        db_path=os.getenv("SIGHTMATE_DB", str(_BACKEND_DIR / "sightmate.db")),
        host=os.getenv("FLASK_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_PORT", "5000")),
        voice_backend=os.getenv("SIGHTMATE_VOICE", "browser").lower(),
        openai_base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
        openai_api_key=os.getenv("OPENAI_API_KEY", "ollama"),
        openai_model=os.getenv("OPENAI_MODEL", "qwen3-vl:8b"),
    )
