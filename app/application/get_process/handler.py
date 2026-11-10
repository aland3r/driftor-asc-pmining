from __future__ import annotations

from app.application.ports import ProcessRepository
from app.domain.errors import NotFound
from app.domain.model import Process


class GetProcessHandler:
    def __init__(self, processes: ProcessRepository):
        self._processes = processes

    def handle(self, process_id: str) -> Process:
        process = self._processes.get(process_id)
        if process is None:
            raise NotFound("Processo não encontrado.")
        return process
