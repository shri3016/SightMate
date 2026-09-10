from backend.schemas import ScreenUnderstanding


def test_roundtrip_to_and_from_dict():
    u = ScreenUnderstanding(
        page_type="login form",
        overview="A login page with email and password fields.",
        key_info=["Two required fields"],
    )
    restored = ScreenUnderstanding.from_dict(u.to_dict())
    assert restored.page_type == "login form"
    assert restored.overview.startswith("A login page")
    assert restored.key_info == ["Two required fields"]


def test_from_dict_tolerates_missing_and_extra_fields():
    u = ScreenUnderstanding.from_dict({"overview": "hi", "unexpected": 123})
    assert u.page_type == "unknown"
    assert u.overview == "hi"
    assert u.sections == []
    assert u.elements == []


def test_from_dict_parses_nested_elements():
    u = ScreenUnderstanding.from_dict(
        {
            "page_type": "shop",
            "overview": "o",
            "elements": [{"type": "button", "label": "Buy", "location": "top", "state": "disabled"}],
        }
    )
    assert u.elements[0].label == "Buy"
    assert u.elements[0].state == "disabled"
