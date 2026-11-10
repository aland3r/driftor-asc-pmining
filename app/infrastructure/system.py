from __future__ import annotations

import uuid
from datetime import datetime, timezone


class UtcClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class UuidGenerator:
    def new_id(self) -> str:
        return str(uuid.uuid4())
