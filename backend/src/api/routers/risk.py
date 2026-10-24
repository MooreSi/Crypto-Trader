from fastapi import APIRouter

from backend.src.api.schemas import RiskUpdate
from backend.src.controllers import risk_controller

router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.get("")
def get() -> dict:
    return risk_controller.get()


@router.get("/defaults")
def defaults() -> dict:
    return risk_controller.defaults()


@router.post("")
def update(body: RiskUpdate) -> dict:
    return risk_controller.update(body.fields)
