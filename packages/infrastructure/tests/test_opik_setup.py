import os

import opik

from regintel_infrastructure.observability.opik_setup import configure_opik_tracing


def test_configure_with_no_api_key_disables_tracing() -> None:
    configure_opik_tracing(None, workspace="default", project_name="regintel-ai")

    assert opik.is_tracing_active() is False


def test_configure_with_an_api_key_enables_tracing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("OPIK_API_KEY", raising=False)

    configure_opik_tracing(
        "fake-key-for-testing", workspace="my-workspace", project_name="my-project"
    )

    assert opik.is_tracing_active() is True
    assert os.environ["OPIK_API_KEY"] == "fake-key-for-testing"
    assert os.environ["OPIK_WORKSPACE"] == "my-workspace"
    assert os.environ["OPIK_PROJECT_NAME"] == "my-project"

    # Restore for other tests in the same process — tracing_active is a process-global
    # singleton, and reset_tracing_to_config_default() wouldn't necessarily give False
    # (that depends on OpikConfig.track_disable, unrelated to api_key presence).
    opik.set_tracing_active(False)
    monkeypatch.delenv("OPIK_API_KEY", raising=False)
