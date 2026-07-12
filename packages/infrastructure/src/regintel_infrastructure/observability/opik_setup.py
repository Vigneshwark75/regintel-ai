import os

import opik


def configure_opik_tracing(api_key: str | None, workspace: str, project_name: str) -> None:
    """Must run once at process startup, before any @opik.track-decorated function
    is called. With no API key, tracing is fully disabled (set_tracing_active(False))
    rather than left to fail per-call — the un-configured behavior otherwise still
    attempts a real network call to Comet's API for every single trace/span and logs
    a wall of "Unauthorized" warnings, which would pollute every test run and any
    local dev session without an Opik account. Configured, every @opik.track call
    elsewhere in the codebase (GroqProvider, ComplianceAgent's tool dispatch) starts
    working with zero further code changes.
    """
    if not api_key:
        opik.set_tracing_active(False)
        return

    os.environ["OPIK_API_KEY"] = api_key
    os.environ["OPIK_WORKSPACE"] = workspace
    os.environ["OPIK_PROJECT_NAME"] = project_name
    opik.set_tracing_active(True)
