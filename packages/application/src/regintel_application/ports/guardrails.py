from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str | None = None


class Guardrails(Protocol):
    """Input/output safety screening port. Deliberately separate from LLMProvider —
    a guardrails engine is a distinct swap point (NeMo Guardrails today, something
    else later) and, as implemented, doesn't even need an LLM of its own (see
    NeMoGuardrailsService: regex-based rails only, no generation involved)."""

    async def check_input(self, text: str) -> GuardrailResult: ...

    async def check_output(self, text: str) -> GuardrailResult: ...
