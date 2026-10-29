from fastapi import APIRouter

from backend.src.api.schemas import StrategyIn
from backend.src.controllers import strategy_controller

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("")
def list_all() -> dict:
    return strategy_controller.list_all()


@router.post("")
def create(body: StrategyIn) -> dict:
    return strategy_controller.create(body.name, body.params, body.notes)


@router.put("/{sid}")
def update(sid: str, body: StrategyIn) -> dict:
    return strategy_controller.update(sid, body.name, body.params, body.notes)


@router.delete("/{sid}")
def delete(sid: str) -> dict:
    return strategy_controller.delete(sid)


@router.post("/{sid}/activate")
def activate(sid: str) -> dict:
    return strategy_controller.activate(sid)
