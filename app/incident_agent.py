"""IncidentDeepDig agent: combines Hindsight memory with Groq reasoning.

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

import asyncio
import json
import re

from app.groq_client import (
    GroqUnavailableError,
    generate_response,
    generate_json_async,
)
from app.memory import hindsight, BANK_ID


async def _recall_memories_async(incident: str):
    """Recall relevant memories on the caller's active event loop."""
    try:
        result = await hindsight.arecall(bank_id=BANK_ID, query=incident)
    except Exception:  # noqa: BLE001 - investigations can continue without history.
        return [], "(Hindsight memory unavailable for this investigation.)", [], False
    recalled = list(result.results)
    memories = [memory.text for memory in recalled]
    context = "\n\n".join(memories) if memories else "(no relevant memories found)"
    return memories, context, recalled, True


def _recall_memories(incident: str):
  """Synchronous adapter for CLI and seed-script callers."""
  memories, context, _, _ = asyncio.run(_recall_memories_async(incident))
  return memories, context


_STOP_WORDS = {
    "a", "an", "and", "are", "after", "as", "at", "be", "by", "for",
    "from", "had", "has", "have", "in", "incident", "is", "it", "of",
    "on", "or", "the", "to", "was", "were", "when", "with",
}


def _memory_relevance(incident: str, recalled) -> float:
    """Return Hindsight's normalized score or explainable incident-term overlap."""
    scores = getattr(recalled, "scores", None)
    final_score = getattr(scores, "final", None)
    if final_score is None and isinstance(scores, dict):
        final_score = scores.get("final")
    if isinstance(final_score, (int, float)):
        score = float(final_score)
        if score > 1:
            score /= 100
        return max(0.0, min(1.0, score))

    text = getattr(recalled, "text", "") or ""
    query_terms = {
        term for term in re.findall(r"[a-z0-9]+", incident.casefold())
        if len(term) > 2 and term not in _STOP_WORDS
    }
    memory_terms = {
        term for term in re.findall(r"[a-z0-9]+", text.casefold())
        if len(term) > 2 and term not in _STOP_WORDS
    }
    return len(query_terms & memory_terms) / len(query_terms) if query_terms else 0.0


def calculate_confidence(incident: str, recalled_memories) -> int:
    """Score evidence on a bounded, explainable scale; no recalled evidence is 0.

    Up to 25 points reflect the number of relevant memories, 50 reflect their
    average relevance, and up to 25 reflect successful versus failed outcomes.
    The memory-count and outcome components are both weighted by relevance.
    """
    memories = list(recalled_memories)
    if not memories:
        return 0

    relevance = [_memory_relevance(incident, item) for item in memories]
    mean_relevance = sum(relevance) / len(relevance)
    count_component = 25 * (min(len(memories), 3) / 3) * mean_relevance
    matching_component = 50 * mean_relevance

    success_count = 0
    failure_count = 0
    failure = re.compile(
        r"\bfailure\b|did\s+not\s+resolve|didn't\s+resolve|not\s+resolved|"
        r"did\s+not\s+work|didn't\s+work|\bfailed\b",
        re.IGNORECASE,
    )
    success = re.compile(
        r"\bsuccess\b|successfully\s+resolved|resolved\s+the\s+incident|\bworked\b",
        re.IGNORECASE,
    )
    for item in memories:
        text = getattr(item, "text", "") or ""
        if failure.search(text):
            failure_count += 1
        elif success.search(text):
            success_count += 1

    outcome_count = success_count + failure_count
    outcome_component = 0.0
    if outcome_count:
        coverage = min(outcome_count, 2) / 2
        balance = (success_count - failure_count) / outcome_count
        outcome_component = 25 * coverage * balance * mean_relevance

    score = count_component + matching_component + outcome_component
    return max(0, min(100, round(score)))


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
3. Previous remediation attempts and their outcomes (SUCCESS or FAILURE)
4. Your recommended investigation steps
5. A warning if the historical evidence is insufficient
"""
    return generate_response(prompt)


STRUCTURED_SYSTEM_PROMPT = """
You are IncidentDeepDig, an AI production incident response assistant.

You help software engineers investigate production incidents using
historical incident memory retrieved from a memory system.

Rules:
- Never invent historical incidents. Only reference incidents that appear
  in the provided HISTORICAL INCIDENT MEMORY.
- Base similarity and root causes strictly on the provided memory.
- If memory is disabled, reason ONLY from the current incident and return an
  empty similar_incidents list.
