from src.setup_env import bootstrap_environment

bootstrap_environment()

import asyncio
import logging
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from decouple import config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.controllers.auth_controller import router as auth_router
from src.controllers.health_controller import router as health_router
from src.controllers.reels_controller import router as reels_router
from src.controllers.rubrica_controller import router as rubrica_router
from src.db import init_db
from src.services.pipeline_services import PipelineServices
from src.services.token_watch_service import check_instagram_token

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("audiencia")

scheduler = AsyncIOScheduler()
pipeline = PipelineServices()


async def _scheduled_pipeline() -> None:
    try:
        await pipeline.run()
    except Exception:
        logger.exception("el pipeline falló")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    secret = (config("ECOSYSTEM_SESSION_SECRET", default="") or "").strip()
    if len(secret) < 32:
        raise RuntimeError("ECOSYSTEM_SESSION_SECRET debe tener al menos 32 caracteres aleatorios")
    init_db()
    scheduler.add_job(
        _scheduled_pipeline,
        IntervalTrigger(minutes=30),
        id="audiencia-pipeline",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        check_instagram_token,
        CronTrigger(hour=9, minute=0, timezone=ZoneInfo("America/Argentina/Buenos_Aires")),
        id="audiencia-token-watch",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    asyncio.get_running_loop().create_task(_scheduled_pipeline())
    logger.info("pipeline programado cada 30 minutos")
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(title="ATV Audiencia", lifespan=lifespan)

_origins = [item.strip() for item in (config("CORS_ORIGINS", default="") or "").split(",") if item.strip()]
if not _origins:
    _origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "PUT", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(reels_router)
app.include_router(rubrica_router)
