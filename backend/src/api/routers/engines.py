from fastapi import APIRouter

from backend.src.api.schemas import Toggle
from backend.src.controllers import engines_controller

router = APIRouter(prefix="/api/engines", tags=["engines"])


@router.get("")
def engines() -> list[dict]:
    return engines_controller.list_status()


@router.post("/{name}/enabled")
def enabled(name: str, body: Toggle) -> dict:
    return engines_controller.set_enabled(name, body.on)


@router.post("/{name}/live")
def live(name: str, body: Toggle) -> dict:
    return engines_controller.set_live(name, body.on)


@router.get("/{name}/signals")
def signals(name: str, limit: int = 100) -> list[dict]:
    return engines_controller.signals(name, limit)


@router.post("/{name}/retrain")
def retrain(name: str) -> dict:
    return engines_controller.retrain(name)
