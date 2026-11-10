import pytest

from app.application.upload_log.handler import UploadLog
from app.domain.errors import InvalidInput, NotFound
from app.domain.model import ProcessStatus
from tests.fakes import CSV_LOG, memory_container, xes


def upload(c, name="Torno", content=CSV_LOG, file_name="torno.csv"):
    process = c.create_process.handle(name)
    return c.upload_log.handle(UploadLog(process_id=process.id, file_name=file_name, content=content))


def test_create_process_starts_empty_and_cannot_be_mapped():
    c, *_ = memory_container()
    process = c.create_process.handle(" Torno  01 ")
    assert process.name == "Torno 01" and process.status == ProcessStatus.EMPTY
    assert process.operations == [] and process.trace_count == 0
    with pytest.raises(InvalidInput):
        c.map_operations.handle(process.id, {})


def test_new_log_replaces_previous_one():
    c, processes, _, _ = memory_container()
    process = upload(c)
    c.map_operations.handle(process.id, {"Alimentacao": "A", "Usinagem": "U", "Retirada": "R"})
    small = "\n".join(CSV_LOG.decode().splitlines()[:4]).encode()
    again = c.upload_log.handle(UploadLog(process_id=process.id, file_name="t2.csv", content=small))
    assert again.status == ProcessStatus.MAPPING and again.graph is None and again.variants == []
    assert again.trace_count == 1 and len(processes.traces(process.id)) == 1


def test_mapping_saves_optional_descriptions_in_catalog():
    c, _, activities, _ = memory_container(catalog=["Usinagem"])
    process = upload(c)
    c.map_operations.handle(
        process.id,
        {"Alimentacao": "Alimentação", "Usinagem": "Usinagem", "Retirada": "Retirada"},
        {"alimentação": "Peça entra na máquina", "Usinagem": "Corte"},
    )
    by_name = {a.name: a.description for a in activities.list()}
    assert by_name == {"Usinagem": "Corte", "Alimentação": "Peça entra na máquina", "Retirada": ""}


def test_upload_returns_operations_with_suggestions():
    c, _, _, _ = memory_container(catalog=["usinagem"])
    process = upload(c)
    assert process.status == ProcessStatus.MAPPING
    assert process.trace_count == 3
    labels = {op.raw_label: op for op in process.operations}
    assert labels["Usinagem"].occurrence_count == 4
    assert labels["Usinagem"].suggested_activity == "usinagem"
    assert labels["Retirada"].suggested_activity == "Retirada"


def test_upload_rejects_empty_name_and_unknown_format():
    c, *_ = memory_container()
    with pytest.raises(InvalidInput):
        upload(c, name="  ")
    with pytest.raises(InvalidInput):
        upload(c, file_name="log.txt")
    with pytest.raises(NotFound):
        c.upload_log.handle(UploadLog(process_id="nope", file_name="t.csv", content=CSV_LOG))


def test_mapping_builds_graph_variants_and_catalog():
    c, _, activities, _ = memory_container()
    process = upload(c)
    mapped = c.map_operations.handle(
        process.id, {"Alimentacao": "Alimentação", "Usinagem": "Usinagem", "Retirada": "Retirada"}
    )
    assert mapped.status == ProcessStatus.READY
    assert {n.label for n in mapped.graph.nodes} == {"Alimentação", "Usinagem", "Retirada"}
    edges = {(e.source, e.target): e.frequency for e in mapped.graph.edges}
    assert edges[("Alimentação", "Usinagem")] == 3
    assert edges[("Usinagem", "Usinagem")] == 1
    assert [v.trace_count for v in mapped.variants] == [2, 1]
    assert {a.name for a in activities.list()} == {"Alimentação", "Usinagem", "Retirada"}


def test_series_requires_mapping_then_uses_activity_sojourn():
    c, *_ = memory_container()
    process = upload(c)
    with pytest.raises(InvalidInput):
        c.get_series.handle(process.id)
    c.map_operations.handle(process.id, {"Alimentacao": "A", "Usinagem": "U", "Retirada": "R"})
    assert [p.value for p in c.get_series.handle(process.id, ["U"])] == [40.0, 50.0, 70.0]
    assert len(c.get_series.handle(process.id)) == 3


def test_rename_and_delete_publish_event():
    c, _, _, publisher = memory_container()
    process = upload(c)
    assert c.rename_process.handle(process.id, " Torno 02 ").name == "Torno 02"
    c.delete_process.handle(process.id)
    assert publisher.sent[0][0] == "process-deleted"
    assert publisher.sent[0][1]["processId"] == process.id
    with pytest.raises(NotFound):
        c.get_process.handle(process.id)
    with pytest.raises(NotFound):
        c.delete_process.handle(process.id)


def test_xes_lifecycle_becomes_event_duration():
    c, *_ = memory_container()
    content = xes(
        [
            ("1", "Machine_Operating", "start", "2020-06-18T00:00:00.000+00:00"),
            ("1", "Machine_Operating", "complete", "2020-06-18T00:00:30.000+00:00"),
            ("2", "Machine_Operating", "start", "2020-06-18T00:01:00.000+00:00"),
            ("2", "Machine_Operating", "complete", "2020-06-18T00:01:45.000+00:00"),
        ]
    )
    process = upload(c, content=content, file_name="mini.xes")
    c.map_operations.handle(process.id, {"Machine_Operating": "Machine_Operating"})
    assert [p.value for p in c.get_series.handle(process.id, ["Machine_Operating"])] == [30.0, 45.0]
