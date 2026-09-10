"""Continuous monitoring via the AI change-detector."""
from backend.app import create_app
from backend.config import Config
from backend.services.monitor import ChangeResult, StubChangeDetector

_IMG = "data:image/jpeg;base64,AAAA"


def _config(tmp_path, name):
    return Config(
        backend="sample",
        db_path=str(tmp_path / f"{name}.db"),
        host="127.0.0.1",
        port=5000,
    )


def test_monitor_announces_a_real_change(tmp_path):
    # tick 1 → nothing important; tick 2 → an event
    script = [
        ChangeResult(event=None, summary="a file is downloading"),
        ChangeResult(event="Your download has finished.", summary="download complete"),
    ]
    app = create_app(_config(tmp_path, "mon"), change_detector=StubChangeDetector(script))
    app.testing = True
    client = app.test_client()

    sid = client.post("/api/analyze-screen", json={"image": _IMG}).get_json()["session_id"]

    assert client.post("/api/monitor", json={"session_id": sid, "image": _IMG}).get_json()[
        "events"
    ] == []

    events = client.post("/api/monitor", json={"session_id": sid, "image": _IMG}).get_json()[
        "events"
    ]
    assert any("finished" in e.lower() for e in events)


def test_monitor_stays_quiet_when_nothing_changes(tmp_path):
    # Default stub detector never reports an event
    app = create_app(_config(tmp_path, "quiet"))  # default StubChangeDetector
    app.testing = True
    client = app.test_client()
    sid = client.post("/api/analyze-screen", json={"image": _IMG}).get_json()["session_id"]
    for _ in range(3):
        assert client.post("/api/monitor", json={"session_id": sid, "image": _IMG}).get_json()[
            "events"
        ] == []


def test_monitor_without_session_is_rejected(tmp_path):
    app = create_app(_config(tmp_path, "nosess"))
    app.testing = True
    res = app.test_client().post("/api/monitor", json={"image": _IMG})
    assert res.status_code == 400
