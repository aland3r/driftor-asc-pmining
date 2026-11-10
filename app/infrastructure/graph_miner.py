"""Adapter: o PM4Py descobre o grafo de sequência direta (DFG) com interface
própria (dicionário de pares). Aqui ele é convertido em arestas do domínio."""

from __future__ import annotations

import pandas as pd

from app.domain.model import GraphEdge, Trace


class Pm4pyGraphMiner:
    def edges(self, traces: list[Trace]) -> list[GraphEdge]:
        rows = [
            {
                "case_id": trace.case_id,
                "activity": event.activity or event.raw_label,
                # O DFG precisa de ordem; a posição no trace desempata timestamps iguais.
                "timestamp": pd.Timestamp("2000-01-01", tz="UTC") + pd.Timedelta(seconds=position),
            }
            for trace in traces
            for position, event in enumerate(trace.events)
        ]
        if not rows:
            return []
        import pm4py  # import tardio: o pm4py é pesado

        dfg, _starts, _ends = pm4py.discover_dfg(
            pd.DataFrame(rows), case_id_key="case_id", activity_key="activity", timestamp_key="timestamp"
        )
        return [GraphEdge(source=s, target=t, frequency=int(n)) for (s, t), n in dfg.items()]
