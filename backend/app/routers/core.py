"""Core routes (Member 2). Endpoints 1-10 of the contract are added here step by step."""
from fastapi import APIRouter

from app import schemas
from app.state import get_current_result

router = APIRouter(tags=["core"])


@router.get("/health", response_model=schemas.HealthOut)
def health() -> schemas.HealthOut:
    result = get_current_result()
    return schemas.HealthOut(
        status="ok",
        version="1.0.0",
        dataset_loaded=result is not None,
        run_id=result.run_id if result else None,
    )
