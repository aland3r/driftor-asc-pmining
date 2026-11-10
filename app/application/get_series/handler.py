"""Série de duração por trace que o ipdd envia para o ADWIN."""

from __future__ import annotations

from app.application.ports import ProcessRepository
from app.domain.errors import InvalidInput, NotFound
from app.domain.model import ProcessStatus, SeriesPoint
from app.domain.rules import duration_series


class GetSeriesHandler:
    def __init__(self, processes: ProcessRepository):
        self._processes = processes

    def handle(self, process_id: str, activities: list[str] | None = None) -> list[SeriesPoint]:
        process = self._processes.get(process_id)
        if process is None:
            raise NotFound("Processo não encontrado.")
        if process.status != ProcessStatus.READY:
            raise InvalidInput("Mapeie as operações antes de analisar o processo.")
        wanted = {a for a in (activities or []) if a}
        points = duration_series(self._processes.traces(process_id), wanted or None)
        if not points:
            raise InvalidInput("O processo não tem traces com duração para esta série.")
        return points
