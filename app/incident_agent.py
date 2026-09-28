"""IncidentIQ agent: combines Hindsight memory with Groq reasoning.

Flow:
    incident text
        -> recall() relevant historical memories from Hindsight
        -> build a prompt with the new incident + historical context
        -> generate an analysis via Groq (text or structured JSON)
        -> return analysis

Two entry points:
    investigate_incident(text)             -> raw markdown analysis (CLI)
    investigate_incident_structured(text)  -> structured dict (API / UI)
"""

import json

from app.groq_client import generate_response, generate_json
from app.memory import hindsight, BANK_ID


def _recall_memories(incident: str):
    """Recall relevant memories and return (memory_texts, joined_context)."""
    result = hindsight.recall(bank_id=BANK_ID, query=incident)
    memories = [memory.text for memory in result.results]
    context = "\n\n".join(memories) if memories else "(no relevant memories found)"
    return memories, context


def investigate_incident(incident: str) -> str:
    """Analyze a new incident using historical memory + the LLM (raw text)."""
    _, historical_context = _recall_memories(incident)

    prompt = f"""
A new production incident has occurred.

NEW INCIDENT:
{incident}


HISTORICAL INCIDENT MEMORY:
{historical_context}


Analyze the new incident.

Provide:

1. Similar historical incidents
2. Previously observed root causes
3. Previously successful resolutions
4. Your recommended investigation steps
5. A warning if the historical evidence is insufficient
"""
    return generate_response(prompt)


STRUCTURED_SYSTEM_PROMPT = """
You are IncidentIQ, an AI production incident response assistant.

You help software engineers investigate production incidents using
historical incident memory retrieved from a memory system.

Rules:
- Never invent historical incidents. Only reference incidents that appear
  in the provided HISTORICAL INCIDENT MEMORY.
- Base similarity and root causes strictly on the provided memory.
- If memory is disabled, reason ONLY from the current incident and return an
  empty similar_incidents list with LOW confidence.
- Always respond with a single valid JSON object, no prose outside it.
"""


def investigate_incident_structured(incident: str, memory_enabled: bool = True) -> dict:
    """Analyze an incident and return structured data for the UI.

    Args:
        incident: the incident description.
        memory_enabled: when True, Hindsight memory is recalled and used.
            When False, the agent reasons only from the current incident and
            must NOT reference or invent historical incidents.

    Returns a dict with:
        similar_incidents: [{id, similarity, service, root_cause,
                             resolution, outcome}]
        similar_count: int
        recommendation: str
        investigation_steps: [str]
        evidence_warning: str
        summary: str
        confidence: int (0-100)
        raw_memories: [str]   (the actual recalled memory texts)
        memory_enabled: bool
    """
    if memory_enabled:
        memories, historical_context = _recall_memories(incident)
    else:
        memories = []
        historical_context = "(memory disabled for this investigation)"

    prompt = f"""
A new production incident has occurred.

NEW INCIDENT:
{incident}


HISTORICAL INCIDENT MEMORY:

{historical_context}

IMPORTANT:
Hindsight memory is currently {"ENABLED" if memory_enabled else "DISABLED"} for this investigation.
If memory is disabled, do NOT reference historical incidents. Do NOT invent
incident IDs, similarity percentages, previous root causes, or previous
resolutions.


Analyze the new incident and return a JSON object with EXACTLY this shape:

{{
  "similar_incidents": [
    {{
      "id": "INC-XXX",
      "similarity": 0-100,
      "service": "service name",
      "root_cause": "previously observed root cause",
      "resolution": "previously successful resolution",
      "outcome": "outcome, e.g. Successfully resolved"
    }}
  ],
  "recommendation": "your single best recommendation as a short paragraph",
  "investigation_steps": ["step 1", "step 2", "..."],
  "evidence_warning": "a warning if historical evidence is weak or insufficient, else empty string",
  "summary": "one-sentence summary of the likely root cause",
  "confidence": 0-100
}}

- similarity is your estimated percentage match (integer).
- Order similar_incidents by similarity descending.
- confidence is how confident you are in the root cause (integer 0-100).
  Without historical evidence, confidence should be LOW (typically 30-55).
- If memory is disabled, similar_incidents MUST be [].
- If memory is disabled, evidence_warning MUST say exactly:
  "Hindsight memory was disabled for this investigation."
- If memory is enabled but no relevant incidents exist, return an empty
  similar_incidents list and set evidence_warning accordingly.
"""

    raw = generate_json(prompt, system=STRUCTURED_SYSTEM_PROMPT)

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # Fallback: return a minimal structure so the UI still renders.
        data = {
            "similar_incidents": [],
            "recommendation": raw or "The model did not return a parseable response.",
            "investigation_steps": [],
            "evidence_warning": "Response could not be parsed as structured data.",
            "summary": "",
            "confidence": 0,
        }

    # Normalize + enrich.
    similar = data.get("similar_incidents") or []
    data.setdefault("recommendation", "")
    data.setdefault("investigation_steps", [])
    data.setdefault("evidence_warning", "")
    data.setdefault("summary", "")
    data.setdefault("confidence", 0)

    # Hard guard: when memory is off, never leak invented incidents even if the
    # model ignored the instruction.
    if not memory_enabled:
        similar = []
        data["evidence_warning"] = "Hindsight memory was disabled for this investigation."

    data["similar_incidents"] = similar
    data["similar_count"] = len(similar)
    data["raw_memories"] = memories
    data["memory_enabled"] = memory_enabled

    return data


def record_resolution(content: str, context: str = "Incident resolution feedback") -> None:
    """Store an incident outcome / engineer feedback back into memory.

    This closes the learning loop: future recalls benefit from what actually
    worked (or did not) on past incidents.
    """
    hindsight.retain(bank_id=BANK_ID, content=content, context=context)
