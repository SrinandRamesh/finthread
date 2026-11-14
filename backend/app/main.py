from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import core, intel

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Step 1 adds: create DB tables. Step 2 adds: load the sample dataset if LOAD_SAMPLE_ON_STARTUP.
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
