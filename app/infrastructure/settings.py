from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str
    mongodb_db: str
    servicebus_connection: str | None
    cors_origins: list[str]

    @staticmethod
    def from_env() -> "Settings":
        return Settings(
            mongodb_uri=os.environ.get("MONGODB_URI", "mongodb://localhost:27017"),
            mongodb_db=os.environ.get("MONGODB_DB", "pmining"),
            servicebus_connection=os.environ.get("SERVICEBUS_CONNECTION") or None,
            cors_origins=[o for o in os.environ.get("CORS_ORIGINS", "*").split(",") if o],
        )
