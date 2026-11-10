"""Persistência no MongoDB Atlas.

Coleções: ``processes`` (resumo, operações, grafo e variantes),
``traces`` (um documento por trace, para não estourar o limite de 16 MB de um
documento) e ``activities`` (catálogo).
"""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import datetime

from pymongo import ASCENDING, ReplaceOne
from pymongo.database import Database

from app.domain.model import (
    Activity,
    GraphEdge,
    GraphNode,
    LogEvent,
    Operation,
    Process,
    ProcessGraph,
    ProcessStatus,
    Trace,
    Variant,
)


def ensure_indexes(db: Database) -> None:
    db.traces.create_index([("processId", ASCENDING), ("index", ASCENDING)], unique=True)
    db.activities.create_index("nameKey", unique=True)


class MongoProcessRepository:
    def __init__(self, db: Database):
        self._db = db

    def add(self, process: Process, traces: list[Trace]) -> None:
        self._db.processes.insert_one(_process_doc(process))
        if traces:
            self._db.traces.insert_many([_trace_doc(process.id, t) for t in traces], ordered=False)

    def get(self, process_id: str) -> Process | None:
        doc = self._db.processes.find_one({"_id": process_id})
        return _process(doc) if doc else None

    def list(self) -> list[Process]:
        return [_process(d) for d in self._db.processes.find({}, {"graph": 0})]

    def save(self, process: Process) -> None:
        self._db.processes.replace_one({"_id": process.id}, _process_doc(process))

    def traces(self, process_id: str) -> list[Trace]:
        return [_trace(d) for d in self._db.traces.find({"processId": process_id}).sort("index", ASCENDING)]

    def replace_traces(self, process_id: str, traces: list[Trace]) -> None:
        if traces:
            self._db.traces.bulk_write(
                [ReplaceOne({"processId": process_id, "index": t.index}, _trace_doc(process_id, t), upsert=True) for t in traces],
                ordered=False,
            )

    def reset_traces(self, process_id: str, traces: list[Trace]) -> None:
        self._db.traces.delete_many({"processId": process_id})
        if traces:
            self._db.traces.insert_many([_trace_doc(process_id, t) for t in traces], ordered=False)

    def delete(self, process_id: str) -> bool:
        deleted = self._db.processes.delete_one({"_id": process_id}).deleted_count > 0
        self._db.traces.delete_many({"processId": process_id})
        return deleted


class MongoActivityRepository:
    def __init__(self, db: Database):
        self._db = db

    def list(self) -> list[Activity]:
        return [Activity(id=d["_id"], name=d["name"], description=d.get("description", "")) for d in self._db.activities.find()]

    def add(self, name: str, description: str = "") -> Activity:
        activity = Activity(id=str(uuid.uuid4()), name=name, description=description)
        self._db.activities.insert_one({"_id": activity.id, "name": name, "nameKey": name.casefold(), "description": description})
        return activity

    def ensure(self, activities: dict[str, str]) -> None:
        for name, description in activities.items():
            update: dict = {"$setOnInsert": {"_id": str(uuid.uuid4()), "name": name, "nameKey": name.casefold()}}
            if description:
                update["$set"] = {"description": description}
            else:
                update["$setOnInsert"]["description"] = ""
            self._db.activities.update_one({"nameKey": name.casefold()}, update, upsert=True)


def _process_doc(p: Process) -> dict:
    return {
        "_id": p.id,
        "name": p.name,
        "fileName": p.file_name,
        "format": p.format,
        "status": p.status.value,
        "createdAt": p.created_at,
        "updatedAt": p.updated_at,
        "startedAt": p.started_at,
        "endedAt": p.ended_at,
        "traceCount": p.trace_count,
        "eventCount": p.event_count,
        "operations": [asdict(o) for o in p.operations],
        "variants": [asdict(v) for v in p.variants],
        "graph": asdict(p.graph) if p.graph else None,
    }


def _process(d: dict) -> Process:
    graph = d.get("graph")
    return Process(
        id=d["_id"],
        name=d["name"],
        file_name=d.get("fileName", ""),
        format=d.get("format", ""),
        status=ProcessStatus(d["status"]),
        created_at=d["createdAt"],
        updated_at=d["updatedAt"],
        started_at=d.get("startedAt"),
        ended_at=d.get("endedAt"),
        trace_count=d.get("traceCount", 0),
        event_count=d.get("eventCount", 0),
        operations=[Operation(**o) for o in d.get("operations", [])],
        variants=[Variant(**v) for v in d.get("variants", [])],
        graph=ProcessGraph(
            nodes=[GraphNode(**n) for n in graph["nodes"]],
            edges=[GraphEdge(**e) for e in graph["edges"]],
        )
        if graph
        else None,
    )


def _trace_doc(process_id: str, t: Trace) -> dict:
    return {
        "processId": process_id,
        "index": t.index,
        "caseId": t.case_id,
        "startedAt": t.started_at,
        "endedAt": t.ended_at,
        "durationSeconds": t.duration_seconds,
        "variantId": t.variant_id,
        "events": [
            {"rawLabel": e.raw_label, "activity": e.activity, "occurredAt": e.occurred_at, "durationSeconds": e.duration_seconds}
            for e in t.events
        ],
    }


def _trace(d: dict) -> Trace:
    return Trace(
        case_id=d["caseId"],
        index=d["index"],
        started_at=d.get("startedAt"),
        ended_at=d.get("endedAt"),
        duration_seconds=d.get("durationSeconds"),
        variant_id=d.get("variantId"),
        events=[
            LogEvent(raw_label=e["rawLabel"], activity=e.get("activity"), occurred_at=e.get("occurredAt"), duration_seconds=e.get("durationSeconds"))
            for e in d.get("events", [])
        ],
    )


