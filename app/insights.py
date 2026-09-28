"""Insight computation for graphs, patterns, and metrics.

All values here are derived directly from data/incidents.json plus the local
investigation history. Nothing is fabricated: counts, rates, and correlations
are computed from the actual seeded incidents.
"""

import json
from collections import defaultdict
from pathlib import Path

from app import store

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "incidents.json"


def _load_incidents() -> list[dict]:
    if not _DATA_FILE.exists():
        return []
    try:
        return json.loads(_DATA_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def build_graph() -> dict:
    """Build a knowledge graph of services, incidents, categories, resolutions.

    Node types: service, incident, category (root-cause family), resolution.
    Edges connect incident -> service, incident -> category, category ->
    resolution (aggregated).
    """
    incidents = _load_incidents()

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add_node(node_id: str, label: str, ntype: str, **extra):
        if node_id not in nodes:
            nodes[node_id] = {"id": node_id, "label": label, "type": ntype, "weight": 0, **extra}
        nodes[node_id]["weight"] += 1

    for inc in incidents:
        inc_id = inc.get("id", "?")
        service = inc.get("service", "unknown")
        category = inc.get("category", "uncategorized")
        severity = inc.get("severity", "")

        svc_id = f"svc:{service}"
        cat_id = f"cat:{category}"
        inc_node_id = f"inc:{inc_id}"

        add_node(svc_id, service, "service")
        add_node(cat_id, category, "category")
        # incident nodes are unique; weight stays 1
        nodes[inc_node_id] = {
            "id": inc_node_id,
            "label": inc_id,
            "type": "incident",
            "weight": 1,
            "severity": severity,
            "service": service,
            "category": category,
        }

        edges.append({"source": inc_node_id, "target": svc_id, "kind": "affects"})
        edges.append({"source": inc_node_id, "target": cat_id, "kind": "caused_by"})

    return {"nodes": list(nodes.values()), "edges": edges}


def discover_patterns() -> dict:
    """Find recurring root-cause categories and deployment correlation."""
    incidents = _load_incidents()
    total = len(incidents)

    by_category: dict[str, list[dict]] = defaultdict(list)
    for inc in incidents:
        by_category[inc.get("category", "uncategorized")].append(inc)

    patterns = []
    for category, incs in by_category.items():
        count = len(incs)
        if count < 2:
            continue  # a pattern needs repetition
        deploy_related = sum(1 for i in incs if i.get("deployment"))
        services = sorted({i.get("service", "unknown") for i in incs})
        resolutions = sorted({i.get("resolution", "") for i in incs if i.get("resolution")})
        avg_duration = round(
            sum(i.get("duration_minutes", 0) for i in incs) / count, 1
        )
        deploy_pct = round(100 * deploy_related / count) if count else 0

        insight = ""
        if deploy_pct >= 60:
            insight = (
                f"{deploy_pct}% of '{category}' incidents occurred shortly after a "
                f"deployment — strongly deployment-correlated."
            )
        elif deploy_pct > 0:
            insight = f"{deploy_pct}% of '{category}' incidents followed a deployment."
        else:
            insight = f"'{category}' incidents were not deployment-related."

        patterns.append(
            {
                "category": category,
                "count": count,
                "services": services,
                "deploy_related": deploy_related,
                "deploy_pct": deploy_pct,
                "avg_duration_minutes": avg_duration,
                "common_resolutions": resolutions[:3],
                "insight": insight,
            }
        )

    patterns.sort(key=lambda p: p["count"], reverse=True)

    # Deployment risk: overall share of incidents that followed a deployment.
    deploy_total = sum(1 for i in incidents if i.get("deployment"))
    deploy_share = round(100 * deploy_total / total) if total else 0

    return {
        "total_incidents": total,
        "patterns": patterns,
        "deployment_risk": {
            "deploy_related": deploy_total,
            "total": total,
            "share_pct": deploy_share,
            "warning": (
                f"{deploy_share}% of all incidents occurred shortly after a deployment. "
                f"Review consumer/config changes in the deployment checklist."
            )
            if deploy_share >= 40
            else "",
        },
    }


def compute_metrics() -> dict:
    """Metrics for charts: severity mix, per-service counts, and a learning
    curve derived from the real investigation history.
    """
    incidents = _load_incidents()

    severity_counts: dict[str, int] = defaultdict(int)
    service_counts: dict[str, int] = defaultdict(int)
    for inc in incidents:
        severity_counts[inc.get("severity", "?")] += 1
        service_counts[inc.get("service", "unknown")] += 1

    # Learning curve from the actual investigation log (oldest first).
    history = list(reversed(store.list_history()))
    curve = []
    for i, rec in enumerate(history, start=1):
        curve.append(
            {
                "index": i,
                "similar_count": rec.get("similar_count", 0),
                "feedback": rec.get("feedback"),
            }
        )

    return {
        "total_incidents": len(incidents),
        "severity": dict(sorted(severity_counts.items())),
        "by_service": dict(sorted(service_counts.items(), key=lambda kv: kv[1], reverse=True)),
        "learning_curve": curve,
    }
