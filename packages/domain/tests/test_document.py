from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from regintel_domain import Chunk, Document, DocumentType


def make_document(**overrides: object) -> Document:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "title": "Master Direction on KYC",
        "document_type": DocumentType.MASTER_DIRECTION,
        "reference_number": "RBI/DBR/2016-17/18",
        "issued_date": date(2016, 2, 25),
    }
    defaults.update(overrides)
    return Document(**defaults)  # type: ignore[arg-type]


def test_document_creation_succeeds_with_valid_fields() -> None:
    document = make_document()

    assert document.document_type == DocumentType.MASTER_DIRECTION


def test_document_rejects_empty_title() -> None:
    with pytest.raises(ValidationError):
        make_document(title="")


def test_chunk_rejects_negative_index() -> None:
    with pytest.raises(ValidationError):
        Chunk(id=uuid4(), document_id=uuid4(), content="text", chunk_index=-1)


def test_chunk_rejects_zero_page_number() -> None:
    with pytest.raises(ValidationError):
        Chunk(id=uuid4(), document_id=uuid4(), content="text", chunk_index=0, page_number=0)
