from typing import Annotated

from fastapi import APIRouter, Depends

from api.auth import AuthenticatedUser, get_current_user
from api.dependencies import get_compliance_agent, get_generate_action_items_use_case
from api.schemas import (
    ActionItemResponse,
    AskRequest,
    AskResponse,
    GenerateActionItemsRequest,
    GenerateActionItemsResponse,
)
from regintel_application.agent.orchestrator import ComplianceAgent
from regintel_application.use_cases.generate_action_items import GenerateActionItemsUseCase

router = APIRouter(tags=["agent"])


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest,
    agent: Annotated[ComplianceAgent, Depends(get_compliance_agent)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> AskResponse:
    answer, citations = await agent.ask(request.question)
    return AskResponse(answer=answer, citations=citations)


@router.post("/action-items", response_model=GenerateActionItemsResponse)
async def generate_action_items(
    request: GenerateActionItemsRequest,
    use_case: Annotated[GenerateActionItemsUseCase, Depends(get_generate_action_items_use_case)],
    _user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> GenerateActionItemsResponse:
    items = await use_case.execute(request.topic, request.owner_role)
    return GenerateActionItemsResponse(
        action_items=[
            ActionItemResponse(
                id=item.id,
                description=item.description,
                citations=item.citations,
                owner_role=item.owner_role,
                priority=item.priority,
                status=item.status,
            )
            for item in items
        ]
    )
