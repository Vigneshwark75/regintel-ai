from typing import Any

RETRIEVE_CHUNKS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "retrieve_chunks",
        "description": (
            "Search ingested regulatory documents for text relevant to a query. "
            "Returns grounded passages with citations. Use this before answering any "
            "factual question about regulatory content."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The search query"}},
            "required": ["query"],
        },
    },
}

SUMMARIZE_REGULATION_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "summarize_regulation",
        "description": "Summarize a single ingested regulatory document, given its document ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "document_id": {
                    "type": "string",
                    "description": "UUID of the document to summarize",
                }
            },
            "required": ["document_id"],
        },
    },
}

COMPARE_REGULATIONS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "compare_regulations",
        "description": "Compare two ingested regulatory documents and describe what changed between them.",
        "parameters": {
            "type": "object",
            "properties": {
                "document_id_a": {"type": "string", "description": "UUID of the first document"},
                "document_id_b": {"type": "string", "description": "UUID of the second document"},
            },
            "required": ["document_id_a", "document_id_b"],
        },
    },
}

GENERATE_ACTION_ITEMS_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "generate_action_items",
        "description": (
            "Generate concrete compliance action items for a topic, grounded in retrieved "
            "regulatory text. Use this when the user asks what their team needs to do."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "The compliance topic to act on"},
                "owner_role": {
                    "type": "string",
                    "enum": ["cro", "compliance_officer", "risk", "auditor", "ops"],
                    "description": "Which team should own the generated action items",
                },
            },
            "required": ["topic", "owner_role"],
        },
    },
}

ALL_TOOLS: list[dict[str, Any]] = [
    RETRIEVE_CHUNKS_TOOL,
    SUMMARIZE_REGULATION_TOOL,
    COMPARE_REGULATIONS_TOOL,
    GENERATE_ACTION_ITEMS_TOOL,
]
