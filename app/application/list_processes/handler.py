from __future__ import annotations

from app.application.ports import ProcessRepository
from app.domain.model import Process


class ListProcessesHandler:
    def __init__(self, processes: ProcessRepository):
        self._processes = processes

    def handle(self) -> list[Process]:
        return sorted(self._processes.list(), key=lambda p: p.created_at, reverse=True)
