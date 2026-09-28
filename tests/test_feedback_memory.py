"""Regression tests for outcome-aware Hindsight feedback and recall."""

import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

# Importing the application constructs a Groq client; calls are mocked below.
os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

from app import api, incident_agent


class FeedbackMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def _submit_feedback(self, feedback):
        record = {
            "id": 7,
            "incident": "Database connection pool exhausted after deploy.",
            "recommendation": "Roll back the deployment and inspect pool settings.",
        }
        retained = AsyncMock()
        with (
            patch.object(api.store, "set_feedback", return_value=record),
            patch.object(api, "record_resolution_async", retained),
        ):
            result = await api.feedback(
                api.FeedbackRequest(
                    record_id=7,
                    feedback=feedback,
                    incident=record["incident"],
                    root_cause="Pool configuration regression.",
                    resolution=record["recommendation"],
                )
            )
        return result, retained

    async def test_worked_feedback_is_retained_as_success(self):
        result, retained = await self._submit_feedback("worked")
        retained.assert_awaited_once()
        content = retained.await_args.args[0]
        self.assertIn("Database connection pool exhausted", content)
        self.assertIn("Roll back the deployment", content)
        self.assertIn("SUCCESS", content)
        self.assertIn("The remediation resolved the incident.", content)
        self.assertTrue(result["retained"])

    async def test_did_not_work_feedback_is_retained_as_failure(self):
        result, retained = await self._submit_feedback("didnt_work")
        retained.assert_awaited_once()
        content = retained.await_args.args[0]
        self.assertIn("Database connection pool exhausted", content)
        self.assertIn("Roll back the deployment", content)
        self.assertIn("FAILURE", content)
        self.assertIn("did NOT resolve the incident", content)
        self.assertIn("Avoid blindly repeating", content)
        self.assertTrue(result["retained"])

    async def test_repeated_identical_feedback_deduplicates_but_other_outcome_is_distinct(self):
        _, worked_first = await self._submit_feedback("worked")
        _, worked_repeat = await self._submit_feedback("worked")
        _, failed = await self._submit_feedback("didnt_work")

        first_id = worked_first.await_args.kwargs["operation_id"]
        repeat_id = worked_repeat.await_args.kwargs["operation_id"]
        failure_id = failed.await_args.kwargs["operation_id"]
        self.assertEqual(first_id, repeat_id)
        self.assertNotEqual(first_id, failure_id)


class RecallOutcomeTests(unittest.IsolatedAsyncioTestCase):
    async def test_recall_returns_failed_experience_to_investigation(self):
        failed_memory = (
            "Incident: Database connection pool exhausted.\n"
            "Resolution: Restarting workers.\nOutcome: FAILURE.\n"
            "The remediation did NOT resolve the incident."
        )
        successful_memory = (
            "Incident: Database connection pool exhaustion after deploy.\n"
            "Resolution: Roll back the deployment.\nOutcome: SUCCESS.\n"
            "The remediation resolved the incident."
        )
        recalled = SimpleNamespace(results=[
            SimpleNamespace(text=failed_memory),
            SimpleNamespace(text=successful_memory),
        ])
        generated = json.dumps({
            "similar_incidents": [],
            "recommendation": "Inspect pool configuration before retrying remediation.",
        })
        with (
            patch.object(incident_agent.hindsight, "arecall", new=AsyncMock(return_value=recalled)) as recall,
            patch.object(incident_agent, "generate_json_async", new=AsyncMock(return_value=generated)) as generate,
        ):
            result = await incident_agent.investigate_incident_structured_async(
                "Database connection pool exhaustion", memory_enabled=True
            )

        recall.assert_awaited_once()
        prompt = generate.await_args.args[0]
        self.assertIn("Outcome: FAILURE", prompt)
        self.assertIn("did NOT resolve the incident", prompt)
        self.assertIn("Outcome: SUCCESS", prompt)
        self.assertIn("Roll back the deployment", prompt)
        self.assertEqual(result["raw_memories"], [failed_memory, successful_memory])

    async def test_memory_off_does_not_recall_or_expose_historical_experiences(self):
        generated = json.dumps({
            "similar_incidents": [{"id": "INC-FAKE", "outcome": "SUCCESS"}],
            "recommendation": "Investigate current symptoms.",
        })
        with (
            patch.object(incident_agent.hindsight, "arecall", new=AsyncMock()) as recall,
            patch.object(incident_agent, "generate_json_async", new=AsyncMock(return_value=generated)),
        ):
            result = await incident_agent.investigate_incident_structured_async(
                "Current incident", memory_enabled=False
            )

        recall.assert_not_awaited()
        self.assertEqual(result["similar_incidents"], [])
        self.assertEqual(result["raw_memories"], [])
        self.assertEqual(
            result["evidence_warning"],
            "Hindsight memory was disabled for this investigation.",
        )


if __name__ == "__main__":
    unittest.main()
