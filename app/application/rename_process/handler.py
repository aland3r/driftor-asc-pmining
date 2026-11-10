"""Update do Processo: renomear."""

from __future__ import annotations

from app.application.ports import Clock, ProcessRepository
from app.domain.errors import InvalidInput, NotFound
from app.domain.model import Process
from app.domain.rules import normalize_name


class RenameProcessHandler:
    def __init__(self, processes: ProcessRepository, clock: Clock):
        self._processes = processes
        self._clock = clock

    def handle(self, process_id: str, name: str) -> Process:
        clean = normalize_name(name)
        if not clean:
            raise InvalidInput("Informe o nome do processo.")
        process = self._processes.get(process_id)
        if process is None:
            raise NotFound("Processo não encontrado.")
        process.name = clean
        process.updated_at = self._clock.now()
        self._processes.save(process)
        return process
