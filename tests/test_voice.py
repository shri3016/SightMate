"""Server-side voice seam: browser default vs server providers."""
import base64

from backend.app import create_app
from backend.config import Config


def _app(tmp_path, voice_backend):
    config = Config(
        backend="sample",
        db_path=str(tmp_path / f"voice-{voice_backend}.db"),
        host="127.0.0.1",
        port=5000,
        voice_backend=voice_backend,
    )
    app = create_app(config)
    app.testing = True
    return app


def test_browser_backend_handles_voice_client_side(tmp_path):
    client = _app(tmp_path, "browser").test_client()
    assert client.post("/api/text-to-speech", json={"text": "hi"}).get_json()["status"] == (
        "handled_client_side"
    )
    assert client.post("/api/speech-to-text", json={"audio": ""}).get_json()["status"] == (
        "handled_client_side"
    )
    assert client.get("/api/health").get_json()["voice_backend"] == "browser"


def test_server_backend_synthesizes_and_transcribes(tmp_path):
    client = _app(tmp_path, "server").test_client()

    tts = client.post("/api/text-to-speech", json={"text": "hello"}).get_json()
    assert tts["status"] == "ok"
    assert base64.b64decode(tts["audio_base64"]) == b"SAMPLE_AUDIO::hello"
    assert tts["provider"] == "stub-tts"

    audio = base64.b64encode(b"anything").decode("ascii")
    stt = client.post("/api/speech-to-text", json={"audio": audio}).get_json()
    assert stt["status"] == "ok"
    assert stt["text"] == "transcribed speech"
