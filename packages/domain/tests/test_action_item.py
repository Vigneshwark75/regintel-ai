from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from regintel_domain import ActionItem, ActionItemPriority, ActionItemStatus, Citation, UserRole


def make_citation() -> Citation:
    return Citation(document_id=uuid4(), chunk_id=uuid4(), quoted_text="Some clause text")


def make_action_item(**overrides: object) -> ActionItem:
    defaults: dict[str, object] = {
        "id": uuid4(),
        "description": "Update KYC policy to reflect revised risk categorisation",
        "citations": [make_citation()],
        "owner_role": UserRole.COMPLIANCE_OFFICER,
        "priority": ActionItemPriority.HIGH,
        "created_at": datetime.now(UTC),
    }
    defaults.update(overrides)
    return ActionItem(**defaults)  # type: ignore[arg-type]


def test_action_item_requires_at_least_one_citation() -> None:
    with pytest.raises(ValidationError):
        make_action_item(citations=[])


def test_action_item_starts_open() -> None:
    item = make_action_item()

    assert item.status == ActionItemStatus.OPEN


def test_start_then_complete_transitions_status() -> None:
    item = make_action_item()

    item.start()
    assert item.status == ActionItemStatus.IN_PROGRESS

    item.complete()
    assert item.status == ActionItemStatus.DONE


def test_dismiss_requires_a_reason() -> None:
    item = make_action_item()

    with pytest.raises(ValueError, match="reason"):
        item.dismiss("   ")


def test_dismissed_item_cannot_be_restarted() -> None:
    item = make_action_item()
    item.dismiss("superseded by later circular")

    with pytest.raises(ValueError, match="dismissed"):
        item.start()


def test_dismissed_item_cannot_be_completed() -> None:
    item = make_action_item()
    item.dismiss("superseded by later circular")

    with pytest.raises(ValueError, match="dismissed"):
        item.complete()
