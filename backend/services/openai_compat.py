"""OpenAI-compatible providers — for local / open models.

Any server that speaks the OpenAI Chat Completions API works here: Ollama,
vLLM, LM Studio, LocalAI (all local/open), and also OpenAI, Gemini (OpenAI
endpoint), and OpenRouter. Point SIGHTMATE at one with a base URL + model.

The model MUST be vision-capable (e.g. Qwen2.5-VL, Llama 3.2 Vision, MiniCPM-V,
moondream) since SightMate reads screenshots.
"""
from __future__ import annotations

import json

from ..core.exceptions import DocumentError, ProviderError, VisionError
from ..core.interfaces import Message
from ..core.jsonparse import extract_json
from ..core.logging import get_logger
from ..prompts import (
    CHANGE_DETECTOR_PROMPT,
    LIVE_ANSWER_PROMPT,
    REASONING_SYSTEM_PROMPT,
    VISION_SYSTEM_PROMPT,
)
from ..schemas import ScreenUnderstanding
from .monitor.change_detector import ChangeResult

log = get_logger(__name__)

_MAX_HISTORY = 12
_NULLISH = {"", "none", "null", "no", "nothing", "no change", "unchanged"}


def _image(b64: str, media_type: str) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{b64}"}}


def _history(messages: list, history: list[Message]) -> None:
    for turn in history[-_MAX_HISTORY:]:
        if turn.get("role") in ("user", "assistant") and turn.get("content"):
            messages.append({"role": turn["role"], "content": turn["content"]})


class OpenAICompatVision:
    name = "openai-vision"

    _PROMPT = (
        "Look at this screenshot and describe it for a blind user in one or two "
        "short sentences: what app or page this is, and the most important things "
        "on it (key text, prices, buttons). Plain text only, no lists, no JSON."
    )

    def __init__(self, client, model: str, max_tokens: int = 300):
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def analyze(self, image_b64: str, media_type: str = "image/jpeg") -> ScreenUnderstanding:
        text = ""
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._PROMPT},
                            _image(image_b64, media_type),
                        ],
                    },
                ],
            )
            text = (resp.choices[0].message.content or "").strip()
        except Exception:  # noqa: BLE001 - degrade gracefully rather than break the share
            log.exception("openai vision call failed")

        if not text:
            # Never block screen-sharing: succeed with a generic overview so the
            # user can immediately start asking questions (which read the screen live).
            text = "I can see your screen. Ask me anything about what's on it."
        return ScreenUnderstanding(page_type="screen", overview=text)


class OpenAICompatReasoning:
    name = "openai-reasoning"

    def __init__(self, client, model: str, max_tokens: int = 1024):
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def answer(self, question: str, understanding: ScreenUnderstanding, history: list[Message]) -> str:
        context = json.dumps(understanding.to_dict(), ensure_ascii=False)
        messages = [{"role": "system", "content": REASONING_SYSTEM_PROMPT}]
        _history(messages, history)
        messages.append({
            "role": "user",
            "content": f"Here is the current screen understanding as JSON:\n{context}\n\nQuestion: {question}",
        })
        return self._complete(messages)

    def answer_live(
        self, question: str, image_b64: str, history: list[Message], media_type: str = "image/jpeg"
    ) -> str:
        messages = [{"role": "system", "content": LIVE_ANSWER_PROMPT}]
        _history(messages, history)
        messages.append({
            "role": "user",
            "content": [{"type": "text", "text": question}, _image(image_b64, media_type)],
        })
        return self._complete(messages)

    def _complete(self, messages) -> str:
        try:
            resp = self._client.chat.completions.create(
                model=self._model, max_tokens=self._max_tokens, messages=messages
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("openai reasoning call failed")
            raise ProviderError(str(exc)) from exc
        return (resp.choices[0].message.content or "").strip()


class OpenAICompatChangeDetector:
    name = "openai-change"

    def __init__(self, client, model: str, max_tokens: int = 400):
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    def detect(self, previous_summary: str, image_b64: str, media_type: str = "image/jpeg") -> ChangeResult:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": CHANGE_DETECTOR_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": (
                                f"Previous state: {previous_summary or 'unknown'}.\n"
                                "What important thing changed, if anything? "
                                "Respond with ONLY the JSON object."
                            )},
                            _image(image_b64, media_type),
                        ],
                    },
                ],
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("openai change detector call failed")
            raise ProviderError(str(exc)) from exc
        text = resp.choices[0].message.content or ""
        try:
            data = extract_json(text)
        except ValueError:
            return ChangeResult(event=None, summary=previous_summary)
        event = data.get("event")
        if isinstance(event, str) and event.strip().lower() in _NULLISH:
            event = None
        summary = str(data.get("summary") or previous_summary)
        return ChangeResult(event=(event or None), summary=summary)


class OpenAICompatDocument:
    """Local vision models accept images (screenshots). So open the PDF in the browser and share
    the screen, and the normal live-screen path reads it page by page on scroll."""

    name = "openai-document"

    def __init__(self, *args, **kwargs):
        pass

    def analyze(self, pdf_b64: str, filename: str = "document.pdf") -> ScreenUnderstanding:
        raise DocumentError(
            "PDF file upload not supported on the local backend",
            speakable=(
                "I can read the PDF. Open the PDF in your browser, then press Enter to share "
                "your screen. I'll read it aloud, and just scroll down to go page by page."
            ),
        )
