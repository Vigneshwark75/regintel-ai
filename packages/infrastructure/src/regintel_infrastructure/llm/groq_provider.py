import json
from typing import Any

import opik
from groq import AsyncGroq, BadRequestError

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

    def __init__(self, client: AsyncGroq, model: str, tool_call_retries: int = 2) -> None:
        self._client = client
        self._model = model
        self._tool_call_retries = tool_call_retries

    @opik.track(type="llm", name="groq_complete")  # type: ignore[untyped-decorator]
    async def complete(
        self, messages: list[LLMMessage], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [_to_groq_message(m) for m in messages],
            # Deterministic decoding: this is a compliance assistant, not a creative
            # one, and lower temperature also measurably reduces (does not eliminate)
            # the malformed-tool-call failure mode retried below.
            "temperature": 0,
        }
        if tools is not None:
            kwargs["tools"] = tools

        response = await self._create_with_retry(kwargs)
        choice = response.choices[0].message

        tool_calls = [
            ToolCall(
                id=call.id, name=call.function.name, arguments=json.loads(call.function.arguments)
            )
            for call in (choice.tool_calls or [])
        ]

        return LLMResponse(content=choice.content or "", tool_calls=tool_calls)

    async def _create_with_retry(self, kwargs: dict[str, Any]) -> Any:
        """Groq's Llama models occasionally emit a malformed inline
        `<function=name{...}</function>` tag instead of a structured tool call —
        a sampling quirk (confirmed via a real flaky test run, not a hypothetical),
        surfaced as BadRequestError(code='tool_use_failed'). It's non-deterministic,
        so retrying the identical request usually succeeds. Any other error type
        propagates immediately — this only retries the one specific failure mode.
        """
        last_error: BadRequestError | None = None
        for _ in range(self._tool_call_retries + 1):
            try:
                return await self._client.chat.completions.create(**kwargs)
            except BadRequestError as exc:
                if "tool_use_failed" not in str(exc):
                    raise
                last_error = exc
        assert last_error is not None
        raise last_error
