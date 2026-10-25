"""Performance analytics over closed trades and the equity curve."""
import math

import pytest

from backend.src.services.positions import analytics


def _t(engine, net, risk=10.0, opened=0.0, hours=2.0):
    return {"engine": engine, "status": "closed", "realised_pnl": net + 1.0, "fees": 1.0,
            "risk_usd": risk, "opened_at": opened, "closed_at": opened + hours * 3600}


def test_headline_numbers():
    trades = [_t("breakout", 20), _t("breakout", -10), _t("reversal", 15), _t("reversal", -10),
              _t("reversal", -10)]
    a = analytics.compute(trades, [])
    assert a["closed"] == 5 and a["net_pnl"] == pytest.approx(5.0)
    assert a["win_rate"] == pytest.approx(0.4)
    assert a["profit_factor"] == pytest.approx(35 / 30)
    assert a["expectancy_r"] == pytest.approx((2 - 1 + 1.5 - 1 - 1) / 5)
    assert a["avg_win"] == pytest.approx(17.5) and a["avg_loss"] == pytest.approx(-10.0)
    assert a["longest_losing_streak"] == 2
    assert a["avg_hold_hours"] == pytest.approx(2.0)


def test_per_engine_breakdown():
    a = analytics.compute([_t("breakout", 20), _t("breakout", -10), _t("reversal", -5)], [])
    b = a["by_engine"]["breakout"]
    assert b["trades"] == 2 and b["net_pnl"] == pytest.approx(10.0) and b["win_rate"] == 0.5
    assert a["by_engine"]["reversal"]["profit_factor"] is None


def test_max_drawdown_from_the_equity_curve():
    eq = [{"ts": i * 3600.0, "equity": e} for i, e in enumerate([100, 120, 90, 110, 80, 130])]
    a = analytics.compute([], eq)
    assert a["max_drawdown_pct"] == pytest.approx((120 - 80) / 120 * 100)


def test_sharpe_from_daily_returns():
    # one point per day: +1%, -1%, +2%
    eq = [{"ts": d * 86400.0, "equity": e} for d, e in enumerate([100, 101, 99.99, 101.9898])]
    a = analytics.compute([], eq)
    rets = [0.01, -0.01, 0.02]
    mean = sum(rets) / 3
    sd = math.sqrt(sum((r - mean) ** 2 for r in rets) / 2)
    assert a["sharpe"] == pytest.approx(mean / sd * math.sqrt(365), rel=1e-3)


def test_nothing_yet():
    a = analytics.compute([], [])
    assert a["closed"] == 0 and a["win_rate"] is None and a["sharpe"] is None
    assert a["max_drawdown_pct"] == 0.0 and a["by_engine"] == {}
