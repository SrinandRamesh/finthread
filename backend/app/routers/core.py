"""Core routes (Member 2). Endpoints 1-10 of the contract are added here step by step."""
from fastapi import APIRouter

from app import schemas

router = APIRouter(tags=["core"])


@router.get("/health", response_model=schemas.HealthOut)
def health() -> schemas.HealthOut:
    return schemas.HealthOut(status="ok", version="1.0.0", dataset_loaded=False, run_id=None)
