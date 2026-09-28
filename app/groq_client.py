"""Groq LLM client.

Wraps the Groq chat-completions API behind a single generate_response()
helper. The system prompt defines the IncidentDeepDig persona and its rules:
never invent history, and clearly separate evidence, reasoning, and
recommended next steps.
"""

import os

from groq import (
    APIConnectionError,
    APITimeoutError,
    AsyncGroq,
    Groq,
    InternalServerError,
    RateLimitError,
)

_TIMEOUT_SECONDS = 30.0
_MAX_RETRIES = 1
client = Groq(
    api_key=os.getenv("GROQ_API_KEY"), timeout=_TIMEOUT_SECONDS, max_retries=_MAX_RETRIES
)
async_client = AsyncGroq(
    api_key=os.getenv("GROQ_API_KEY"), timeout=_TIMEOUT_SECONDS, max_retries=_MAX_RETRIES
)


class GroqUnavailableError(RuntimeError):
    """A transient Groq failure after the SDK's bounded retry policy."""


_TRANSIENT_ERRORS = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)

SYSTEM_PROMPT = """
You are IncidentDeepDig, an AI production incident response assistant.

Your job is to help software engineers investigate
production incidents using historical incident memory.

Never invent historical incidents.

Clearly distinguish:
1. Evidence from previous incidents
2. Your reasoning
3. Recommended next steps
"""


def generate_response(prompt: str) -> str:
    """Send a prompt to Groq and return the assistant's text response."""
    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
    except _TRANSIENT_ERRORS as exc:
        raise GroqUnavailableError("Groq is temporarily unavailable. Please retry.") from exc
    return response.choices[0].message.content


def generate_json(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    """Send a prompt to Groq and force a JSON object response.

    The caller is responsible for parsing the returned string. Using
    response_format=json_object makes the model return strictly valid JSON.
    """
    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
    except _TRANSIENT_ERRORS as exc:
        raise GroqUnavailableError("Groq is temporarily unavailable. Please retry.") from exc
    return response.choices[0].message.content


async def generate_json_async(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    """Async JSON generation with a bounded timeout/retry and clear transient errors."""
    try:
        response = await async_client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
    except _TRANSIENT_ERRORS as exc:
        raise GroqUnavailableError(
            "Groq is temporarily unavailable. Please retry the investigation."
        ) from exc
    return response.choices[0].message.content
