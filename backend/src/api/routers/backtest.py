from fastapi import APIRouter

from backend.src.api.schemas import BacktestRequest, TuneRequest
from backend.src.controllers import backtest_controller

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/strategies")
def strategies() -> list[dict]:
    return backtest_controller.strategies()


@router.post("")
def run(body: BacktestRequest) -> dict:
    return backtest_controller.run(body.strategy, body.coin, body.bars)


@router.post("/tune")
def tune(body: TuneRequest) -> dict:
    return backtest_controller.tune(body.strategy, body.coin, body.bars, body.folds)
