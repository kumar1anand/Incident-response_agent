"""IncidentDeepDig command-line investigation entry point.

Run with:
    python -m app.main
"""

import sys

from dotenv import load_dotenv

# LLM output can contain Unicode (e.g. non-breaking hyphens). Force UTF-8 so
# printing doesn't crash on Windows consoles that default to cp1252.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):
    pass

# Load environment before importing modules that read env at import time.
load_dotenv()

from app.incident_agent import investigate_incident


new_incident = """
Payment Service is returning HTTP 500 errors.

Kafka consumer lag has increased significantly.

The problem started shortly after a deployment.
"""


def main() -> None:
    response = investigate_incident(new_incident)

    print("\n")
    print("=" * 80)
    print("INCIDENTDEEPDIG ANALYSIS")
    print("=" * 80)
    print(response)


if __name__ == "__main__":
    main()
