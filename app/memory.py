"""Hindsight memory client.

Hindsight is the long-term memory layer for IncidentIQ. Its three core
operations are:
    - retain(): store new information (incidents, resolutions, feedback)
    - recall(): retrieve relevant memories for a query
    - reflect(): synthesize higher-level insights from stored memories
"""

import os

from hindsight_client import Hindsight

# Initialize the client from environment configuration.
hindsight = Hindsight(
    base_url=os.getenv("HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io"),
    api_key=os.getenv("HINDSIGHT_API_KEY"),
)

# The memory bank all IncidentIQ operations read from / write to.
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incidentiq")


def format_incident(incident: dict) -> str:
    """Render a structured incident dict into the plain-text form we retain.

    Mirrors the layout used for INC-001 so recall works consistently across
    seeded incidents and ad-hoc ones.
    """
    symptoms = incident.get("symptoms", [])
    if isinstance(symptoms, list):
        symptoms_text = "\n".join(symptoms)
    else:
        symptoms_text = str(symptoms)

    return f"""
Incident ID: {incident.get("id", "UNKNOWN")}

Service: {incident.get("service", "Unknown")}

Symptoms:
{symptoms_text}

Root Cause:
{incident.get("root_cause", "")}

Resolution:
{incident.get("resolution", "")}

Outcome:
{incident.get("outcome", "")}

Resolution Status:
{incident.get("resolution_status", "")}
""".strip()
