from backend.db import Database
from backend.schemas import ScreenUnderstanding
from backend.services.memory import SessionManager


def _manager(tmp_path):
    return SessionManager(Database(str(tmp_path / "test.db")))


def test_create_and_understanding_roundtrip(tmp_path):
    sm = _manager(tmp_path)
    sid = sm.create_session()
    assert sm.get_understanding(sid) is None

    u = ScreenUnderstanding(page_type="shop", overview="a shop", key_info=["Price: $10"])
    sm.save_understanding(sid, u)

    got = sm.get_understanding(sid)
    assert got is not None
    assert got.page_type == "shop"
    assert got.key_info == ["Price: $10"]


def test_history_is_ordered(tmp_path):
    sm = _manager(tmp_path)
    sid = sm.create_session()
    sm.add_message(sid, "user", "how much?")
    sm.add_message(sid, "assistant", "ten dollars")

    history = sm.get_history(sid)
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"] == "how much?"


def test_ensure_session_creates_when_missing(tmp_path):
    sm = _manager(tmp_path)
    sid = sm.ensure_session(None)
    assert sm.ensure_session(sid) == sid
    assert sm.ensure_session("does-not-exist") != "does-not-exist"
