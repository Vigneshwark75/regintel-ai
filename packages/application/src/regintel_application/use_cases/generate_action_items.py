import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from regintel_application.ports.llm_provider import LLMMessage, LLMProvider
from regintel_application.use_cases.retrieve_chunks import RetrieveChunksUseCase
from regintel_domain import ActionItem, ActionItemPriority, UserRole

_SYSTEM_PROMPT = (
    "You generate concrete compliance action items from regulatory text. Respond with "
    "ONLY a JSON array, no other text, of objects shaped like: "
    '{"description": "...", "priority": "low"|"medium"|"high"|"critical", '
    '"citation_indices": [0, 2]}. citation_indices must reference the bracketed numbers '
    "in the provided text and must be non-empty — every action item must be directly "
    "supported by at least one cited passage. Do not propose action items that aren't "
    "grounded in the provided text."
)


@dataclass
class GenerateActionItemsUseCase:
    """Retrieves grounding text for a topic, then asks the LLM to propose action items —
    each one carrying only the specific citations the LLM says support it (not the whole
    retrieved set), so the domain layer's "an ActionItem needs >=1 citation" invariant is
    actually meaningful here rather than trivially satisfied.
    """

    retrieve_chunks: RetrieveChunksUseCase
    llm_provider: LLMProvider

    async def execute(self, topic: str, owner_role: UserRole) -> list[ActionItem]:
        citations = await self.retrieve_chunks.execute(topic, top_n=5)
        if not citations:
            return []

        context = "\n\n".join(f"[{i}] {c.quoted_text}" for i, c in enumerate(citations))
        response = await self.llm_provider.complete(
            [
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content=context),
            ]
        )

        try:
            proposals = json.loads(response.content)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM did not return valid JSON action items: {response.content!r}"
            ) from exc

        items: list[ActionItem] = []
        for proposal in proposals:
            indices = proposal.get("citation_indices") or []
            item_citations = [citations[i] for i in indices if 0 <= i < len(citations)]
            if not item_citations:
                continue  # ungrounded proposal — skip rather than raise, LLM output is imperfect

            items.append(
                ActionItem(
                    id=uuid4(),
                    description=proposal["description"],
                    citations=item_citations,
                    owner_role=owner_role,
                    priority=ActionItemPriority(proposal["priority"]),
                    created_at=datetime.now(UTC),
                )
            )

        return items
