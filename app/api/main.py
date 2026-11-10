"""API HTTP do microsserviço de mineração de processos (MS1, MongoDB)."""


from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.api.container import Container
from app.api.schemas import (
    ActivityIn,
    ActivityOut,
    MappingIn,
    ProcessOut,
    ProcessSummaryOut,
    RenameIn,
    SeriesOut,
    SeriesPointOut,
    TraceOut,
    process_out,
    summary,
    trace_out,
)
from app.application.upload_process.handler import UploadProcess
from app.domain.errors import DomainError, NotFound

TAG_PROCESSES = "Processos"
TAG_ACTIVITIES = "Atividades"


def create_app(container_factory=None, cors_origins: list[str] | None = None) -> FastAPI:
    app = FastAPI(
        title="Driftor ASC · pmining",
        version="1.0.0",
        description=(
            "Microsserviço 1: upload de event log (XES/CSV), mapeamento de operações para atividades, "
            "grafo de processo (PM4Py) e CRUD de processos no MongoDB Atlas."
        ),
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=cors_origins or ["*"], allow_methods=["*"], allow_headers=["*"]
    )

    state: dict[str, Container] = {}

    def container() -> Container:
        if "c" not in state:
            if container_factory is None:
                from app.api.container import production_container

                state["c"] = production_container()
            else:
                state["c"] = container_factory()
        return state["c"]

    C = Annotated[Container, Depends(container)]

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, err: DomainError):
        status = 404 if isinstance(err, NotFound) else 422
        return JSONResponse(status_code=status, content={"detail": str(err)})

    @app.get("/health", tags=["Saúde"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "pmining"}

    @app.post("/processes", response_model=ProcessOut, status_code=201, tags=[TAG_PROCESSES],
              summary="Cria um processo a partir de um event log (status 'mapeando')")
    async def upload_process(c: C, name: Annotated[str, Form()], file: Annotated[UploadFile, File()]):
        content = await file.read()
        process = c.upload_process.handle(UploadProcess(name=name, file_name=file.filename or "", content=content))
        return process_out(process)

    @app.put("/processes/{process_id}/operations", response_model=ProcessOut, tags=[TAG_PROCESSES],
             summary="Mapeia operações para atividades e gera grafo e variantes (status 'pronto')")
    def map_operations(c: C, process_id: str, body: MappingIn):
        mapping = {item.raw_label: item.activity for item in body.operations}
        return process_out(c.map_operations.handle(process_id, mapping))

    @app.get("/processes", response_model=list[ProcessSummaryOut], tags=[TAG_PROCESSES], summary="Lista os processos")
    def list_processes(c: C):
        return [ProcessSummaryOut.model_validate(summary(p)) for p in c.list_processes.handle()]

    @app.get("/processes/{process_id}", response_model=ProcessOut, tags=[TAG_PROCESSES],
             summary="Detalhe do processo com operações, grafo e variantes")
    def get_process(c: C, process_id: str):
        return process_out(c.get_process.handle(process_id))

    @app.patch("/processes/{process_id}", response_model=ProcessOut, tags=[TAG_PROCESSES], summary="Renomeia o processo")
    def rename_process(c: C, process_id: str, body: RenameIn):
        return process_out(c.rename_process.handle(process_id, body.name))

    @app.delete("/processes/{process_id}", status_code=204, tags=[TAG_PROCESSES],
                summary="Exclui o processo e publica process-deleted")
    def delete_process(c: C, process_id: str):
        c.delete_process.handle(process_id)
        return Response(status_code=204)

    @app.get("/processes/{process_id}/traces", response_model=list[TraceOut], tags=[TAG_PROCESSES],
             summary="Traces do processo, opcionalmente de uma variante")
    def list_traces(c: C, process_id: str, variant_id: Annotated[str | None, Query(alias="variantId")] = None):
        return [trace_out(t) for t in c.list_traces.handle(process_id, variant_id)]

    @app.get("/processes/{process_id}/series", response_model=SeriesOut, tags=[TAG_PROCESSES],
             summary="Série de duração por trace (entrada do ADWIN)")
    def get_series(c: C, process_id: str, activity: Annotated[list[str] | None, Query()] = None):
        points = c.get_series.handle(process_id, activity)
        return SeriesOut(
            process_id=process_id,
            activities=activity or [],
            points=[SeriesPointOut.model_validate(p) for p in points],
        )

    @app.get("/activities", response_model=list[ActivityOut], tags=[TAG_ACTIVITIES], summary="Catálogo de atividades")
    def list_activities(c: C):
        return [ActivityOut.model_validate(a) for a in c.activities.list()]

    @app.post("/activities", response_model=ActivityOut, status_code=201, tags=[TAG_ACTIVITIES], summary="Cria uma atividade")
    def create_activity(c: C, body: ActivityIn):
        return ActivityOut.model_validate(c.activities.create(body.name))

    return app


def _default_app() -> FastAPI:
    from app.infrastructure.settings import Settings

    return create_app(cors_origins=Settings.from_env().cors_origins)


app = _default_app()
