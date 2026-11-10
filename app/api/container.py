"""Composição: liga as portas da aplicação às implementações de infraestrutura."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.activities.handler import ActivitiesHandler
from app.application.create_process.handler import CreateProcessHandler
from app.application.delete_process.handler import DeleteProcessHandler
from app.application.get_process.handler import GetProcessHandler
from app.application.get_series.handler import GetSeriesHandler
from app.application.list_processes.handler import ListProcessesHandler
from app.application.list_traces.handler import ListTracesHandler
from app.application.map_operations.handler import MapOperationsHandler
from app.application.rename_process.handler import RenameProcessHandler
from app.application.upload_log.handler import UploadLogHandler


@dataclass
class Container:
    create_process: CreateProcessHandler
    upload_log: UploadLogHandler
    map_operations: MapOperationsHandler
    list_processes: ListProcessesHandler
    get_process: GetProcessHandler
    rename_process: RenameProcessHandler
    delete_process: DeleteProcessHandler
    get_series: GetSeriesHandler
    list_traces: ListTracesHandler
    activities: ActivitiesHandler


def build_container(processes, activities, parser, miner, publisher, clock, ids) -> Container:
    return Container(
        create_process=CreateProcessHandler(processes, clock, ids),
        upload_log=UploadLogHandler(parser, processes, activities, clock),
        map_operations=MapOperationsHandler(processes, activities, miner, clock),
        list_processes=ListProcessesHandler(processes),
        get_process=GetProcessHandler(processes),
        rename_process=RenameProcessHandler(processes, clock),
        delete_process=DeleteProcessHandler(processes, publisher, clock),
        get_series=GetSeriesHandler(processes),
        list_traces=ListTracesHandler(processes),
        activities=ActivitiesHandler(activities),
    )


def production_container() -> Container:
    from pymongo import MongoClient

    from app.infrastructure.events import LogOnlyPublisher, ServiceBusPublisher
    from app.infrastructure.graph_miner import Pm4pyGraphMiner
    from app.infrastructure.log_parser import PandasLogParser
    from app.infrastructure.mongo_repositories import MongoActivityRepository, MongoProcessRepository, ensure_indexes
    from app.infrastructure.settings import Settings
    from app.infrastructure.system import UtcClock, UuidGenerator

    settings = Settings.from_env()
    db = MongoClient(settings.mongodb_uri, tz_aware=True)[settings.mongodb_db]
    ensure_indexes(db)
    publisher = ServiceBusPublisher(settings.servicebus_connection) if settings.servicebus_connection else LogOnlyPublisher()
    return build_container(
        processes=MongoProcessRepository(db),
        activities=MongoActivityRepository(db),
        parser=PandasLogParser(),
        miner=Pm4pyGraphMiner(),
        publisher=publisher,
        clock=UtcClock(),
        ids=UuidGenerator(),
    )
