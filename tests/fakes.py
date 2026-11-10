from __future__ import annotations

import copy
import itertools
from datetime import datetime, timezone

from app.api.container import build_container
from app.domain.model import Activity
from app.infrastructure.events import LogOnlyPublisher
from app.infrastructure.graph_miner import Pm4pyGraphMiner
from app.infrastructure.log_parser import PandasLogParser


class MemoryProcesses:
    def __init__(self):
        self.processes = {}
        self.trace_store = {}

    def add(self, process, traces):
        self.processes[process.id] = copy.deepcopy(process)
        self.trace_store[process.id] = copy.deepcopy(traces)

    def get(self, process_id):
        p = self.processes.get(process_id)
        return copy.deepcopy(p) if p else None

    def list(self):
        return [copy.deepcopy(p) for p in self.processes.values()]

    def save(self, process):
        self.processes[process.id] = copy.deepcopy(process)

    def traces(self, process_id):
        return copy.deepcopy(self.trace_store.get(process_id, []))

    def replace_traces(self, process_id, traces):
        self.trace_store[process_id] = copy.deepcopy(traces)

    def delete(self, process_id):
        self.trace_store.pop(process_id, None)
        return self.processes.pop(process_id, None) is not None


class MemoryActivities:
    def __init__(self, names=()):
        self.items = [Activity(id=f"a{i}", name=n) for i, n in enumerate(names)]

    def list(self):
        return list(self.items)

    def add(self, name):
        a = Activity(id=f"a{len(self.items)}", name=name)
        self.items.append(a)
        return a

    def ensure(self, names):
        known = {a.name.casefold() for a in self.items}
        for n in names:
            if n.casefold() not in known:
                self.add(n)


class FixedClock:
    def now(self):
        return datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)


class SeqIds:
    def __init__(self):
        self._c = itertools.count(1)

    def new_id(self):
        return f"p{next(self._c)}"


def memory_container(catalog=()):
    processes, activities, publisher = MemoryProcesses(), MemoryActivities(catalog), LogOnlyPublisher()
    c = build_container(processes, activities, PandasLogParser(), Pm4pyGraphMiner(), publisher, FixedClock(), SeqIds())
    return c, processes, activities, publisher


def xes(events):
    """events: (case, activity, transition, iso timestamp)."""
    by_case = {}
    for case, activity, transition, ts in events:
        by_case.setdefault(case, []).append((activity, transition, ts))
    traces = "".join(
        '<trace><string key="concept:name" value="%s"/>%s</trace>'
        % (
            case,
            "".join(
                '<event><string key="concept:name" value="%s"/><string key="lifecycle:transition" value="%s"/>'
                '<date key="time:timestamp" value="%s"/></event>' % row
                for row in rows
            ),
        )
        for case, rows in by_case.items()
    )
    return ('<?xml version="1.0" encoding="UTF-8"?><log xes.version="1.0">%s</log>' % traces).encode()


CSV_LOG = "\n".join(
    [
        "Case;Atividade;Inicio;Fim;Tempo(s)",
        "1;Alimentacao;19-01-2012 07:54:31;19-01-2012 07:54:46;15",
        "1;Usinagem;19-01-2012 07:54:46;19-01-2012 07:55:26;40",
        "1;Retirada;19-01-2012 07:55:26;19-01-2012 07:55:29;3",
        "2;Alimentacao;19-01-2012 07:55:29;19-01-2012 07:55:47;18",
        "2;Usinagem;19-01-2012 07:55:47;19-01-2012 07:56:37;50",
        "2;Retirada;19-01-2012 07:56:37;19-01-2012 07:56:40;3",
        "3;Alimentacao;19-01-2012 07:56:40;19-01-2012 07:56:50;10",
        "3;Usinagem;19-01-2012 07:56:50;19-01-2012 07:57:40;50",
        "3;Usinagem;19-01-2012 07:57:40;19-01-2012 07:58:00;20",
        "3;Retirada;19-01-2012 07:58:00;19-01-2012 07:58:03;3",
    ]
).encode()
