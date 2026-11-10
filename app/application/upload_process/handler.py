"""Create do Processo: recebe o log, faz o parse e devolve as operações a mapear."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from app.application.ports import ActivityRepository, Clock, IdGenerator, LogParser, ProcessRepository
from app.domain.errors import InvalidInput
from app.domain.model import Operation, Process, ProcessStatus
from app.domain.rules import normalize_name, suggest_activity

MAX_UPLOAD_BYTES = 64 * 1024 * 1024


@dataclass
class UploadProcess:
    name: str
    file_name: str
    content: bytes


class UploadProcessHandler:
    def __init__(self, parser: LogParser, processes: ProcessRepository, activities: ActivityRepository, clock: Clock, ids: IdGenerator):
        self._parser = parser
        self._processes = processes
        self._activities = activities
        self._clock = clock
        self._ids = ids

    def handle(self, command: UploadProcess) -> Process:
        name = normalize_name(command.name)
        if not name:
            raise InvalidInput("Informe o nome do processo.")
        if not command.content:
            raise InvalidInput("Arquivo vazio.")
        if len(command.content) > MAX_UPLOAD_BYTES:
            raise InvalidInput("Arquivo acima do limite de 64 MB.")

        parsed = self._parser.parse(command.content, command.file_name)
        catalog = self._activities.list()

        occurrences: dict[str, int] = defaultdict(int)
        case_ids: dict[str, set[str]] = defaultdict(set)
        durations: dict[str, list[float]] = defaultdict(list)
        for trace in parsed.traces:
            for event in trace.events:
                occurrences[event.raw_label] += 1
                case_ids[event.raw_label].add(trace.case_id)
                if event.duration_seconds is not None:
                    durations[event.raw_label].append(event.duration_seconds)

        operations = [
            Operation(
                raw_label=label,
                occurrence_count=count,
                case_count=len(case_ids[label]),
                mean_duration_seconds=round(sum(durations[label]) / len(durations[label]), 3) if durations[label] else 0.0,
                suggested_activity=suggest_activity(label, catalog),
            )
            for label, count in sorted(occurrences.items(), key=lambda item: (-item[1], item[0]))
        ]

        starts = [t.started_at for t in parsed.traces if t.started_at]
        ends = [t.ended_at for t in parsed.traces if t.ended_at]
        now = self._clock.now()
        process = Process(
            id=self._ids.new_id(),
            name=name,
            file_name=command.file_name,
            format=parsed.format,
            status=ProcessStatus.MAPPING,
            created_at=now,
            updated_at=now,
            trace_count=len(parsed.traces),
            event_count=sum(occurrences.values()),
            operations=operations,
            started_at=min(starts) if starts else None,
            ended_at=max(ends) if ends else None,
        )
        self._processes.add(process, parsed.traces)
        return process
