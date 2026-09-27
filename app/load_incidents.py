"""Seed Hindsight memory from data/incidents.json.

Reads the synthetic incidents and retains each one into the memory bank so the
agent has historical context to recall against.

Run with:
    python -m app.load_incidents
"""

import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from app.memory import hindsight, BANK_ID, format_incident

# data/incidents.json lives at the project root, one level above app/.
DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "incidents.json"


def load_incidents() -> None:
    incidents = json.loads(DATA_FILE.read_text(encoding="utf-8"))

    print(f"Loading {len(incidents)} incidents into bank '{BANK_ID}'...\n")

    for incident in incidents:
        incident_id = incident.get("id", "UNKNOWN")
        content = format_incident(incident)

        hindsight.retain(
            bank_id=BANK_ID,
            content=content,
            context="Historical incident postmortem",
        )
        print(f"  stored {incident_id}")

    print("\nDone. All incidents retained.")


if __name__ == "__main__":
    load_incidents()
