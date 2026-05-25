from dataclasses import dataclass
from uuid import UUID

from regintel_application.ports.document_repository import DocumentRepository
from regintel_application.ports.llm_provider import LLMMessage, LLMProvider

_SYSTEM_PROMPT = (
    "You compare two versions of a regulatory document and describe what changed "
    "between them, focused on obligations, thresholds, and deadlines that affect a "
    "compliance team. If nothing material changed, say so plainly. Do not invent "
    "differences that are not supported by the two texts."
)


@dataclass
class CompareRegulationsUseCase:
    document_repository: DocumentRepository
    llm_provider: LLMProvider

    async def execute(self, document_id_a: UUID, document_id_b: UUID) -> str:
        chunks_a = await self.document_repository.get_chunks_by_document(document_id_a)
        chunks_b = await self.document_repository.get_chunks_by_document(document_id_b)
        if not chunks_a or not chunks_b:
            raise ValueError("both documents must have ingested chunks to compare")

        text_a = "\n\n".join(chunk.content for chunk in chunks_a)
        text_b = "\n\n".join(chunk.content for chunk in chunks_b)
        response = await self.llm_provider.complete(
            [
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(
                    role="user",
                    content=f"Document A:\n{text_a}\n\nDocument B:\n{text_b}\n\nWhat changed?",
                ),
            ]
        )
        return response.content
