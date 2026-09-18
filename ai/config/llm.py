"""The one LLM client. OpenAI-compatible, so Ollama and the HF router are the same
code path — see the Phase 5 decision note in the roadmap.

Every call is schema-constrained: the model is handed a JSON Schema with
`strict: true` and the reply is validated against the Pydantic model that produced
it. A reply that still fails validation is retried with the validation error, never
repaired with a regex. (NFR-2)
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from config.settings import settings


class GenerationError(RuntimeError):
    """The model could not be made to answer in the shape the caller asked for."""


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Pydantic's schema, tightened to what `strict: true` requires: every object
    closed, and every property required. Optional fields become nullable rather
    than absent, because a strict schema has no notion of an omitted key."""
    schema = model.model_json_schema()
    _tighten(schema)
    return schema


def _tighten(node: Any) -> None:
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            node["additionalProperties"] = False
            node["required"] = list(node["properties"])
        for key, value in node.items():
            if key != "required":
                _tighten(value)
    elif isinstance(node, list):
        for item in node:
            _tighten(item)


async def generate[T: BaseModel](
    shape: type[T],
    prompt: str,
    *,
    system: str,
    max_tokens: int = 2048,
) -> T:
    """Ask for one structured answer and hand back a validated model."""
    schema = strict_schema(shape)
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    failure = ""
    for _ in range(settings.llm_attempts):
        raw = await _complete(messages, schema, shape.__name__, max_tokens)
        try:
            return shape.model_validate_json(raw)
        except ValidationError as exc:
            failure = _first_errors(exc)
            messages = messages[:2] + [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": (
                        f"That reply did not satisfy the schema: {failure}\n"
                        "Answer again with JSON that matches the schema exactly."
                    ),
                },
            ]

    raise GenerationError(
        f"{settings.provenance} would not produce a valid {shape.__name__}: {failure}"
    )


async def _complete(
    messages: list[dict[str, str]],
    schema: dict[str, Any],
    name: str,
    max_tokens: int,
) -> str:
    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        # Extraction and scoring are not creative tasks, and a re-score should agree
        # with the score it replaces.
        "temperature": 0,
        "max_tokens": max_tokens,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": name, "strict": True, "schema": schema},
        },
    }
    if settings.llm_disable_thinking:
        payload["chat_template_kwargs"] = {"enable_thinking": False}

    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        response = await client.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        )
        if response.status_code >= 400:
            raise GenerationError(
                f"{settings.llm_host} returned {response.status_code}: {response.text[:300]}"
            )
        body = response.json()

    try:
        return body["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError) as exc:
        raise GenerationError(f"unreadable completion from {settings.llm_host}: {body}") from exc


def _first_errors(exc: ValidationError, limit: int = 3) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
        for error in exc.errors()[:limit]
    )


if __name__ == "__main__":
    import asyncio

    class Demo(BaseModel):
        skills: list[str]

    async def main() -> None:
        answer = await generate(
            Demo,
            "We are hiring a Python engineer with Kubernetes experience.",
            system="Extract the technologies named in the text.",
        )
        print(settings.provenance, "->", answer.skills)

    asyncio.run(main())
