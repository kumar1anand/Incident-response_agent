"""Evidence-based graph, pattern, and metric views over Hindsight memories."""

import re
from collections import defaultdict

from app import store
from app.memory import BANK_ID, hindsight

_PAGE_SIZE = 100
_FIELDS = (
    "Incident ID", "Incident", "Service", "Severity", "Category", "Deployment",
    "Duration", "Symptoms", "Root Cause", "Resolution", "Outcome",
    "Engineer Feedback", "Context",
)
_FIELD_LINE = re.compile(r"^\s*(" + "|".join(re.escape(x) for x in _FIELDS) + r"):\s*(.*)$", re.I)


def _parse_memory(item, index: int) -> dict | None:
    """Parse the labeled incident and feedback formats this app retains."""
    text = item if isinstance(item, str) else getattr(item, "text", "") or ""
    if not text.strip():
        return None

    fields: dict[str, list[str]] = defaultdict(list)
    current = None
    for line in text.splitlines():
        match = _FIELD_LINE.match(line)
        if match:
            current = match.group(1).casefold()
            fields[current].append(match.group(2).strip())
        elif current:
            fields[current][-1] += ("\n" if fields[current][-1] else "") + line.strip()

    def value(label: str) -> str:
        return "\n".join(v for v in fields.get(label.casefold(), []) if v).strip()

    incident = value("Incident")
    incident_id = value("Incident ID")
    root_cause = value("Root Cause")
    resolution = value("Resolution")
    service = value("Service")
    category = value("Category") or root_cause
    outcome = None
    failure_pattern = r"\bfailure\b|did\s+not\s+resolve|didn't\s+resolve|not\s+resolved|did\s+not\s+work|didn't\s+work|\bfailed\b"
    success_pattern = r"\bsuccess\b|successfully\s+resolved|\bresolved\b|\bworked\b"
    recorded_outcome = value("Outcome").casefold()
    feedback_outcome = value("Engineer Feedback").casefold()
    if re.search(failure_pattern, recorded_outcome):
        outcome = "FAILURE"
    elif re.search(success_pattern, recorded_outcome):
        outcome = "SUCCESS"
    elif re.search(failure_pattern, feedback_outcome):
        outcome = "FAILURE"
    elif re.search(success_pattern, feedback_outcome):
        outcome = "SUCCESS"
    elif re.search(failure_pattern, text.casefold()):
        outcome = "FAILURE"
    elif re.search(success_pattern, text.casefold()):
        outcome = "SUCCESS"

    # Ignore unrelated memory facts; only count a memory with incident context
    # or an explicit incident identifier.
    if not (incident or incident_id):
        return None

    memory_id = getattr(item, "id", None) if not isinstance(item, str) else None
    stable_id = str(incident_id or memory_id or f"memory-{index}")
    deployment = value("Deployment")
    deployment_known = bool(deployment) and deployment.casefold() not in ("none", "no", "n/a")
    deployment_labeled = any(k.casefold() == "deployment" for k in fields)
    duration_match = re.search(r"\d+(?:\.\d+)?", value("Duration"))
    return {
        "id": stable_id,
        "incident": incident or incident_id,
        "service": service,
        "severity": value("Severity"),
        "category": category,
        "root_cause": root_cause,
        "resolution": resolution,
        "outcome": outcome,
        "deployment": deployment if deployment_known else "",
        "deployment_known": deployment_labeled,
        "duration_minutes": float(duration_match.group()) if duration_match else None,
        "source_text": text,
    }


def _experience_records(memories) -> list[dict]:
    return [record for i, item in enumerate(memories) if (record := _parse_memory(item, i))]


def _build_graph(records: list[dict]) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(node_id: str, label: str, ntype: str, **extra):
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "type": ntype, "weight": 0, **extra}
        nodes[node_id]["weight"] += 1

    for rec in records:
        inc_id = f"inc:{rec['id']}"
        nodes[inc_id] = {
            "id": inc_id,
            "label": rec["incident"][:80],
            "type": "incident",
            "weight": 1,
            "severity": rec["severity"],
            "service": rec["service"],
            "category": rec["category"],
            "outcome": rec["outcome"],
        }
        if rec["service"]:
            service_id = f"svc:{rec['service']}"
            add_node(service_id, rec["service"], "service")
            edges.append({"source": inc_id, "target": service_id, "kind": "affects"})
        if rec["category"]:
            category_id = f"cat:{rec['category']}"
            add_node(category_id, rec["category"], "category")
            edges.append({"source": inc_id, "target": category_id, "kind": "caused_by"})
        if rec["resolution"]:
            resolution_id = f"rem:{rec['resolution']}"
            add_node(resolution_id, rec["resolution"], "remediation", outcomes={"SUCCESS": 0, "FAILURE": 0, "UNKNOWN": 0})
            outcome_key = rec["outcome"] or "UNKNOWN"
            nodes[resolution_id]["outcomes"][outcome_key] += 1
            edges.append({
                "source": inc_id,
                "target": resolution_id,
                "kind": (rec["outcome"] or "unknown").casefold(),
            })
    return {"available": True, "error": "", "nodes": list(nodes.values()), "edges": edges}


