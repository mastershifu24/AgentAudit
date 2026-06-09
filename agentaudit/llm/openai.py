import os
from dataclasses import dataclass
from types import SimpleNamespace

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


@dataclass
class LLMResponse:
    """Normalized response shape for @trace_llm (provider-agnostic)."""

    text: str
    usage_metadata: SimpleNamespace


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return OpenAI(api_key=api_key)


def call_openai(
    prompt: str,
    model: str = DEFAULT_MODEL,
    *,
    system: str | None = None,
    temperature: float | None = None,
) -> LLMResponse:
    """Send a prompt to OpenAI and return a normalized response object."""
    client = _get_client()
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    kwargs: dict = {"model": model, "messages": messages}
    if temperature is not None:
        kwargs["temperature"] = temperature
    completion = client.chat.completions.create(**kwargs)
    usage = completion.usage
    return LLMResponse(
        text=completion.choices[0].message.content or "",
        usage_metadata=SimpleNamespace(
            prompt_token_count=usage.prompt_tokens if usage else None,
            candidates_token_count=usage.completion_tokens if usage else None,
        ),
    )


def call_openai_with_tools(messages: list[dict], tools: list[dict], model: str = DEFAULT_MODEL):
    """Send a multi-turn chat with tool definitions. Returns raw completion."""
    client = _get_client()
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
    )
