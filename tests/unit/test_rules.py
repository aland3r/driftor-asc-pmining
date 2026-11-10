from datetime import datetime, timedelta, timezone

import pytest

from app.domain.errors import InvalidInput
from app.domain.model import Activity, LogEvent, Operation, Trace
from app.domain.rules import build_variants, duration_series, histogram, node_metrics, suggest_activity, validate_mapping

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def trace(i, labels, durations=None, start_offset=0):
    durations = durations or [1.0] * len(labels)
    return Trace(
        case_id=str(i),
        index=i,
        started_at=T0 + timedelta(minutes=start_offset),
        ended_at=None,
        duration_seconds=float(sum(durations)),
        events=[LogEvent(raw_label=l, occurred_at=None, duration_seconds=d, activity=l) for l, d in zip(labels, durations)],
    )


def test_suggestion_reuses_catalog_name_ignoring_case():
    catalog = [Activity(id="1", name="Machine Operating")]
    assert suggest_activity("machine   operating", catalog) == "Machine Operating"
    assert suggest_activity(" Nova  etapa ", catalog) == "Nova etapa"


def test_mapping_must_cover_every_operation():
    ops = [Operation("A", 1, 1, 0, "A"), Operation("B", 1, 1, 0, "B")]
    with pytest.raises(InvalidInput):
        validate_mapping(ops, {"A": "Alfa"})
    with pytest.raises(InvalidInput):
        validate_mapping(ops, {"A": "Alfa", "B": "  "})
    with pytest.raises(InvalidInput):
        validate_mapping(ops, {"A": "x", "B": "y", "C": "z"})
    assert validate_mapping(ops, {"A": " Alfa ", "B": "Beta"}) == {"A": "Alfa", "B": "Beta"}


def test_variants_are_ordered_by_frequency_and_tag_traces():
    traces = [trace(1, ["a", "b"]), trace(2, ["a", "c"]), trace(3, ["a", "b"])]
    variants = build_variants(traces)
    assert [v.label for v in variants] == ["Variante 1", "Variante 2"]
    assert variants[0].sequence == ["a", "b"] and variants[0].trace_count == 2
    assert [t.variant_id for t in traces] == ["v1", "v2", "v1"]


def test_node_metrics_count_repetitions_and_ends():
    nodes = node_metrics([trace(1, ["a", "b", "b"], [1, 2, 4]), trace(2, ["a", "b"], [1, 6])])
    assert nodes["b"].frequency == 3
    assert nodes["b"].case_frequency == 2
    assert nodes["b"].max_repetitions == 2
    assert nodes["b"].end_frequency == 2
    assert nodes["a"].start_frequency == 2
    assert nodes["b"].median_duration_seconds == 4


def test_series_whole_trace_or_selected_activity_in_time_order():
    traces = [trace(1, ["a", "b"], [1, 5], start_offset=10), trace(2, ["a", "b"], [2, 7], start_offset=0)]
    whole = duration_series(traces)
    assert [(p.index, p.case_id, p.value) for p in whole] == [(1, "2", 9.0), (2, "1", 6.0)]
    only_b = duration_series(traces, {"b"})
    assert [p.value for p in only_b] == [7.0, 5.0]


def test_histogram_bins():
    assert histogram([]) == []
    assert sum(histogram([1, 2, 3, 4, 100])) == 5
    assert histogram([5, 5])[0] == 2
