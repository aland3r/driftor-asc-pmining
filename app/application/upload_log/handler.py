"""Carrega o log de eventos num processo: parse e operações a mapear (status 'mapeando').

Um novo log substitui o anterior: traces, grafo e variantes recomeçam do zero.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.ports import ActivityRepository, Clock, LogParser, ProcessRepository
from app.domain.errors import InvalidInput, NotFound
from app.domain.model import Process, ProcessStatus
from app.domain.rules import build_operations

MAX_UPLOAD_BYTES = 64 * 1024 * 1024


@dataclass
class UploadLog:
    process_id: str
    file_name: str
    content: bytes


class UploadLogHandler:
    def __init__(self, parser: LogParser, processes: ProcessRepository, activities: ActivityRepository, clock: Clock):
        self._parser = parser
        self._processes = processes
        self._activities = activities
        self._clock = clock

    def handle(self, command: UploadLog) -> Process:
        process = self._processes.get(command.process_id)
        if process is None:
            raise NotFound("Processo não encontrado.")
        if not command.content:
            raise InvalidInput("Arquivo vazio.")
        if len(command.content) > MAX_UPLOAD_BYTES:
            raise InvalidInput("Arquivo acima do limite de 64 MB.")

        parsed = self._parser.parse(command.content, command.file_name)
        operations = build_operations(parsed.traces, self._activities.list())
        starts = [t.started_at for t in parsed.traces if t.started_at]
        ends = [t.ended_at for t in parsed.traces if t.ended_at]

        process.file_name = command.file_name
        process.format = parsed.format
        process.status = ProcessStatus.MAPPING
        process.trace_count = len(parsed.traces)
        process.event_count = sum(op.occurrence_count for op in operations)
        process.operations = operations
        process.graph = None
        process.variants = []
        process.started_at = min(starts) if starts else None
        process.ended_at = max(ends) if ends else None
        process.updated_at = self._clock.now()

        self._processes.reset_traces(process.id, parsed.traces)
        self._processes.save(process)
        return process
