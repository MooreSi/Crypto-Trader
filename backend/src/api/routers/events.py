from fastapi import APIRouter

from backend.src.api.schemas import NewEvent
from backend.src.controllers import events_controller

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
def upcoming(days: int = 7) -> list[dict]:
    return events_controller.upcoming(days)


@router.get("/kinds")
def kinds() -> dict:
    return events_controller.kinds()


@router.post("")
def add(body: NewEvent) -> dict:
    return events_controller.add(body.ts, body.title, body.impact, body.kind, body.coins)


@router.post("/refresh")
def refresh() -> dict:
    return {"events": events_controller.refresh()}


@router.delete("/{event_id}")
def delete(event_id: int) -> dict:
    return {"deleted": events_controller.delete(event_id)}
