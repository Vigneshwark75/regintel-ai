import pytest

from regintel_application.ports.llm_provider import LLMMessage
from regintel_infrastructure.llm.groq_provider import GroqProvider

pytestmark = pytest.mark.integration

_WEATHER_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }
]


async def test_complete_returns_plain_text(groq_provider: GroqProvider) -> None:
    response = await groq_provider.complete(
        [LLMMessage(role="user", content="Reply with exactly the word: pong")]
    )

    assert "pong" in response.content.lower()
    assert response.tool_calls == []


async def test_complete_invokes_the_relevant_tool(groq_provider: GroqProvider) -> None:
    response = await groq_provider.complete(
        [
            LLMMessage(
                role="user",
                content="What is the weather in Mumbai right now? Use the get_weather tool.",
            )
        ],
        tools=_WEATHER_TOOL,
    )

    assert len(response.tool_calls) == 1
    call = response.tool_calls[0]
    assert call.name == "get_weather"
    assert "mumbai" in call.arguments["city"].lower()


async def test_complete_replays_prior_tool_call_in_history(groq_provider: GroqProvider) -> None:
    first = await groq_provider.complete(
        [LLMMessage(role="user", content="What is the weather in Delhi? Use the tool.")],
        tools=_WEATHER_TOOL,
    )
    assert len(first.tool_calls) == 1
    call = first.tool_calls[0]

    second = await groq_provider.complete(
        [
            LLMMessage(role="user", content="What is the weather in Delhi? Use the tool."),
            LLMMessage(role="assistant", content="", tool_calls=[call]),
            LLMMessage(role="tool", content="Sunny, 32C", tool_call_id=call.id),
        ]
    )

    assert "32" in second.content or "sunny" in second.content.lower()
