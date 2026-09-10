import pytest

from backend.app import create_app
from backend.config import Config
from backend.services.document import StubDocumentProvider
from backend.services.reasoning import StubReasoningProvider
from backend.services.vision import StubVisionProvider

_SAMPLE_IMAGE = "data:image/jpeg;base64,AAAA"
_SAMPLE_PDF = "data:application/pdf;base64,JVBERi0xLjQK"


@pytest.fixture
def client(tmp_path):
    config = Config(
        backend="sample",
        db_path=str(tmp_path / "api.db"),
        host="127.0.0.1",
        port=5000,
    )
    app = create_app(
        config,
        vision=StubVisionProvider(),
        reasoning=StubReasoningProvider(),
        document=StubDocumentProvider(),
    )
    app.testing = True
    return app.test_client()


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.get_json()
    assert body["status"] == "ok"
    assert body["vision_provider"] == "stub-vision"


def test_analyze_then_ask_flow(client):
    # 1. Analyze the screen
    res = client.post("/api/analyze-screen", json={"image": _SAMPLE_IMAGE})
    assert res.status_code == 200
    analyzed = res.get_json()
    sid = analyzed["session_id"]
    assert "headphones" in analyzed["overview_text"].lower()

    # 2. Ask a follow-up answered from the cached understanding
    res = client.post("/api/ask", json={"session_id": sid, "question": "How much does it cost?"})
    assert res.status_code == 200
    assert "29,990" in res.get_json()["answer"]

    # 3. Conversation history reflects both turns
    res = client.get(f"/api/conversation/{sid}")
    roles = [m["role"] for m in res.get_json()["messages"]]
    assert roles == ["user", "assistant"]


def test_analyze_document_then_ask_flow(client):
    # A PDF becomes the same ScreenUnderstanding shape → same Q&A loop.
    res = client.post("/api/analyze-document", json={"pdf": _SAMPLE_PDF, "filename": "inv.pdf"})
    assert res.status_code == 200
    analyzed = res.get_json()
    sid = analyzed["session_id"]
    assert "invoice" in analyzed["overview_text"].lower()

    res = client.post("/api/ask", json={"session_id": sid, "question": "What is the total?"})
    assert res.status_code == 200
    assert "1,250" in res.get_json()["answer"]


def test_analyze_document_without_pdf_is_rejected(client):
    res = client.post("/api/analyze-document", json={})
    assert res.status_code == 502
    assert "document" in res.get_json()["message"].lower()


def test_ask_with_live_image_reads_current_screen(client):
    # A question with a fresh frame re-reads the screen live — no prior
    # analyze-screen needed, and scrolling would be picked up the same way.
    res = client.post(
        "/api/ask", json={"question": "How much does it cost?", "image": _SAMPLE_IMAGE}
    )
    assert res.status_code == 200
    body = res.get_json()
    assert body["session_id"]
    assert "29,990" in body["answer"]


def test_ask_before_analyze_is_rejected(client):
    res = client.post("/api/ask", json={"session_id": "nope", "question": "what is this?"})
    assert res.status_code == 400
    assert "screen" in res.get_json()["message"].lower()


def test_analyze_without_image_is_rejected(client):
    res = client.post("/api/analyze-screen", json={})
    assert res.status_code == 502
    assert "message" in res.get_json()
