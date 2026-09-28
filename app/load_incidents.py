"""Seed Hindsight memory from data/incidents.json.

Reads the synthetic incidents and retains each one into the memory bank so the
agent has historical context to recall against.

Run with:
    python -m app.load_incidents
"""

import json
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.memory import hindsight, BANK_ID, format_incident

# data/incidents.json lives at the project root, one level above app/.
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "incidents.json"
_PAGE_SIZE = 100


def _existing_incident_ids(client) -> set[str]:
    """Read stable seed IDs already present in the bank before retaining."""
    ids: set[str] = set()
    offset = 0
    total = None
    while total is None or offset < total:
        result = client.list_memories(bank_id=BANK_ID, limit=_PAGE_SIZE, offset=offset)
        items = getattr(result, "items", None) or []
        if total is None:
            total = getattr(result, "total", None)
        for item in items:
            text = getattr(item, "text", "") or ""
            ids.update(re.findall(r"^Incident ID:\s*([^\s]+)", text, re.IGNORECASE | re.MULTILINE))
        offset += len(items)
        if not items or len(items) < _PAGE_SIZE:
            break
    return ids


def load_incidents(incidents: list[dict] | None = None, memory_client=None) -> None:
    """Retain each seed ID once; injectable inputs keep loader tests offline."""
    if incidents is None:
        incidents = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    client = memory_client or hindsight
    existing_ids = _existing_incident_ids(client)

    print(f"Loading {len(incidents)} incidents into bank '{BANK_ID}'...\n")

    for incident in incidents:
        incident_id = incident.get("id", "UNKNOWN")
        if incident_id in existing_ids:
            print(f"  skipped {incident_id} (already stored)")
            continue
        content = format_incident(incident)
        timestamp_text = incident.get("occurred_start")
        timestamp = datetime.fromisoformat(timestamp_text.replace("Z", "+00:00")) if timestamp_text else None

        client.retain(
            bank_id=BANK_ID,
            content=content,
            context="Historical incident postmortem",
            timestamp=timestamp,
            operation_id=f"seed-incident-{incident_id}",
        )
        existing_ids.add(incident_id)
        print(f"  stored {incident_id}")

    print("\nDone. All incidents retained.")


if __name__ == "__main__":
    load_incidents()
