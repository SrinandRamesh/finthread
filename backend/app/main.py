"""FastAPI application — creates app, CORS, includes both routers, startup sample load."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import core, intel

logger = logging.getLogger("finthread")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables
    init_db()
    logger.info("Database tables created.")

    # Load sample dataset on startup if configured
    if settings.LOAD_SAMPLE_ON_STARTUP:
        import os
        if os.path.exists(settings.SAMPLE_DATA_PATH):
            from app.state import get_current_result
            if get_current_result() is None:
                try:
                    from app.ingestion.loader import ingest_csv_file
                    from app.pipeline import run_analysis
                    dataset_info = ingest_csv_file(settings.SAMPLE_DATA_PATH, source="sample")
                    cfg = get_settings()
                    run_analysis(dataset_info.dataset_id, cfg)
                    logger.info("Sample dataset loaded and analysis completed on startup.")
                except Exception as e:
                    logger.warning(f"Failed to load sample on startup: {e}")
        else:
            logger.info(f"Sample file not found at {settings.SAMPLE_DATA_PATH}, skipping startup load.")

    yield


app = FastAPI(title="FinThread API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(core.router, prefix="/api")
app.include_router(intel.router, prefix="/api")
