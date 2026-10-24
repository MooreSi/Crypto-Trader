from fastapi import APIRouter

from backend.src.controllers import trades_controller

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("/open")
def open_trades() -> list[dict]:
    return trades_controller.open_trades()


@router.get("/history")
def history(limit: int = 200, offset: int = 0) -> list[dict]:
    return trades_controller.history(limit, offset)


@router.get("/stats")
def stats() -> dict:
    return trades_controller.stats()


@router.get("/decisions")
def decisions(limit: int = 100) -> list[dict]:
    return trades_controller.gate_decisions(limit)


@router.get("/{trade_id}/events")
def events(trade_id: int) -> list[dict]:
    return trades_controller.trade_events(trade_id)


@router.post("/{trade_id}/close")
def close(trade_id: int) -> dict:
    return {"closed": trades_controller.close(trade_id)}
