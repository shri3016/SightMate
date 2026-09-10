"""API routes: the SightMate spine (analyze → ask → converse), monitor, and voice."""
from __future__ import annotations

import base64

from flask import Blueprint, current_app, jsonify, request

from ..core.exceptions import DocumentError, NoScreenShared, SightMateError, VisionError
from ..schemas import ScreenUnderstanding

api_bp = Blueprint("api", __name__)


def _services():
    return current_app.extensions["sightmate"]


def _strip_data_url(image: str) -> tuple[str, str]:
    """Accept a raw base64 string or a data URL; return (b64, media_type)."""
    media_type = "image/jpeg"
    if image.startswith("data:"):
        header, _, b64 = image.partition(",")
        if ";" in header and ":" in header:
            media_type = header[header.index(":") + 1 : header.index(";")] or media_type
        return b64, media_type
    return image, media_type


@api_bp.errorhandler(SightMateError)
def _handle_sightmate_error(exc: SightMateError):
    return jsonify({"error": type(exc).__name__, "message": exc.speakable}), exc.http_status


@api_bp.get("/health")
def health():
    svc = _services()
    config = svc["config"]
    backend = config.resolved_backend
    model = config.openai_model if backend == "local" else "sample"
    return jsonify(
        {
            "status": "ok",
            "backend": backend,
            "model": model,
            "vision_provider": getattr(svc["vision"], "name", "unknown"),
            "reasoning_provider": getattr(svc["reasoning"], "name", "unknown"),
            "document_provider": getattr(svc["document"], "name", "unknown"),
            "voice_backend": config.voice_backend,
            "sample_mode": backend == "sample",
        }
    )


@api_bp.post("/analyze-screen")
def analyze_screen():
    data = request.get_json(silent=True) or {}
    image = data.get("image")
    if not image:
        raise VisionError("no image provided", speakable="I didn't receive a screen image.")

    b64, media_type = _strip_data_url(image)
    svc = _services()
    sessions = svc["sessions"]

    session_id = sessions.ensure_session(data.get("session_id"))
    understanding = svc["vision"].analyze(b64, media_type)
    sessions.save_understanding(session_id, understanding)

    return jsonify(
        {
            "session_id": session_id,
            "understanding": understanding.to_dict(),
            "overview_text": understanding.overview,
        }
    )


@api_bp.post("/analyze-document")
def analyze_document():
    data = request.get_json(silent=True) or {}
    pdf = data.get("pdf")
    if not pdf:
        raise DocumentError("no pdf provided", speakable="I didn't receive a document.")

    b64, _ = _strip_data_url(pdf)
    svc = _services()
    sessions = svc["sessions"]

    session_id = sessions.ensure_session(data.get("session_id"))
    understanding = svc["document"].analyze(b64, data.get("filename", "document.pdf"))
    sessions.save_understanding(session_id, understanding)

    return jsonify(
        {
            "session_id": session_id,
            "understanding": understanding.to_dict(),
            "overview_text": understanding.overview,
        }
    )


@api_bp.post("/ask")
def ask():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    session_id = data.get("session_id")
    image = data.get("image")

    if not question:
        raise SightMateError(
            "empty question", speakable="I didn't catch a question. Please try again."
        )

    svc = _services()
    sessions = svc["sessions"]

    if image:
        # LIVE screen: answer straight from the CURRENT frame in a SINGLE model
        # call (image + question). Fast, and scrolling is handled automatically.
        session_id = sessions.ensure_session(session_id)
        b64, media_type = _strip_data_url(image)
        history = sessions.get_history(session_id)
        answer = svc["reasoning"].answer_live(question, b64, history, media_type)
    else:
        # No live frame (e.g. a PDF session): answer from the cached understanding.
        if not session_id:
            raise NoScreenShared()
        understanding = sessions.get_understanding(session_id)
        if understanding is None:
            raise NoScreenShared()
        history = sessions.get_history(session_id)
        answer = svc["reasoning"].answer(question, understanding, history)

    sessions.add_message(session_id, "user", question)
    sessions.add_message(session_id, "assistant", answer)

    return jsonify({"answer": answer, "session_id": session_id})


@api_bp.post("/monitor")
def monitor():
    """Continuous monitoring: ask the model if something important just changed.

    Note: this only sees what is inside the shared surface. Browser download
    popups and OS notifications that sit outside the shared tab/window cannot be
    detected — share the whole screen to catch more.
    """
    data = request.get_json(silent=True) or {}
    image = data.get("image")
    session_id = data.get("session_id")
    if not image:
        raise VisionError("no image provided", speakable="I didn't receive a screen image.")
    if not session_id:
        raise NoScreenShared()

    b64, media_type = _strip_data_url(image)
    svc = _services()
    sessions = svc["sessions"]

    previous = sessions.get_understanding(session_id)
    prev_summary = previous.overview if previous else ""

    result = svc["change_detector"].detect(prev_summary, b64, media_type)

    # Store the new state as the reference for the next tick (so a change isn't
    # re-announced every few seconds).
    sessions.save_understanding(
        session_id, ScreenUnderstanding(page_type="(live)", overview=result.summary)
    )

    events = [result.event] if result.event else []
    return jsonify({"events": events})


@api_bp.get("/conversation/<session_id>")
def conversation(session_id: str):
    sessions = _services()["sessions"]
    return jsonify({"session_id": session_id, "messages": sessions.get_history(session_id)})


# --- Voice seams ---
# Default browser backend: voice runs client-side (Web Speech), so these return
# "handled_client_side". With SIGHTMATE_VOICE=server, they route through the
# configured STT/TTS providers.


@api_bp.post("/speech-to-text")
def speech_to_text():
    stt = _services().get("stt")
    if stt is None:
        return jsonify({"status": "handled_client_side"})

    data = request.get_json(silent=True) or {}
    audio_b64 = data.get("audio")
    if not audio_b64:
        raise SightMateError("no audio", speakable="I didn't receive any audio.")
    text = stt.transcribe(base64.b64decode(audio_b64))
    return jsonify({"status": "ok", "text": text, "provider": stt.name})


@api_bp.post("/text-to-speech")
def text_to_speech():
    tts = _services().get("tts")
    if tts is None:
        return jsonify({"status": "handled_client_side"})

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        raise SightMateError("no text", speakable="There was nothing to speak.")
    audio = tts.synthesize(text)
    return jsonify(
        {
            "status": "ok",
            "audio_base64": base64.b64encode(audio).decode("ascii"),
            "provider": tts.name,
        }
    )
