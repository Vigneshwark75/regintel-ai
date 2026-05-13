from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None  # set on role="tool" messages, replying to a ToolCall.id
    tool_calls: list[ToolCall] | None = None  # set on role="assistant" messages that called tools


@dataclass(frozen=True)
class LLMResponse:
    content: str
    tool_calls: list[ToolCall]


class LLMProvider(Protocol):
    """Chat completion port, with tool-calling support built in from the start —
    Phase 6's LangGraph agent loop calls this directly rather than going through
    LangChain's own model wrappers, so vendor specifics stay behind this port
    instead of leaking into the agent orchestration code.
    """

    async def complete(
        self, messages: list[LLMMessage], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse: ...
