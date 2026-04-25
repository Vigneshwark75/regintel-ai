from datetime import date
from uuid import uuid4

import pytest

from regintel_domain import Chunk, Document, DocumentType
from regintel_infrastructure.db.document_repository import PostgresDocumentRepository

pytestmark = pytest.mark.integration


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


async def test_save_and_get_document_round_trips(db_session) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresDocumentRepository(db_session)
    document = make_document()

    await repo.save_document(document)
    fetched = await repo.get_document(document.id)

    assert fetched == document


async def test_get_document_returns_none_when_missing(db_session) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresDocumentRepository(db_session)

    assert await repo.get_document(uuid4()) is None


async def test_chunks_are_returned_ordered_by_index(db_session) -> None:  # type: ignore[no-untyped-def]
    repo = PostgresDocumentRepository(db_session)
    document = make_document()
    await repo.save_document(document)

    chunks = [
        Chunk(id=uuid4(), document_id=document.id, content="second", chunk_index=1),
        Chunk(id=uuid4(), document_id=document.id, content="first", chunk_index=0),
    ]
    await repo.save_chunks(chunks)

    fetched = await repo.get_chunks_by_document(document.id)

    assert [chunk.content for chunk in fetched] == ["first", "second"]
