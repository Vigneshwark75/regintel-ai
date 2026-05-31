from datetime import date
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from api.auth import AuthenticatedUser, get_current_user, require_roles
from api.dependencies import (
    get_compare_regulations_use_case,
    get_ingest_document_use_case,
    get_summarize_regulation_use_case,
)
from api.schemas import CompareRequest, CompareResponse, DocumentUploadResponse, SummarizeResponse
from regintel_application.use_cases.compare_regulations import CompareRegulationsUseCase
from regintel_application.use_cases.ingest_document import IngestDocumentUseCase
from regintel_application.use_cases.summarize_regulation import SummarizeRegulationUseCase
from regintel_domain import Document, DocumentType, UserRole
from regintel_infrastructure.ingestion import parse_and_chunk

router = APIRouter(prefix="/documents", tags=["documents"])

# Uploading is a compliance-content-management action, not a read; scoped to the
# roles that actually manage what regulatory documents the platform knows about.
_require_uploader = require_roles(UserRole.CRO, UserRole.COMPLIANCE_OFFICER)


@router.post("", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
    document_type: Annotated[DocumentType, Form()],
    reference_number: Annotated[str, Form()],
    issued_date: Annotated[date, Form()],
    ingest: Annotated[IngestDocumentUseCase, Depends(get_ingest_document_use_case)],
    _user: Annotated[AuthenticatedUser, Depends(_require_uploader)],
) -> DocumentUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="file must have a name")

    content = await file.read()
    document = Document(
        id=uuid4(),
        title=title,
        document_type=document_type,
        reference_number=reference_number,
        issued_date=issued_date,
    )
    try:
        chunks = parse_and_chunk(file.filename, content, document.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await ingest.execute(document, chunks)
    return DocumentUploadResponse(document_id=document.id, chunk_count=len(chunks))


@router.post("/{document_id}/summarize", response_model=SummarizeResponse)
async def summarize_document(
    document_id: UUID,
    summarize: Annotated[SummarizeRegulationUseCase, Depends(get_summarize_regulation_use_case)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> SummarizeResponse:
    try:
        summary = await summarize.execute(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return SummarizeResponse(summary=summary)


@router.post("/compare", response_model=CompareResponse)
async def compare_documents(
    request: CompareRequest,
    compare: Annotated[CompareRegulationsUseCase, Depends(get_compare_regulations_use_case)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> CompareResponse:
    try:
        comparison = await compare.execute(request.document_id_a, request.document_id_b)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CompareResponse(comparison=comparison)
