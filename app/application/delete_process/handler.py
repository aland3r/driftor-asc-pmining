"""Delete do Processo; o ipdd apaga as análises ao consumir process-deleted."""

from __future__ import annotations

from app.application.ports import Clock, EventPublisher, ProcessRepository
from app.domain.errors import NotFound

PROCESS_DELETED_QUEUE = "process-deleted"


class DeleteProcessHandler:
    def __init__(self, processes: ProcessRepository, publisher: EventPublisher, clock: Clock):
        self._processes = processes
        self._publisher = publisher
        self._clock = clock

    def handle(self, process_id: str) -> None:
        if not self._processes.delete(process_id):
            raise NotFound("Processo não encontrado.")
        self._publisher.publish(
            PROCESS_DELETED_QUEUE,
            {"type": "process-deleted", "processId": process_id, "occurredAt": self._clock.now().isoformat()},
        )
