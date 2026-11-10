"""Regras puras: sugestão de atividade, variantes, métricas do grafo e série."""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict

from .errors import InvalidInput
from .model import (
    Activity,
    GraphEdge,
    GraphNode,
    Operation,
    ProcessGraph,
    SeriesPoint,
    Trace,
    Variant,
)

HISTOGRAM_BINS = 12


def normalize_name(name: str) -> str:
    return " ".join(name.strip().split())


def suggest_activity(raw_label: str, catalog: list[Activity]) -> str:
    """Atividade do catálogo com o mesmo nome (sem diferenciar caixa) ou o próprio rótulo."""
    wanted = normalize_name(raw_label).casefold()
    for activity in catalog:
        if activity.name.casefold() == wanted:
            return activity.name
    return normalize_name(raw_label)


def build_operations(traces: list[Trace], catalog: list[Activity]) -> list[Operation]:
    """Uma operação por rótulo bruto do log, da mais frequente para a menos frequente."""
    occurrences: dict[str, int] = defaultdict(int)
    case_ids: dict[str, set[str]] = defaultdict(set)
    durations: dict[str, list[float]] = defaultdict(list)
    for trace in traces:
        for event in trace.events:
            occurrences[event.raw_label] += 1
            case_ids[event.raw_label].add(trace.case_id)
            if event.duration_seconds is not None:
                durations[event.raw_label].append(event.duration_seconds)
    return [
        Operation(
            raw_label=label,
            occurrence_count=count,
            case_count=len(case_ids[label]),
            mean_duration_seconds=round(sum(durations[label]) / len(durations[label]), 3) if durations[label] else 0.0,
            suggested_activity=suggest_activity(label, catalog),
        )
        for label, count in sorted(occurrences.items(), key=lambda item: (-item[1], item[0]))
    ]


def validate_mapping(operations: list[Operation], mapping: dict[str, str]) -> dict[str, str]:
    """Todo rótulo bruto precisa de uma atividade não vazia."""
    known = {op.raw_label for op in operations}
    unknown = sorted(set(mapping) - known)
    if unknown:
        raise InvalidInput(f"Operações desconhecidas: {', '.join(unknown)}.")
    clean = {raw: normalize_name(activity or "") for raw, activity in mapping.items()}
    missing = sorted(raw for raw in known if not clean.get(raw))
    if missing:
        raise InvalidInput(f"Mapeie todas as operações. Faltam: {', '.join(missing)}.")
    return clean


def apply_mapping(traces: list[Trace], mapping: dict[str, str]) -> None:
    for trace in traces:
        for event in trace.events:
            event.activity = mapping[event.raw_label]


def build_variants(traces: list[Trace]) -> list[Variant]:
    """Agrupa traces pela sequência de atividades; a mais frequente é a Variante 1."""
    groups: dict[tuple[str, ...], list[Trace]] = defaultdict(list)
    for trace in traces:
        groups[tuple(e.activity or e.raw_label for e in trace.events)].append(trace)

    ordered = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
    total = len(traces) or 1
    variants: list[Variant] = []
    for position, (sequence, members) in enumerate(ordered, start=1):
        variant_id = f"v{position}"
        for trace in members:
            trace.variant_id = variant_id
        variants.append(
            Variant(
                id=variant_id,
                label=f"Variante {position}",
                sequence=list(sequence),
                trace_count=len(members),
                share=round(len(members) / total, 4),
            )
        )
    return variants


def node_metrics(traces: list[Trace]) -> dict[str, GraphNode]:
    """Frequência e desempenho de cada atividade, como no painel de detalhe do grafo."""
    freq: Counter[str] = Counter()
    cases: Counter[str] = Counter()
    starts: Counter[str] = Counter()
    ends: Counter[str] = Counter()
    max_rep: dict[str, int] = defaultdict(int)
    durations: dict[str, list[float]] = defaultdict(list)

    for trace in traces:
        labels = [e.activity or e.raw_label for e in trace.events]
        if not labels:
            continue
        starts[labels[0]] += 1
        ends[labels[-1]] += 1
        per_case = Counter(labels)
        for label, count in per_case.items():
            freq[label] += count
            cases[label] += 1
            max_rep[label] = max(max_rep[label], count)
        for event in trace.events:
            if event.duration_seconds is not None:
                durations[event.activity or event.raw_label].append(float(event.duration_seconds))

    nodes: dict[str, GraphNode] = {}
    for label in freq:
        values = durations.get(label, [])
        nodes[label] = GraphNode(
            id=label,
            label=label,
            frequency=freq[label],
            case_frequency=cases[label],
            start_frequency=starts[label],
            end_frequency=ends[label],
            max_repetitions=max_rep[label],
            total_duration_seconds=round(sum(values), 3),
            mean_duration_seconds=round(statistics.fmean(values), 3) if values else 0.0,
            median_duration_seconds=round(statistics.median(values), 3) if values else 0.0,
            min_duration_seconds=round(min(values), 3) if values else 0.0,
            max_duration_seconds=round(max(values), 3) if values else 0.0,
            histogram=histogram(values),
        )
    return nodes


def histogram(values: list[float], bins: int = HISTOGRAM_BINS) -> list[int]:
    if not values:
        return []
    low, high = min(values), max(values)
    if high == low:
        return [len(values)] + [0] * (bins - 1)
    width = (high - low) / bins
    counts = [0] * bins
    for value in values:
        counts[min(int((value - low) / width), bins - 1)] += 1
    return counts


def merge_graph(nodes: dict[str, GraphNode], edges: list[GraphEdge]) -> ProcessGraph:
    ordered = sorted(nodes.values(), key=lambda n: (-n.frequency, n.label))
    return ProcessGraph(nodes=ordered, edges=sorted(edges, key=lambda e: (-e.frequency, e.source, e.target)))


def duration_series(traces: list[Trace], activities: set[str] | None = None) -> list[SeriesPoint]:
    """Uma observação por trace, em ordem cronológica.

    Sem filtro, o valor é a duração do trace. Com ``activities``, é a soma das
    durações dos eventos dessas atividades (o tempo de permanência que a
    pesquisa usa ao isolar ``Machine_Operating``).
    """
    ordered = sorted(traces, key=lambda t: (t.started_at is None, t.started_at, t.index))
    points: list[SeriesPoint] = []
    for trace in ordered:
        if activities:
            selected = [
                e.duration_seconds
                for e in trace.events
                if (e.activity or e.raw_label) in activities and e.duration_seconds is not None
            ]
            if not selected:
                continue
            value = float(sum(selected))
        else:
            if trace.duration_seconds is None or trace.duration_seconds < 0:
                continue
            value = float(trace.duration_seconds)
        points.append(SeriesPoint(index=len(points) + 1, case_id=trace.case_id, started_at=trace.started_at, value=value))
    return points