def _discover_patterns(records: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        if rec["category"]:
            groups[rec["category"]].append(rec)

    patterns = []
    for category, experiences in groups.items():
        if len(experiences) < 2:
            continue
        deploy_known = [r for r in experiences if r["deployment_known"]]
        successful = sum(r["outcome"] == "SUCCESS" for r in experiences)
        failed = sum(r["outcome"] == "FAILURE" for r in experiences)
        services = sorted({r["service"] for r in experiences if r["service"]})
        resolutions = sorted({r["resolution"] for r in experiences if r["resolution"]})
        by_resolution: dict[str, dict] = {}
        for rec in experiences:
            if not rec["resolution"]:
                continue
            counts = by_resolution.setdefault(rec["resolution"], {"resolution": rec["resolution"], "success": 0, "failure": 0, "unknown": 0})
            outcome_key = {"SUCCESS": "success", "FAILURE": "failure"}.get(rec["outcome"], "unknown")
            counts[outcome_key] += 1
        durations = [r["duration_minutes"] for r in experiences if r["duration_minutes"] is not None]
        deploy_related_known = sum(bool(r["deployment"]) for r in deploy_known)
        deploy_pct = round(100 * deploy_related_known / len(deploy_known)) if deploy_known else None
        patterns.append({
            "category": category,
            "count": len(experiences),
            "services": services,
            "deploy_related": deploy_related_known if deploy_known else None,
            "deploy_pct": deploy_pct,
            "avg_duration_minutes": round(sum(durations) / len(durations), 1) if durations else None,
            "common_resolutions": resolutions[:3],
            "remediation_outcomes": sorted(by_resolution.values(), key=lambda r: r["resolution"]),
            "successful_remediations": successful,
            "failed_remediations": failed,
            "insight": f"{len(experiences)} memories share this recorded category.",
        })
    patterns.sort(key=lambda p: p["count"], reverse=True)

    deployment_records = [r for r in records if r["deployment_known"]]
    deploy_total = sum(bool(r["deployment"]) for r in deployment_records)
    deploy_pct = round(100 * deploy_total / len(deployment_records)) if deployment_records else None
    return {
        "available": True,
        "total_incidents": len(records),
        "patterns": patterns,
        "error": "",
        "deployment_risk": {
            "deploy_related": deploy_total if deployment_records else None,
            "total": len(deployment_records),
            "share_pct": deploy_pct,
            "warning": f"{deploy_pct}% of memories with deployment data followed a deployment."
            if deploy_pct is not None and deploy_pct >= 40 else "",
        },
    }


def _compute_metrics(records: list[dict], history: list[dict] | None = None) -> dict:
    severity: dict[str, int] = defaultdict(int)
    by_service: dict[str, int] = defaultdict(int)
    for rec in records:
        if rec["severity"]:
            severity[rec["severity"]] += 1
        if rec["service"]:
            by_service[rec["service"]] += 1
    milestones = []
    for i, rec in enumerate(reversed(history if history is not None else store.list_history()), start=1):
        milestones.append({
            "index": i,
            "similar_count": rec.get("similar_count", 0),
            "feedback": rec.get("feedback"),
        })
    return {
        "available": True,
        "total_incidents": len(records),
        "severity": dict(sorted(severity.items())),
        "by_service": dict(sorted(by_service.items(), key=lambda kv: kv[1], reverse=True)),
        "outcomes": {
            "success": sum(r["outcome"] == "SUCCESS" for r in records),
            "failure": sum(r["outcome"] == "FAILURE" for r in records),
            "unknown": sum(r["outcome"] is None for r in records),
        },
        "learning_curve": milestones,
    }


async def get_snapshot() -> dict:
    """Load the Hindsight bank and derive all screen data from its memories."""
    try:
        memories = []
        offset = 0
        total = None
        while total is None or offset < total:
            result = await hindsight.alist_memories(
                bank_id=BANK_ID, limit=_PAGE_SIZE, offset=offset
            )
            page = getattr(result, "items", None) or []
            if total is None:
                total = getattr(result, "total", None)
            memories.extend(page)
            offset += len(page)
            if not page or len(page) < _PAGE_SIZE:
                break

        records = _experience_records(memories)

        return {
            "available": True,
            "error": "",
            "memory_count": total if total is not None else len(memories),
            "graph": _build_graph(records),
            "patterns": _discover_patterns(records),
            "metrics": _compute_metrics(records),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "available": False,
            "error": f"Hindsight insights unavailable: {exc}",
            "memory_count": 0,
            "graph": {"available": False, "nodes": [], "edges": []},
            "patterns": {
                "available": False, "total_incidents": 0, "patterns": [],
                "error": f"Hindsight insights unavailable: {exc}",
                "deployment_risk": {"deploy_related": None, "total": 0, "share_pct": None, "warning": ""},
            },
            "metrics": {
                "available": False, "total_incidents": 0, "severity": {},
                "by_service": {}, "outcomes": {"success": 0, "failure": 0, "unknown": 0},
                "learning_curve": _compute_metrics([])["learning_curve"],
            },
        }


def build_graph(records: list[dict]) -> dict:
    return _build_graph(records)


def discover_patterns(records: list[dict]) -> dict:
    return _discover_patterns(records)


def compute_metrics(records: list[dict]) -> dict:
    return _compute_metrics(records)
