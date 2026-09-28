"""IncidentDeepDig FastAPI backend.

Exposes the agent + memory operations as REST endpoints for the React UI.

Run with:
    uvicorn app.api:app --reload --port 8000
"""

import sys
import hashlib

# LLM/memory output can contain Unicode; force UTF-8 so logging on Windows
# consoles doesn't crash.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app import store
from app import insights
from app.incident_agent import (
    investigate_incident_structured_async,
    record_resolution_async,
)
from app.memory import hindsight, BANK_ID

app = FastAPI(title="IncidentDeepDig API", version="1.0.0")

# Allow the Vite dev server (and any local origin) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Schemas ----------

class InvestigateRequest(BaseModel):
    incident: str
    memory_enabled: bool = True


class FeedbackRequest(BaseModel):
    record_id: int
    feedback: str  # "worked" | "didnt_work"
    incident: str = ""
    root_cause: str = ""
    resolution: str = ""


# ---------- Endpoints ----------

@app.get("/api/health")
async def health():
    """Report backend + Hindsight connectivity for the header status pill."""
    hindsight_ok = True
    try:
        await hindsight.aget_version()
    except Exception:
        hindsight_ok = False
    return {
        "status": "healthy" if hindsight_ok else "degraded",
        "hindsight": hindsight_ok,
        "bank_id": BANK_ID,
    }


@app.post("/api/investigate")
async def investigate(req: InvestigateRequest):
    """Investigate a new incident: recall memory + Groq analysis."""
    incident = (req.incident or "").strip()
    if not incident:
        raise HTTPException(status_code=400, detail="Incident text is required.")

    analysis = await investigate_incident_structured_async(
        incident, memory_enabled=req.memory_enabled
    )
    record = store.add_investigation(incident, analysis)

    # Attach the record id so the UI can send feedback later.
    analysis["record_id"] = record["id"]
    return analysis


# The fixed incident used for the 60-second judge demonstration.
JUDGE_INCIDENT = """
Payment Service is returning HTTP 500 errors.

Kafka consumer lag has increased significantly.

The problem started shortly after deployment v2.4.1.

Customer payment requests are intermittently failing.
""".strip()


@app.post("/api/judge-demo")
async def judge_demo():
    """Run the same incident twice: once without memory, once with Hindsight.

    Powers the Judge Mode before/after story. Returns both analyses plus the
    incident text so the frontend can animate the contrast.
    """
    without_memory = await investigate_incident_structured_async(
        JUDGE_INCIDENT, memory_enabled=False
    )
    with_memory = await investigate_incident_structured_async(
        JUDGE_INCIDENT, memory_enabled=True
    )

    # Record the with-memory run so feedback + history reflect the demo.
    record = store.add_investigation(JUDGE_INCIDENT, with_memory)
    with_memory["record_id"] = record["id"]

    return {
        "incident": JUDGE_INCIDENT,
        "without_memory": without_memory,
        "with_memory": with_memory,
    }


@app.post("/api/feedback")
async def feedback(req: FeedbackRequest):
    """Record engineer feedback and retain either outcome into Hindsight."""
    if req.feedback not in ("worked", "didnt_work"):
        raise HTTPException(status_code=400, detail="Invalid feedback value.")

    record = store.set_feedback(req.record_id, req.feedback)
    if record is None:
        raise HTTPException(status_code=404, detail="Investigation record not found.")

    # Retain both positive and negative experiences so recall can guide future
    # recommendations away from remediations that failed in similar incidents.
    outcome = "SUCCESS" if req.feedback == "worked" else "FAILURE"
    outcome_detail = (
        "The remediation resolved the incident."
        if req.feedback == "worked"
        else "The remediation did NOT resolve the incident. Avoid blindly repeating this remediation for similar incidents."
    )
    content = f"""
Incident remediation feedback.

Incident:
{req.incident or record.get("incident", "")}

Root Cause:
{req.root_cause or "As diagnosed by IncidentDeepDig."}

Resolution:
{req.resolution or record.get("recommendation", "")}

Engineer feedback:
{"The recommendation worked." if req.feedback == "worked" else "The recommendation did not work."}

Outcome:
{outcome}
{outcome_detail}
""".strip()
    try:
        content_key = " ".join(content.split()).casefold()
        operation_id = "feedback-" + hashlib.sha256(content_key.encode("utf-8")).hexdigest()
        await record_resolution_async(content, operation_id=operation_id)
        record["retained"] = True
    except Exception as exc:  # noqa: BLE001
        record["retained"] = False
        record["retain_error"] = str(exc)

    return record


@app.get("/api/memory")
async def memory(limit: int = 50):
    """List incidents currently remembered in Hindsight."""
    try:
        result = await hindsight.alist_memories(bank_id=BANK_ID)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Hindsight error: {exc}") from exc

    # ListMemoryUnitsResponse exposes .items (list of MemoryUnitListItem)
    # and .total.
    raw_items = getattr(result, "items", None) or []
    total = getattr(result, "total", len(raw_items))

    items = []
    for item in raw_items[:limit]:
        items.append(
            {
                "id": getattr(item, "id", None),
                "text": getattr(item, "text", "") or "",
                "context": getattr(item, "context", "") or "",
                "entities": getattr(item, "entities", "") or "",
                "fact_type": getattr(item, "fact_type", "") or "",
                "occurred_start": getattr(item, "occurred_start", None),
                "updated_at": getattr(item, "updated_at", None),
            }
        )

    return {"total": total, "items": items}


@app.get("/api/history")
def history():
    """Return the ordered investigation log (newest first)."""
    records = store.list_history()
    return {"total": len(records), "items": records}


@app.get("/api/learning")
def learning():
    """Summarize the agent's learning curve from the investigation log.

    We bucket investigations in order and report how many similar incidents
    the agent found over time, plus feedback outcomes. This powers the
    Learning screen's before/after story.
    """
    records = list(reversed(store.list_history()))  # oldest first
    milestones = []
    for i, rec in enumerate(records, start=1):
        milestones.append(
            {
                "index": i,
                "similar_count": rec.get("similar_count", 0),
                "summary": rec.get("summary", ""),
                "feedback": rec.get("feedback"),
                "created_at": rec.get("created_at"),
            }
        )

    total = len(records)
    worked = sum(1 for r in records if r.get("feedback") == "worked")
    return {
        "total_investigations": total,
        "successful_resolutions": worked,
        "milestones": milestones,
    }


@app.get("/api/graph")
async def graph():
    """Knowledge graph built from retained Hindsight memories."""
    return (await insights.get_snapshot())["graph"]


@app.get("/api/patterns")
async def patterns():
    """Recurring incident patterns derived from retained Hindsight memories."""
    return (await insights.get_snapshot())["patterns"]


@app.get("/api/metrics")
async def metrics():
    """Aggregate metrics derived from retained Hindsight memories."""
    return (await insights.get_snapshot())["metrics"]
