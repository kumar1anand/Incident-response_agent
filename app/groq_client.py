"""Groq LLM client.

Wraps the Groq chat-completions API behind a single generate_response()
helper. The system prompt defines the IncidentIQ persona and its rules:
never invent history, and clearly separate evidence, reasoning, and
recommended next steps.
"""

import os

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are IncidentIQ, an AI production incident response assistant.

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
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content


def generate_json(prompt: str, system: str = SYSTEM_PROMPT) -> str:
    """Send a prompt to Groq and force a JSON object response.

    The caller is responsible for parsing the returned string. Using
    response_format=json_object makes the model return strictly valid JSON.
    """
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content
