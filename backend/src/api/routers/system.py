from fastapi import APIRouter

from backend.src.api.schemas import Paused
from backend.src.controllers import system_controller

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def status() -> dict:
    return system_controller.status()


@router.get("/version")
def version() -> dict:
    return system_controller.version()


@router.get("/releases")
def releases() -> list[dict]:
    return system_controller.releases()


@router.post("/pause")
def pause(body: Paused) -> dict:
    return system_controller.set_paused(body.paused)
