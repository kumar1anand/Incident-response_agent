"""Reliability tests for Hindsight recall and async Groq analysis."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

import httpx
from groq import APITimeoutError

from app import groq_client, incident_agent


INCIDENT = "Payment API errors with Kafka consumer lag"


class AgentReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_hindsight_recall_failure_continues_without_historical_claims(self):
        model_response = json.dumps({
            "similar_incidents": [{"id": "INC-FAKE", "similarity": 99}],
            "recommendation": "Inspect current payment and Kafka metrics.",
        })
        with (
            patch.object(incident_agent.hindsight, "arecall", new=AsyncMock(side_effect=ConnectionError("offline"))),
            patch.object(incident_agent, "generate_json_async", new=AsyncMock(return_value=model_response)) as generate,
        ):
            result = await incident_agent.investigate_incident_structured_async(INCIDENT)

        self.assertFalse(result["memory_available"])
        self.assertEqual(result["similar_incidents"], [])
        self.assertEqual(result["raw_memories"], [])
        self.assertEqual(result["confidence"], 0)
        self.assertEqual(result["evidence_warning"], "Hindsight memory was unavailable for this investigation.")
        self.assertIn("UNAVAILABLE", generate.await_args.args[0])
        self.assertIn("Do NOT reference historical incidents", generate.await_args.args[0])

    async def test_groq_timeout_is_converted_to_controlled_error(self):
        timeout = APITimeoutError(request=httpx.Request("POST", "https://api.groq.com"))
        with patch.object(
            groq_client.async_client.chat.completions,
            "create",
            new=AsyncMock(side_effect=timeout),
        ):
            with self.assertRaises(groq_client.GroqUnavailableError):
                await groq_client.generate_json_async("prompt")

    async def test_groq_failure_returns_safe_analysis_instead_of_crashing(self):
        recalled = SimpleNamespace(results=[])
        with (
            patch.object(incident_agent.hindsight, "arecall", new=AsyncMock(return_value=recalled)),
            patch.object(
                incident_agent,
                "generate_json_async",
                new=AsyncMock(side_effect=groq_client.GroqUnavailableError("Groq timed out")),
            ),
        ):
            result = await incident_agent.investigate_incident_structured_async(INCIDENT)

        self.assertEqual(result["recommendation"], "Analysis is temporarily unavailable. Please retry.")
        self.assertEqual(result["similar_incidents"], [])
        self.assertIn("Groq timed out", result["evidence_warning"])

    async def test_normal_recall_and_groq_success(self):
        memory = SimpleNamespace(
            text=f"{INCIDENT}. Outcome: SUCCESS. Remediation resolved the incident.",
            scores=SimpleNamespace(final=0.9),
        )
        recalled = SimpleNamespace(results=[memory])
        model_response = json.dumps({
            "similar_incidents": [{
                "id": "INC-42", "similarity": 80, "service": "payment-api",
                "root_cause": "Consumer lag", "resolution": "Adjust consumer config",
                "outcome": "SUCCESS",
            }],
            "recommendation": "Check consumer group configuration.",
        })
        with (
            patch.object(incident_agent.hindsight, "arecall", new=AsyncMock(return_value=recalled)),
            patch.object(incident_agent, "generate_json_async", new=AsyncMock(return_value=model_response)),
        ):
            result = await incident_agent.investigate_incident_structured_async(INCIDENT)

        self.assertTrue(result["memory_available"])
        self.assertEqual(result["similar_count"], 1)
        self.assertEqual(result["recommendation"], "Check consumer group configuration.")
        self.assertGreater(result["confidence"], 0)


if __name__ == "__main__":
    unittest.main()
