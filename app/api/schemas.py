"""Contratos HTTP (camelCase, como o BFF e o front esperam)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class OperationOut(Schema):
    raw_label: str
    occurrence_count: int
    case_count: int
    mean_duration_seconds: float
    suggested_activity: str
    activity: str | None = None


class VariantOut(Schema):
    id: str
    label: str
    sequence: list[str]
    trace_count: int
    share: float


class NodeOut(Schema):
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
    histogram: list[int]


class EdgeOut(Schema):
    source: str
    target: str
    frequency: int


class GraphOut(Schema):
    nodes: list[NodeOut]
    edges: list[EdgeOut]


class ProcessSummaryOut(Schema):
    id: str
    name: str
    file_name: str
    format: str
    status: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None
    trace_count: int
    event_count: int
    activity_count: int
    variant_count: int


class ProcessOut(ProcessSummaryOut):
    operations: list[OperationOut]
    variants: list[VariantOut]
    graph: GraphOut | None = None


class TraceOut(Schema):
    index: int
    case_id: str
    variant_id: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: float | None = None
    event_count: int
    activities: list[str]


class SeriesPointOut(Schema):
    index: int
    case_id: str
    started_at: datetime | None = None
    value: float


class SeriesOut(Schema):
    process_id: str
    activities: list[str]
    points: list[SeriesPointOut]


class ActivityOut(Schema):
    id: str
    name: str
    description: str = ""


class ActivityIn(Schema):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=280)


class CreateProcessIn(Schema):
    name: str = Field(min_length=1, max_length=160)


class RenameIn(Schema):
    name: str = Field(min_length=1, max_length=160)


class MappingItemIn(Schema):
    raw_label: str
    activity: str
    description: str = Field(default="", max_length=280)


class MappingIn(Schema):
    operations: list[MappingItemIn]


def summary(process) -> dict:
    activities = {op.activity for op in process.operations if op.activity}
    return {
        "id": process.id,
        "name": process.name,
        "file_name": process.file_name,
        "format": process.format,
        "status": process.status.value,
        "created_at": process.created_at,
        "updated_at": process.updated_at,
        "started_at": process.started_at,
        "ended_at": process.ended_at,
        "trace_count": process.trace_count,
        "event_count": process.event_count,
        "activity_count": len(activities),
        "variant_count": len(process.variants),
    }


def process_out(process) -> ProcessOut:
    return ProcessOut.model_validate(
        {
            **summary(process),
            "operations": process.operations,
            "variants": process.variants,
            "graph": process.graph,
        }
    )


def trace_out(trace) -> TraceOut:
    return TraceOut(
        index=trace.index,
        case_id=trace.case_id,
        variant_id=trace.variant_id,
        started_at=trace.started_at,
        ended_at=trace.ended_at,
        duration_seconds=trace.duration_seconds,
        event_count=len(trace.events),
        activities=[e.activity or e.raw_label for e in trace.events],
    )
