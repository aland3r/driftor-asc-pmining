import mongomock

from app.api.container import build_container
from app.application.upload_process.handler import UploadProcess
from app.infrastructure.events import LogOnlyPublisher
from app.infrastructure.graph_miner import Pm4pyGraphMiner
from app.infrastructure.log_parser import PandasLogParser
from app.infrastructure.mongo_repositories import MongoActivityRepository, MongoProcessRepository, ensure_indexes
from tests.fakes import CSV_LOG, FixedClock, SeqIds


def test_round_trip_in_mongo():
    db = mongomock.MongoClient(tz_aware=True)["pmining"]
    ensure_indexes(db)
    c = build_container(MongoProcessRepository(db), MongoActivityRepository(db), PandasLogParser(), Pm4pyGraphMiner(), LogOnlyPublisher(), FixedClock(), SeqIds())
    process = c.upload_process.handle(UploadProcess(name="Torno", file_name="t.csv", content=CSV_LOG))
    assert db.traces.count_documents({"processId": process.id}) == 3
    c.map_operations.handle(process.id, {"Alimentacao": "A", "Usinagem": "U", "Retirada": "R"})
    loaded = c.get_process.handle(process.id)
    assert loaded.graph is not None and len(loaded.variants) == 2
    assert {t.variant_id for t in c.list_traces.handle(process.id)} == {"v1", "v2"}
    assert db.activities.count_documents({}) == 3
    c.delete_process.handle(process.id)
    assert db.traces.count_documents({}) == 0
