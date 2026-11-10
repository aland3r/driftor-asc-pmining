"""Traces do processo para a lista lateral (agrupados por variante no front)."""

from __future__ import annotations

from app.application.ports import ProcessRepository
from app.domain.errors import NotFound
from app.domain.model import Trace


class ListTracesHandler:
    def __init__(self, processes: ProcessRepository):
        self._processes = processes

    def handle(self, process_id: str, variant_id: str | None = None) -> list[Trace]:
        if self._processes.get(process_id) is None:
            raise NotFound("Processo não encontrado.")
        traces = self._processes.traces(process_id)
        if variant_id:
            traces = [t for t in traces if t.variant_id == variant_id]
        return sorted(traces, key=lambda t: t.index)
