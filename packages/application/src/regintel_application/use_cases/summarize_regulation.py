from dataclasses import dataclass
from uuid import UUID

from regintel_application.ports.document_repository import DocumentRepository
from regintel_application.ports.llm_provider import LLMMessage, LLMProvider

_SYSTEM_PROMPT = (
    "You are a regulatory compliance assistant. Summarize the following regulatory "
    "document concisely and accurately, preserving key obligations, thresholds, and "
    "deadlines. Do not invent details that are not present in the text."
)


@dataclass
class SummarizeRegulationUseCase:
    document_repository: DocumentRepository
    llm_provider: LLMProvider

    async def execute(self, document_id: UUID) -> str:
        chunks = await self.document_repository.get_chunks_by_document(document_id)
        if not chunks:
            raise ValueError(f"no ingested chunks found for document {document_id}")

        combined_text = "\n\n".join(chunk.content for chunk in chunks)
        response = await self.llm_provider.complete(
            [
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content=combined_text),
            ]
        )
        return response.content
