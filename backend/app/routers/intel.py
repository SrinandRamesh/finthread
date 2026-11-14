"""TEMPORARY STUB created by the Integration Lead at kickoff.
Member 3 owns this file and replaces it completely on feat/intel."""
from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["intel"])


def _not_ready() -> None:
    raise HTTPException(status_code=501, detail="Not implemented yet")


@router.get("/overview")
def overview():
    _not_ready()


@router.get("/clusters")
def clusters():
    _not_ready()


@router.get("/clusters/{cluster_id}")
def cluster_detail(cluster_id: str):
    _not_ready()


@router.get("/alerts")
def alerts():
    _not_ready()


@router.get("/evaluation")
def evaluation():
    _not_ready()
