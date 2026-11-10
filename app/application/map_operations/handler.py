"""Liga cada operação do log a uma atividade e gera grafo e variantes."""

from __future__ import annotations

from app.application.ports import ActivityRepository, Clock, GraphMiner, ProcessRepository
from app.domain.errors import NotFound
from app.domain.model import Process, ProcessStatus
from app.domain.rules import apply_mapping, build_variants, merge_graph, node_metrics, validate_mapping


class MapOperationsHandler:
    def __init__(self, processes: ProcessRepository, activities: ActivityRepository, miner: GraphMiner, clock: Clock):
        self._processes = processes
        self._activities = activities
        self._miner = miner
        self._clock = clock

    def handle(self, process_id: str, mapping: dict[str, str]) -> Process:
        process = self._processes.get(process_id)
        if process is None:
            raise NotFound("Processo não encontrado.")

        clean = validate_mapping(process.operations, mapping)
        # Sem autenticação nesta versão: atividade nova entra no catálogo.
        self._activities.ensure(sorted(set(clean.values())))

        traces = self._processes.traces(process_id)
        apply_mapping(traces, clean)
        process.variants = build_variants(traces)
        process.graph = merge_graph(node_metrics(traces), self._miner.edges(traces))
        for operation in process.operations:
            operation.activity = clean[operation.raw_label]
        process.status = ProcessStatus.READY
        process.updated_at = self._clock.now()

        self._processes.replace_traces(process_id, traces)
        self._processes.save(process)
        return process
