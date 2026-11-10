"""Entidades do domínio de mineração de processos.

Sem dependências externas: nada aqui conhece Mongo, FastAPI ou PM4Py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ProcessStatus(str, Enum):
    MAPPING = "mapeando"
    READY = "pronto"


@dataclass
class LogEvent:
    raw_label: str
    occurred_at: datetime | None
    duration_seconds: float | None
    activity: str | None = None


@dataclass
class Trace:
    case_id: str
    index: int
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: float | None
    events: list[LogEvent] = field(default_factory=list)
    variant_id: str | None = None


@dataclass
class Operation:
    """Rótulo bruto do log e a atividade do catálogo a que ele foi ligado."""

    raw_label: str
    occurrence_count: int
    case_count: int
    mean_duration_seconds: float
    suggested_activity: str
    activity: str | None = None


@dataclass
class Variant:
    id: str
    label: str
    sequence: list[str]
    trace_count: int
    share: float


@dataclass
class GraphNode:
    id: str
    label: str
    frequency: int
    case_frequency: int
    start_frequency: int
    end_frequency: int
    max_repetitions: int
    total_duration_seconds: float
    mean_duration_seconds: float
    median_duration_seconds: float
    min_duration_seconds: float
    max_duration_seconds: float
    histogram: list[int] = field(default_factory=list)


@dataclass
class GraphEdge:
    source: str
    target: str
    frequency: int


@dataclass
class ProcessGraph:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)


@dataclass
class Process:
    id: str
    name: str
    file_name: str
    format: str
    status: ProcessStatus
    created_at: datetime
    updated_at: datetime
    trace_count: int
    event_count: int
    operations: list[Operation] = field(default_factory=list)
    graph: ProcessGraph | None = None
    variants: list[Variant] = field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass
class Activity:
    id: str
    name: str


@dataclass
class SeriesPoint:
    index: int
    case_id: str
    started_at: datetime | None
    value: float
