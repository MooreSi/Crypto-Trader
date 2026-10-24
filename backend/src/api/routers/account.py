from fastapi import APIRouter

from backend.src.controllers import account_controller

router = APIRouter(prefix="/api", tags=["account"])


@router.get("/account")
def account() -> dict:
    return account_controller.account()


@router.get("/account/equity")
def equity(days: int = 30) -> list[dict]:
    return account_controller.equity_curve(days)


@router.get("/markets")
def markets() -> list[dict]:
    return account_controller.markets()


@router.get("/markets/{coin}/candles")
def candles(coin: str, interval: str = "15m", bars: int = 200) -> list[dict]:
    return account_controller.chart(coin, interval, bars)
