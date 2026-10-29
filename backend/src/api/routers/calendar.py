from fastapi import APIRouter, Path, Query

from backend.src.api.schemas import JournalIn
from backend.src.controllers import calendar_controller

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

# Shape only: whether it is a real date is the service's question, and an end
# of YYYY-MM-31 is deliberate (a whole month for any month).
DAY = r"^\d{4}-\d{2}-\d{2}$"


@router.get("/trades")
def trades(days: int = Query(365, ge=1, le=730)) -> dict:
    return calendar_controller.trades(days)


@router.get("/events")
def events(start: str = Query(..., pattern=DAY), end: str = Query(..., pattern=DAY)) -> dict:
    return {"events": calendar_controller.events(start, end)}


@router.get("/journal")
def journal(start: str = Query(..., pattern=DAY), end: str = Query(..., pattern=DAY)) -> dict:
    return {"entries": calendar_controller.journal_between(start, end)}


@router.post("/journal/{day}")
def save_journal(body: JournalIn, day: str = Path(..., pattern=DAY)) -> dict:
    return {"entry": calendar_controller.save_journal(day, body.note, body.tags, body.mood)}
