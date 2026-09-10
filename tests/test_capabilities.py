"""Chart & form capabilities — same analyze→ask loop, richer understandings."""
from backend.app import create_app
from backend.config import Config
from backend.schemas import Element, ScreenUnderstanding
from backend.services.document import StubDocumentProvider
from backend.services.reasoning import StubReasoningProvider
from backend.services.vision import StubVisionProvider

_IMG = "data:image/jpeg;base64,AAAA"


def _client(tmp_path, understanding):
    config = Config(
        backend="sample",
        db_path=str(tmp_path / "cap.db"),
        host="127.0.0.1",
        port=5000,
    )
    app = create_app(
        config,
        vision=StubVisionProvider(understanding),
        reasoning=StubReasoningProvider(),
        document=StubDocumentProvider(),
    )
    app.testing = True
    return app.test_client()


def _analyze(client):
    return client.post("/api/analyze-screen", json={"image": _IMG}).get_json()["session_id"]


def test_chart_trend_is_explained(tmp_path):
    understanding = ScreenUnderstanding(
        page_type="dashboard",
        overview="A sales dashboard with a revenue chart.",
        elements=[Element(type="chart", label="Monthly revenue", location="center")],
        key_info=["Revenue rose steadily from January to June, peaking in April."],
    )
    client = _client(tmp_path, understanding)
    sid = _analyze(client)

    ans = client.post("/api/ask", json={"session_id": sid, "question": "Explain the chart"}).get_json()
    assert "rose steadily" in ans["answer"].lower()
    assert "april" in ans["answer"].lower()


def test_form_fields_are_described(tmp_path):
    understanding = ScreenUnderstanding(
        page_type="signup form",
        overview="A signup form.",
        elements=[
            Element(type="form_field", label="Name", state="required"),
            Element(type="form_field", label="Email", state="focused"),
            Element(type="form_field", label="Password", state="required"),
        ],
        key_info=["3 required fields"],
        suggested_actions=["Fill in the Email field next."],
    )
    client = _client(tmp_path, understanding)
    sid = _analyze(client)

    ans = client.post(
        "/api/ask", json={"session_id": sid, "question": "Help with this form"}
    ).get_json()
    answer = ans["answer"]
    assert "3 fields" in answer
    assert "Email" in answer
    assert "next" in answer.lower()
