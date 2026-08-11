"""Retrieval gate: decide whether a turn needs long-term memory.

Before touching the memory stores, a cheap model answers one narrow question:
does this user message need stored memories? The gate is deliberately fail-open:
if the model call or JSON parsing fails, Waku retrieves rather than losing a
memory that may matter.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import anthropic

Observer = Callable[[str, dict[str, Any]], None]

GATE_PROMPT = """\
You are a retrieval gate for a personal assistant's long-term memory.
Given the user's message, decide if answering well requires the user's stored
memories (facts about people, projects, preferences, or past events).

Reply with ONLY this JSON as one single-line object and nothing else. Do not
include markdown, explanations, or newlines. JSON schema:
{{"retrieve": true/false, "query": "<search keywords if true, else empty>",
"reason": "<5 words>"}}.

General knowledge, math, small talk, or self-contained requests -> false.
Anything referencing the user's life, people, plans, or history -> true.

User message: {message}"""


def _parse_gate_json(text: str, fallback_query: str) -> tuple[bool, str, str]:
    if "{" not in text:
        return True, fallback_query, "gate returned no JSON - failing open"
    decision = json.loads(text[text.index("{") : text.rindex("}") + 1])
    return (
        bool(decision.get("retrieve")),
        decision.get("query", fallback_query),
        decision.get("reason", ""),
    )


def should_retrieve(
    client: anthropic.Anthropic,
    small_model: str,
    message: str,
    notify: Observer | None = None,
) -> tuple[bool, str, str]:
    """Return (retrieve?, search_query, reason)."""
    try:
        kwargs = {
            "model": small_model,
            # Reasoning models may spend tokens before producing the JSON.
            "max_tokens": 600,
            "messages": [{"role": "user", "content": GATE_PROMPT.format(message=message)}],
        }
        if hasattr(client.messages, "stream"):
            try:
                chunks: list[str] = []
                with client.messages.stream(**kwargs) as stream:
                    for delta in stream.text_stream:
                        chunks.append(delta)
                        if notify:
                            notify("gate_text", {"delta": delta})
                return _parse_gate_json("".join(chunks), message)
            except Exception as exc:
                if notify:
                    notify("stream_fallback", {"reason": f"gate {type(exc).__name__}: {exc}"})
                pass  # fall back to the blocking path below

        response = client.messages.create(**kwargs)
        text = "".join(b.text for b in response.content if b.type == "text")
        return _parse_gate_json(text, message)
    except Exception as exc:
        return True, message, f"gate failed open ({type(exc).__name__})"
