from uuid import uuid4

import pytest
from pydantic import ValidationError

from regintel_domain import Citation


def make_citation(**overrides: object) -> Citation:
    defaults: dict[str, object] = {
        "document_id": uuid4(),
        "chunk_id": uuid4(),
        "quoted_text": "Regulated entities shall maintain a KYC policy...",
    }
    defaults.update(overrides)
    return Citation(**defaults)  # type: ignore[arg-type]


def test_citation_rejects_empty_quoted_text() -> None:
    with pytest.raises(ValidationError):
        make_citation(quoted_text="")


def test_citation_is_immutable() -> None:
    citation = make_citation()

    with pytest.raises(ValidationError):
        citation.quoted_text = "tampered"
