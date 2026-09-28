"""Smoke test: store (retain) a first incident in Hindsight.

Run with:
    python scripts/retain_sample_hindsight.py
"""

from dotenv import load_dotenv

load_dotenv()

import os

from hindsight_client import Hindsight

client = Hindsight(
    base_url=os.getenv("HINDSIGHT_API_URL"),
    api_key=os.getenv("HINDSIGHT_API_KEY"),
)

BANK_ID = os.getenv("HINDSIGHT_BANK_ID")


incident = """
Incident ID: INC-001

Service: Payment Service

Symptoms:
Payment requests are returning HTTP 500 errors.
Kafka consumer lag is increasing.

Root Cause:
Kafka consumer rebalance caused delayed payment event processing.

Resolution:
Restarted affected consumers and increased Kafka partition capacity.

Outcome:
Payment processing returned to normal and consumer lag dropped.

Resolution Status:
Successfully resolved.
"""


client.retain(
    bank_id=BANK_ID,
    content=incident,
    context="Production incident postmortem",
)

print("Incident stored successfully!")
