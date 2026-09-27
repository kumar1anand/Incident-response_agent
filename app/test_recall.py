"""Smoke test: recall relevant memories from Hindsight.

Run with:
    python app/test_recall.py
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


result = client.recall(
    bank_id=BANK_ID,
    query="What happened previously when the payment service had Kafka consumer lag?",
)


print("\nRelevant memories:\n")

for memory in result.results:
    print(memory.text)
    print("-" * 80)
