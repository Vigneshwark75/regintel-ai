from streamlit.testing.v1 import AppTest


def _app() -> AppTest:
    return AppTest.from_file("../src/ui/app.py")


def test_shows_login_form_when_not_authenticated() -> None:
    at = _app().run()

    assert not at.exception
    assert at.title[0].value == "RegIntel AI"
    assert len(at.text_input) == 2  # username + password


def test_shows_navigation_when_authenticated() -> None:
    at = _app()
    at.session_state["access_token"] = "fake-token"
    at.session_state["username"] = "compliance"

    at.run()

    assert not at.exception
    assert at.sidebar.radio[0].options == ["Ask", "Upload", "Compare", "Action Items"]