- Always respond with a single valid JSON object, no prose outside it.
"""


async def investigate_incident_structured_async(
  incident: str, memory_enabled: bool = True
) -> dict:
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
      memories, historical_context, recalled_memories, memory_available = await _recall_memories_async(incident)
    else:
        memories = []
        historical_context = "(memory disabled for this investigation)"
        recalled_memories = []
        memory_available = False

    prompt = f"""
A new production incident has occurred.

NEW INCIDENT:
{incident}


HISTORICAL INCIDENT MEMORY:

{historical_context}

IMPORTANT:
Hindsight memory status is {"AVAILABLE" if memory_available else "UNAVAILABLE" if memory_enabled else "DISABLED"} for this investigation.
If memory is unavailable or disabled, use only the current incident. Do NOT reference historical incidents. Do NOT invent
incident IDs, similarity percentages, previous root causes, or previous
remediation outcomes, including successes and failures.


Analyze the new incident and return a JSON object with EXACTLY this shape:

{{
  "similar_incidents": [
    {{
      "id": "INC-XXX",
      "similarity": 0-100,
      "service": "service name",
      "root_cause": "previously observed root cause",
      "resolution": "previously attempted remediation",
      "outcome": "SUCCESS or FAILURE, with whether it resolved the incident"
    }}
  ],
  "recommendation": "your single best recommendation as a short paragraph",
  "investigation_steps": ["step 1", "step 2", "..."],
  "evidence_warning": "a warning if historical evidence is weak or insufficient, else empty string",
  "summary": "one-sentence summary of the likely root cause"
}}

- similarity is your estimated percentage match (integer).
- Order similar_incidents by similarity descending.
- Distinguish SUCCESS from FAILURE using the recalled memory text. Do not
  describe a failed remediation as successful or recommend blindly repeating
  a remediation explicitly recorded as not resolving a similar incident.
- Use both successful and failed historical experiences when explaining a
  recommendation. State when prior evidence is mixed.
- If memory is disabled, similar_incidents MUST be [].
- If memory is disabled, evidence_warning MUST say exactly:
  "Hindsight memory was disabled for this investigation."
- If memory is enabled but no relevant incidents exist, return an empty
  similar_incidents list and set evidence_warning accordingly.
"""

    try:
        raw = await generate_json_async(prompt, system=STRUCTURED_SYSTEM_PROMPT)
        data = json.loads(raw)
    except GroqUnavailableError as exc:
        data = {
            "similar_incidents": [],
            "recommendation": "Analysis is temporarily unavailable. Please retry.",
            "investigation_steps": [],
            "evidence_warning": str(exc),
            "summary": "",
        }
    except (json.JSONDecodeError, TypeError):
        # Fallback: return a minimal structure so the UI still renders.
        data = {
            "similar_incidents": [],
            "recommendation": raw or "The model did not return a parseable response.",
            "investigation_steps": [],
            "evidence_warning": "Response could not be parsed as structured data.",
            "summary": "",
        }

    # Normalize + enrich.
    similar = data.get("similar_incidents") or []
    data.setdefault("recommendation", "")
    data.setdefault("investigation_steps", [])
    data.setdefault("evidence_warning", "")
    data.setdefault("summary", "")
    # Confidence is computed from retrieved evidence below; ignore any model
    # supplied confidence value, including arbitrary zeros or percentages.

    # Hard guard: when memory is off, never leak invented incidents even if the
    # model ignored the instruction.
    if not memory_enabled or not memory_available:
        similar = []
        data["evidence_warning"] = (
            "Hindsight memory was disabled for this investigation."
            if not memory_enabled
            else "Hindsight memory was unavailable for this investigation."
        )

    data["similar_incidents"] = similar
    data["similar_count"] = len(similar)
    data["confidence"] = calculate_confidence(incident, recalled_memories)
    data["raw_memories"] = memories
    data["memory_enabled"] = memory_enabled
    data["memory_available"] = memory_available

    return data


def investigate_incident_structured(incident: str, memory_enabled: bool = True) -> dict:
    """Synchronous adapter for CLI callers."""
    return asyncio.run(
        investigate_incident_structured_async(incident, memory_enabled=memory_enabled)
    )


async def record_resolution_async(
    content: str,
    context: str = "Incident resolution feedback",
    operation_id: str | None = None,
) -> None:
    """Store an outcome using Hindsight on the active event loop."""
    await hindsight.aretain(
        bank_id=BANK_ID, content=content, context=context, operation_id=operation_id
    )


def record_resolution(content: str, context: str = "Incident resolution feedback") -> None:
    """Store an incident outcome / engineer feedback back into memory.

    This closes the learning loop: future recalls benefit from what actually
    worked (or did not) on past incidents.
    """
    asyncio.run(record_resolution_async(content, context=context))
