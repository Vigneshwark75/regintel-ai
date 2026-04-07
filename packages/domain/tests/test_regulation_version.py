from datetime import date
from uuid import uuid4

from regintel_domain import RegulationVersion


def make_version(**overrides: object) -> RegulationVersion:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "regulation_name": "Master Direction — KYC",
        "document_id": uuid4(),
        "version_number": 1,
        "effective_date": date(2016, 2, 25),
    }
    defaults.update(overrides)
    return RegulationVersion(**defaults)  # type: ignore[arg-type]


def test_new_version_is_current_by_default() -> None:
    version = make_version()

    assert version.is_current is True


def test_supersede_marks_version_as_not_current() -> None:
    version = make_version()

    version.supersede()

    assert version.is_current is False
