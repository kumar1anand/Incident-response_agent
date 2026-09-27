"""Central configuration for IncidentIQ.

Loads environment variables from the project .env file and exposes them
as module-level constants so the rest of the app has a single import point.
"""

import os

from dotenv import load_dotenv

# Load .env once, as early as possible.
load_dotenv()

# Hindsight (memory) configuration
HINDSIGHT_API_URL = os.getenv("HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io")
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")
HINDSIGHT_BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "incidentiq")

# Groq (LLM) configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


def require(name: str, value: str | None) -> str:
    """Return the value or raise a clear error if it is missing."""
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Set it in your .env file (see .env template)."
        )
    return value
