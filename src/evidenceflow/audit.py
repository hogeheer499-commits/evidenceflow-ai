from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Any


class AuditLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._previous_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return "0" * 64
        last = self.path.read_text().splitlines()[-1]
        return str(json.loads(last)["event_hash"])

    def append(self, event: str, case_id: str, **details: Any) -> str:
        with self._lock:
            record = {
                "timestamp": datetime.now(UTC).isoformat(),
                "event": event,
                "case_id": case_id,
                "details": details,
                "previous_hash": self._previous_hash,
            }
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
            event_hash = hashlib.sha256(canonical.encode()).hexdigest()
            record["event_hash"] = event_hash
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(self.path, 0o600)
            self._previous_hash = event_hash
            return event_hash

    def verify(self) -> bool:
        with self._lock:
            previous = "0" * 64
            if not self.path.exists():
                return True
            try:
                for line in self.path.read_text().splitlines():
                    record = json.loads(line)
                    event_hash = record.pop("event_hash")
                    if record["previous_hash"] != previous:
                        return False
                    canonical = json.dumps(
                        record, sort_keys=True, separators=(",", ":")
                    )
                    if hashlib.sha256(canonical.encode()).hexdigest() != event_hash:
                        return False
                    previous = event_hash
            except (json.JSONDecodeError, KeyError, TypeError):
                return False
            return True
