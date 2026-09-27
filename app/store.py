"""Lightweight local persistence for investigation history.

Hindsight is our long-term semantic memory, but for the UI we also want a
plain, ordered log of every investigation and its feedback outcome (for the
History and Learning screens). We keep that in a small JSON file.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_HISTORY_FILE = _DATA_DIR / "history.json"
_lock = threading.Lock()


def _read() -> list[dict]:
    if not _HISTORY_FILE.exists():
        return []
    try:
        return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _write(records: list[dict]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _HISTORY_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")


def add_investigation(incident: str, analysis: dict) -> dict:
    """Append a new investigation record and return it."""
    with _lock:
        records = _read()
        record = {
            "id": len(records) + 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "incident": incident,
            "summary": analysis.get("summary", ""),
            "similar_count": analysis.get("similar_count", 0),
            "recommendation": analysis.get("recommendation", ""),
            "feedback": None,  # "worked" | "didnt_work" | None
        }
        records.append(record)
        _write(records)
        return record


def set_feedback(record_id: int, feedback: str) -> dict | None:
    """Attach feedback to an existing investigation record."""
    with _lock:
        records = _read()
        for record in records:
            if record["id"] == record_id:
                record["feedback"] = feedback
                _write(records)
                return record
        return None


def list_history() -> list[dict]:
    """Return all investigation records, newest first."""
    return list(reversed(_read()))


def count() -> int:
    return len(_read())
