import json
from typing import Any

from groq import AsyncGroq

from regintel_application.ports.llm_provider import LLMMessage, LLMResponse, ToolCall


def _to_groq_message(message: LLMMessage) -> dict[str, Any]:
    payload: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.tool_call_id is not None:
        payload["tool_call_id"] = message.tool_call_id
    if message.tool_calls is not None:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
            }
            for call in message.tool_calls
        ]
    return payload


class GroqProvider:
    """Implements the application layer's LLMProvider port via Groq's free-tier,
    OpenAI-compatible API serving open-weight Llama models.
    """

    def __init__(self, client: AsyncGroq, model: str) -> None:
        self._client = client
        self._model = model

    async def complete(
        self, messages: list[LLMMessage], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [_to_groq_message(m) for m in messages],
        }
        if tools is not None:
            kwargs["tools"] = tools

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0].message

        tool_calls = [
            ToolCall(
                id=call.id, name=call.function.name, arguments=json.loads(call.function.arguments)
            )
            for call in (choice.tool_calls or [])
        ]

        return LLMResponse(content=choice.content or "", tool_calls=tool_calls)
