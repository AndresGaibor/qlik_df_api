import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.models import AutomationRun
from app.qlik.automation import QlikAutomation, QlikAutomationError
from app.schemas import ApiResponse, QlikRunRequest, RunData

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=ApiResponse[dict[str, str]])
async def health() -> ApiResponse[dict[str, str]]:
    return ApiResponse(data={"status": "ok"})


@router.post("/api/v1/qlik/runs", response_model=ApiResponse[RunData])
async def create_qlik_run(request: Request, payload: QlikRunRequest) -> ApiResponse[RunData]:
    settings = request.app.state.settings
    session_factory = request.app.state.session_factory
    run = AutomationRun(status="running", space_name=payload.space, dataflow_name=payload.dataflow)

    async with session_factory() as session:
        session.add(run)
        await session.commit()
        await session.refresh(run)

        try:
            result = await QlikAutomation(settings).run(
                tenant_name=payload.tenant,
                space_name=payload.space,
                dataflow_name=payload.dataflow,
                headless=payload.headless,
            )
            run.status = "completed"
            run.tenant_name = result["selected_tenant"]["name"]
            run.space_name = result["space"]["name"]
            selected_dataflows = result["selected_dataflows"]
            run.dataflow_name = (
                selected_dataflows[0]["name"] if len(selected_dataflows) == 1 else None
            )
            run.downloaded_files = json.dumps(result["downloaded_files"])
        except (ValueError, QlikAutomationError) as error:
            run.status = "failed"
            run.error = str(error)
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
            ) from error
        except Exception as error:
            run.status = "failed"
            run.error = "Error interno durante la automatizacion Qlik"
            await session.commit()
            logger.exception("Error inesperado durante la automatizacion Qlik")
            detail = "No se pudo completar la automatizacion Qlik"
            if settings.app_env == "development":
                detail = f"{type(error).__name__}: {error}"
            raise HTTPException(
                status_code=502, detail=detail
            ) from error

        await session.commit()
        await session.refresh(run)
        return ApiResponse(data=RunData.model_validate(run))


@router.get("/api/v1/qlik/runs", response_model=ApiResponse[list[RunData]])
async def list_qlik_runs(
    request: Request, limit: int = 20, offset: int = 0
) -> ApiResponse[list[RunData]]:
    if limit < 1 or limit > 100 or offset < 0:
        raise HTTPException(
            status_code=400, detail="limit debe estar entre 1 y 100; offset no puede ser negativo"
        )
    async with request.app.state.session_factory() as session:
        result = await session.scalars(
            select(AutomationRun)
            .order_by(AutomationRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return ApiResponse(data=[RunData.model_validate(run) for run in result.all()])
