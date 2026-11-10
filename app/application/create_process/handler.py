"""Create do Processo: só o nome; o log de eventos vem depois (status 'vazio')."""

from __future__ import annotations

from app.application.ports import Clock, IdGenerator, ProcessRepository
from app.domain.errors import InvalidInput
from app.domain.model import Process, ProcessStatus
from app.domain.rules import normalize_name


class CreateProcessHandler:
    def __init__(self, processes: ProcessRepository, clock: Clock, ids: IdGenerator):
        self._processes = processes
        self._clock = clock
        self._ids = ids

    def handle(self, name: str) -> Process:
        clean = normalize_name(name)
        if not clean:
            raise InvalidInput("Informe o nome do processo.")
        now = self._clock.now()
        process = Process(
            id=self._ids.new_id(),
            name=clean,
            file_name="",
            format="",
            status=ProcessStatus.EMPTY,
            created_at=now,
            updated_at=now,
            trace_count=0,
            event_count=0,
        )
        self._processes.add(process, [])
        return process
