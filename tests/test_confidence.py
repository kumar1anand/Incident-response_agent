"""Tests for deterministic confidence scoring from recalled evidence."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

from app import incident_agent


INCIDENT = "Payment service Kafka consumer lag after deployment"


def recalled(text, score):
    return SimpleNamespace(text=text, scores=SimpleNamespace(final=score))


class ConfidenceTests(unittest.IsolatedAsyncioTestCase):
    async def analyze(self, memories, model_json):
        recall_response = SimpleNamespace(results=memories)
        with (
            patch.object(incident_agent.hindsight, "arecall", new=AsyncMock(return_value=recall_response)),
            patch.object(incident_agent, "generate_json_async", new=AsyncMock(return_value=model_json)) as generate,
        ):
            result = await incident_agent.investigate_incident_structured_async(INCIDENT)
        return result, generate.await_args.args[0]

    async def test_no_memory_is_zero_and_model_cannot_supply_confidence(self):
        model_json = json.dumps({"confidence": 94, "similar_incidents": [{"id": "invented"}]})
        with (
            patch.object(incident_agent.hindsight, "arecall", new=AsyncMock()),
            patch.object(incident_agent, "generate_json_async", new=AsyncMock(return_value=model_json)) as generate,
        ):
            result = await incident_agent.investigate_incident_structured_async(
                INCIDENT, memory_enabled=False
            )

        self.assertEqual(result["confidence"], 0)
        self.assertEqual(result["similar_incidents"], [])
        prompt = generate.await_args.args[0].casefold()
        self.assertNotIn('"confidence"', prompt)
        self.assertNotIn("30-55", prompt)

    async def test_strong_successful_memory_evidence_scores_high(self):
        memories = [
            recalled(f"{INCIDENT}. Outcome: SUCCESS. Remediation resolved the incident. {i}", 0.9)
            for i in range(3)
        ]
        result, prompt = await self.analyze(memories, json.dumps({"similar_incidents": []}))

        self.assertEqual(result["confidence"], 90)
        self.assertNotIn('"confidence"', prompt.casefold())

    async def test_failed_outcomes_reduce_confidence_relative_to_successes(self):
        successes = [
            recalled(f"{INCIDENT}. Outcome: SUCCESS. The remediation resolved the incident. {i}", 0.95)
            for i in range(2)
        ]
        failures = [
            recalled(f"{INCIDENT}. Outcome: FAILURE. The remediation did NOT resolve the incident. {i}", 0.95)
            for i in range(2)
        ]
        success_result, _ = await self.analyze(successes, json.dumps({}))
        failure_result, _ = await self.analyze(failures, json.dumps({}))

        self.assertGreater(success_result["confidence"], failure_result["confidence"])
        self.assertGreater(failure_result["confidence"], 0)

    async def test_missing_model_confidence_is_calculated_from_evidence(self):
        memories = [recalled(f"{INCIDENT}. Outcome: SUCCESS. Resolved.", 0.9)]
        result, _ = await self.analyze(memories, json.dumps({"summary": "Evidence-backed finding."}))

        self.assertEqual(result["confidence"], 64)

    def test_zero_relevance_stays_zero(self):
        memories = [recalled("Unrelated cache outage", 0.0)]
        self.assertEqual(incident_agent.calculate_confidence(INCIDENT, memories), 0)


if __name__ == "__main__":
    unittest.main()
