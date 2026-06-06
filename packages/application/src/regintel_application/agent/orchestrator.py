from dataclasses import dataclass
from typing import Any, Literal, TypedDict
from uuid import UUID

from langgraph.graph import END, StateGraph

from regintel_application.agent.tools import ALL_TOOLS
from regintel_application.ports.guardrails import Guardrails
from regintel_application.ports.llm_provider import LLMMessage, LLMProvider, ToolCall
from regintel_application.use_cases.compare_regulations import CompareRegulationsUseCase
from regintel_application.use_cases.generate_action_items import GenerateActionItemsUseCase
from regintel_application.use_cases.retrieve_chunks import RetrieveChunksUseCase
from regintel_application.use_cases.summarize_regulation import SummarizeRegulationUseCase
from regintel_domain import Citation, UserRole

_INPUT_BLOCKED_MESSAGE = "I can't process that request — it was flagged by an input safety check."
_OUTPUT_BLOCKED_MESSAGE = (
    "I generated a response, but it was withheld by an output safety check. "
    "Please rephrase your question."
)

_SYSTEM_PROMPT = (
    "You are RegIntel AI, a compliance assistant for banks and NBFCs. Answer questions "
    "about regulatory documents using the tools available to you. Always call "
    "retrieve_chunks to ground factual claims in retrieved text before answering — never "
    "state a regulatory requirement you have not retrieved and verified. Use "
    "summarize_regulation to summarize one document, compare_regulations to describe what "
    "changed between two documents, and generate_action_items when the user asks what "
    "their team needs to do."
)

# Hard cap on tool-calling rounds — a safety valve against a misbehaving model looping
# forever, not a limit expected to be hit in normal use.
_MAX_TOOL_ITERATIONS = 5


class AgentState(TypedDict):
    messages: list[LLMMessage]
    citations: list[Citation]
    iterations: int


@dataclass
class ComplianceAgent:
    """LangGraph tool-calling loop over our own LLMProvider port — deliberately not
    built on langchain's model wrappers or langgraph's prebuilt ReAct agent, so vendor
    specifics (Groq today, anything else later) stay behind our own port instead of
    leaking into the orchestration layer.
    """

    llm_provider: LLMProvider
    retrieve_chunks: RetrieveChunksUseCase
    summarize_regulation: SummarizeRegulationUseCase
    compare_regulations: CompareRegulationsUseCase
    generate_action_items: GenerateActionItemsUseCase
    guardrails: Guardrails

    def __post_init__(self) -> None:
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        graph = StateGraph(AgentState)
        graph.add_node("agent", self._call_model)
        graph.add_node("tools", self._execute_tools)
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", self._should_continue, {"tools": "tools", "end": END})
        graph.add_edge("tools", "agent")
        return graph.compile()

    async def _call_model(self, state: AgentState) -> dict[str, Any]:
        response = await self.llm_provider.complete(state["messages"], tools=ALL_TOOLS)
        new_message = LLMMessage(
            role="assistant",
            content=response.content,
            tool_calls=response.tool_calls or None,
        )
        return {
            "messages": [*state["messages"], new_message],
            "iterations": state["iterations"] + 1,
        }

    def _should_continue(self, state: AgentState) -> Literal["tools", "end"]:
        if state["iterations"] >= _MAX_TOOL_ITERATIONS:
            return "end"
        last_message = state["messages"][-1]
        return "tools" if last_message.tool_calls else "end"

    async def _execute_tools(self, state: AgentState) -> dict[str, Any]:
        last_message = state["messages"][-1]
        assert last_message.tool_calls is not None

        new_messages: list[LLMMessage] = []
        new_citations = list(state["citations"])
        for call in last_message.tool_calls:
            result_text, citations = await self._dispatch(call)
            new_citations.extend(citations)
            new_messages.append(LLMMessage(role="tool", content=result_text, tool_call_id=call.id))

        return {"messages": [*state["messages"], *new_messages], "citations": new_citations}

    async def _dispatch(self, call: ToolCall) -> tuple[str, list[Citation]]:
        if call.name == "retrieve_chunks":
            citations = await self.retrieve_chunks.execute(call.arguments["query"])
            text = (
                "\n\n".join(f"[{i}] {c.quoted_text}" for i, c in enumerate(citations))
                or "No relevant chunks found."
            )
            return text, citations

        if call.name == "summarize_regulation":
            summary = await self.summarize_regulation.execute(UUID(call.arguments["document_id"]))
            return summary, []

        if call.name == "compare_regulations":
            comparison = await self.compare_regulations.execute(
                UUID(call.arguments["document_id_a"]), UUID(call.arguments["document_id_b"])
            )
            return comparison, []

        if call.name == "generate_action_items":
            items = await self.generate_action_items.execute(
                call.arguments["topic"], UserRole(call.arguments["owner_role"])
            )
            citations = [c for item in items for c in item.citations]
            text = (
                "\n".join(f"- ({item.priority.value}) {item.description}" for item in items)
                or "No grounded action items could be generated for that topic."
            )
            return text, citations

        return f"Unknown tool: {call.name}", []

    async def ask(self, question: str) -> tuple[str, list[Citation]]:
        input_check = await self.guardrails.check_input(question)
        if not input_check.allowed:
            return _INPUT_BLOCKED_MESSAGE, []

        initial_state: AgentState = {
            "messages": [
                LLMMessage(role="system", content=_SYSTEM_PROMPT),
                LLMMessage(role="user", content=question),
            ],
            "citations": [],
            "iterations": 0,
        }
        final_state: AgentState = await self._graph.ainvoke(initial_state)
        answer = final_state["messages"][-1].content

        output_check = await self.guardrails.check_output(answer)
        if not output_check.allowed:
            return _OUTPUT_BLOCKED_MESSAGE, []

        return answer, final_state["citations"]
