"""Flask application factory.

Wires the config, database, and providers together and registers the routes.
Providers can be injected (tests pass stubs); otherwise they're built from
config. The AI brain is any OpenAI-compatible server (Ollama / vLLM / LM Studio /
OpenAI / Gemini / OpenRouter). 
"""
from __future__ import annotations

from pathlib import Path

from flask import Flask

from .config import Config, load_config
from .core.logging import get_logger
from .db import Database
from .routes import register_routes
from .services.document import StubDocumentProvider
from .services.memory import SessionManager
from .services.monitor import StubChangeDetector
from .services.reasoning import StubReasoningProvider
from .services.speech import StubSTTProvider, StubTTSProvider
from .services.vision import StubVisionProvider

log = get_logger(__name__)

_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"


def create_app(
    config: Config | None = None,
    *,
    vision=None,
    reasoning=None,
    document=None,
    change_detector=None,
    stt=None,
    tts=None,
    session_manager=None,
) -> Flask:
    config = config or load_config()

    app = Flask(
        __name__,
        template_folder=str(_FRONTEND / "templates"),
        static_folder=str(_FRONTEND / "static"),
    )

    db = Database(config.db_path)

    if vision is None or reasoning is None or document is None or change_detector is None:
        vision, reasoning, document, change_detector = _build_providers(
            config, vision, reasoning, document, change_detector
        )

    if stt is None and tts is None:
        stt, tts = _build_voice(config)

    session_manager = session_manager or SessionManager(db)

    app.extensions["sightmate"] = {
        "config": config,
        "vision": vision,
        "reasoning": reasoning,
        "document": document,
        "change_detector": change_detector,
        "stt": stt,
        "tts": tts,
        "sessions": session_manager,
    }

    register_routes(app)
    return app


def _build_providers(config: Config, vision, reasoning, document, change_detector):
    backend = config.resolved_backend

    if backend == "sample":
        log.warning(
            "No model configured — running in SAMPLE mode with stub providers. "
            "Set SIGHTMATE_BACKEND=local with OPENAI_BASE_URL/OPENAI_MODEL (e.g. Ollama) "
            "in .env for real screen understanding."
        )
        return (
            vision or StubVisionProvider(),
            reasoning or StubReasoningProvider(),
            document or StubDocumentProvider(),
            change_detector or StubChangeDetector(),
        )

    if backend == "local":
        # Any OpenAI-compatible server: Ollama / vLLM / LM Studio / OpenAI / Gemini.
        from openai import OpenAI

        from .services.openai_compat import (
            OpenAICompatChangeDetector,
            OpenAICompatDocument,
            OpenAICompatReasoning,
            OpenAICompatVision,
        )

        client = OpenAI(base_url=config.openai_base_url, api_key=config.openai_api_key)
        model = config.openai_model
        log.info("Using local/OpenAI-compatible backend (url=%s, model=%s)", config.openai_base_url, model)
        return (
            vision or OpenAICompatVision(client, model),
            reasoning or OpenAICompatReasoning(client, model),
            document or OpenAICompatDocument(),
            change_detector or OpenAICompatChangeDetector(client, model),
        )

    raise ValueError(
        f"Unsupported backend {backend!r}. Set SIGHTMATE_BACKEND=local (an "
        "OpenAI-compatible server such as Ollama, vLLM, LM Studio, or a hosted "
        "OpenAI/Gemini/OpenRouter endpoint) or 'sample'."
    )


def _build_voice(config: Config):
    """Server-side STT/TTS providers, or (None, None) for the browser backend."""
    if config.voice_backend == "server":
        # Real deployments swap these stubs for Whisper (STT) + Piper/OpenAI (TTS),
        # which implement the same two-method Protocols.
        log.info("Voice backend: server (STT/TTS via providers)")
        return StubSTTProvider(), StubTTSProvider()
    return None, None  # browser Web Speech handles voice client-side


def main() -> None:
    config = load_config()
    app = create_app(config)
    log.info(
        "SightMate running on http://%s:%s (backend=%s, model=%s)",
        config.host,
        config.port,
        config.resolved_backend,
        config.openai_model,
    )
    app.run(host=config.host, port=config.port, debug=True)


if __name__ == "__main__":
    main()
