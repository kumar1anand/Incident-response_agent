"""Tests for Hindsight-backed insights and their API response shapes."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

from app import api, insights


def memory(memory_id, text):
    return SimpleNamespace(id=memory_id, text=text)


INCIDENT_ONE = """Incident remediation feedback.

Incident:
Payment requests failing while Kafka lag rises.

Root Cause:
Consumer group rebalance after deployment.

Resolution:
Restart consumers.

Outcome:
SUCCESS
The remediation resolved the incident.
"""

INCIDENT_TWO = """Incident remediation feedback.

Incident:
Payment webhooks delayed and Kafka lag rising.

Root Cause:
Consumer group rebalance after deployment.

Resolution:
Restart consumers.

Outcome:
FAILURE
The remediation did NOT resolve the incident.
"""


class HindsightInsightsTests(unittest.IsolatedAsyncioTestCase):
    async def test_insights_derive_from_memories_and_distinguish_outcomes(self):
        response = SimpleNamespace(items=[memory("m1", INCIDENT_ONE), memory("m2", INCIDENT_TWO)], total=2)
        with patch.object(insights.hindsight, "alist_memories", new=AsyncMock(return_value=response)) as listing:
            snapshot = await insights.get_snapshot()

        listing.assert_awaited_once_with(bank_id=insights.BANK_ID, limit=100, offset=0)
        self.assertTrue(snapshot["available"])
        self.assertEqual(snapshot["metrics"]["total_incidents"], 2)
        self.assertEqual(snapshot["metrics"]["outcomes"], {"success": 1, "failure": 1, "unknown": 0})
        self.assertEqual(snapshot["patterns"]["patterns"][0]["count"], 2)
        pattern = snapshot["patterns"]["patterns"][0]
        self.assertEqual(pattern["successful_remediations"], 1)
        self.assertEqual(pattern["failed_remediations"], 1)
        self.assertEqual(pattern["remediation_outcomes"][0]["success"], 1)
        self.assertEqual(pattern["remediation_outcomes"][0]["failure"], 1)
        remediation_node = next(n for n in snapshot["graph"]["nodes"] if n["type"] == "remediation")
        self.assertEqual(remediation_node["outcomes"], {"SUCCESS": 1, "FAILURE": 1, "UNKNOWN": 0})

    async def test_empty_memory_produces_empty_insights(self):
        response = SimpleNamespace(items=[], total=0)
        with patch.object(insights.hindsight, "alist_memories", new=AsyncMock(return_value=response)):
            snapshot = await insights.get_snapshot()

        self.assertTrue(snapshot["available"])
        self.assertEqual(snapshot["patterns"]["patterns"], [])
        self.assertEqual(snapshot["graph"]["nodes"], [])
        self.assertEqual(snapshot["metrics"]["total_incidents"], 0)
        self.assertEqual(snapshot["metrics"]["by_service"], {})

    async def test_hindsight_error_returns_unavailable_empty_memory_data(self):
        with patch.object(insights.hindsight, "alist_memories", new=AsyncMock(side_effect=RuntimeError("offline"))):
            snapshot = await insights.get_snapshot()

        self.assertFalse(snapshot["available"])
        self.assertIn("offline", snapshot["error"])
        self.assertFalse(snapshot["patterns"]["available"])
        self.assertEqual(snapshot["graph"]["nodes"], [])
        self.assertEqual(snapshot["metrics"]["by_service"], {})

    async def test_api_routes_return_shapes_consumed_by_frontend(self):
        snapshot = {
            "graph": {"available": True, "error": "", "nodes": [], "edges": []},
            "patterns": {"available": True, "error": "", "total_incidents": 0, "patterns": [],
                          "deployment_risk": {"deploy_related": None, "total": 0, "share_pct": None, "warning": ""}},
            "metrics": {"available": True, "error": "", "total_incidents": 0, "severity": {},
                        "by_service": {}, "outcomes": {"success": 0, "failure": 0, "unknown": 0}, "learning_curve": []},
        }
        with patch.object(api.insights, "get_snapshot", new=AsyncMock(return_value=snapshot)):
            graph_response = await api.graph()
            patterns_response = await api.patterns()
            metrics_response = await api.metrics()

        self.assertEqual(graph_response, snapshot["graph"])
        self.assertEqual(patterns_response, snapshot["patterns"])
        self.assertEqual(metrics_response, snapshot["metrics"])
        self.assertIn("available", graph_response)
        self.assertIn("outcomes", metrics_response)


if __name__ == "__main__":
    unittest.main()
