from datetime import UTC, datetime
from uuid import uuid4

import pytest

from regintel_domain import Citation, ComplianceQuery, UserRole


def make_query() -> ComplianceQuery:
    return ComplianceQuery(
        id=uuid4(),
        asked_by_role=UserRole.RISK,
        question="What changed in the latest KYC master direction amendment?",
        created_at=datetime.now(UTC),
    )


def test_new_query_has_no_answer() -> None:
    query = make_query()

    assert query.answer is None
    assert query.answered_at is None


def test_record_answer_requires_citations() -> None:
    query = make_query()

    with pytest.raises(ValueError, match="citation"):
        query.record_answer("Some answer", citations=[])


def test_record_answer_sets_answer_and_timestamp() -> None:
    query = make_query()
    citation = Citation(document_id=uuid4(), chunk_id=uuid4(), quoted_text="relevant clause")

    query.record_answer("Customer due diligence thresholds were revised.", citations=[citation])

    assert query.answer == "Customer due diligence thresholds were revised."
    assert query.citations == [citation]
    assert query.answered_at is not None
