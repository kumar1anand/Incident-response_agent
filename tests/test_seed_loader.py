"""Idempotency tests for the seed incident loader."""

import os
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

os.environ.setdefault("GROQ_API_KEY", "test-key-for-unit-tests")

from app.load_incidents import load_incidents


def seed_record():
    return {
        "id": "INC-TEST-1",
        "occurred_start": "2026-09-01T12:00:00Z",
        "service": "checkout",
        "severity": "SEV-2",
        "category": "database timeout",
        "symptoms": ["Checkout writes time out"],
        "root_cause": "Connection pool exhausted.",
        "resolution": "Increased pool size.",
        "deployment": "v1.2",
        "duration_minutes": 20,
        "outcome": "resolved",
    }


class FakeMemoryClient:
    def __init__(self):
        self.contents = []
        self.retains = []

    def list_memories(self, bank_id, limit, offset):
        items = [SimpleNamespace(text=text) for text in self.contents[offset:offset + limit]]
        return SimpleNamespace(items=items, total=len(self.contents))

    def retain(self, **kwargs):
        self.retains.append(kwargs)
        self.contents.append(kwargs["content"])


class SeedLoaderTests(unittest.TestCase):
    def test_duplicate_seed_ids_are_retained_once_per_run(self):
        client = FakeMemoryClient()
        incident = seed_record()

        load_incidents([incident, incident], memory_client=client)

        self.assertEqual(len(client.retains), 1)
        self.assertEqual(client.retains[0]["operation_id"], "seed-incident-INC-TEST-1")
        self.assertEqual(client.retains[0]["timestamp"], datetime(2026, 9, 1, 12, tzinfo=timezone.utc))

    def test_repeated_loader_execution_skips_existing_seed_memory(self):
        client = FakeMemoryClient()
        incident = seed_record()

        load_incidents([incident], memory_client=client)
        load_incidents([incident], memory_client=client)

        self.assertEqual(len(client.retains), 1)
        self.assertIn("Incident ID: INC-TEST-1", client.contents[0])


if __name__ == "__main__":
    unittest.main()
