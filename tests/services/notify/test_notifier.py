"""Telegram trade alerts: every trade event, once, in order, never the backlog.

The notifier reads the `trade_events` audit trail (the record every money
change already writes) after each positions pass, so it needs no hook in
the order path: it cannot delay, change or fail an order.
"""
import pytest

from backend.src.db import database
from backend.src.services.engines.base import Signal
from backend.src.services.notify import notifier, telegram
from backend.src.services.positions import manager, trades_repo
from backend.src.services.risk import settings, sizing
from backend.src.services.trading import order_service


@pytest.fixture
def sent(monkeypatch):
    out = []
    monkeypatch.setattr(notifier, "_credentials", lambda: ("tok", "42"))
    monkeypatch.setattr(telegram, "send", lambda token, chat, text: out.append((token, chat, text)))
    return out


def _open(fx):
    sig = Signal(engine="trend_pa", coin="ETH", direction="long", entry=3000.0, stop=2970.0,
                 created_at=0, interval="1h", reason="test")
    market = next(m for m in fx.markets() if m.coin == "ETH")
    s = settings.defaults()
    d = sizing.compute(market, 10_000, 10_000, 3000.0, 2970.0, s)
    return trades_repo.get(order_service.open_trade(fx, market, sig, d, s, []))


def test_first_pass_skips_the_backlog_then_sends_new_events(fake_exchange, fixed_clock, sent):
    _open(fake_exchange)                     # history from before alerts were on
    assert notifier.notify_pass() == 0 and sent == []
    t = _open_second(fake_exchange)
    assert notifier.notify_pass() == 1
    assert "OPENED" in sent[0][2] and "SOL" in sent[0][2] and sent[0][:2] == ("tok", "42")
    assert notifier.notify_pass() == 0       # nothing twice
    assert t


def _open_second(fx):
    sig = Signal(engine="breakout", coin="SOL", direction="short", entry=150.0, stop=153.0,
                 created_at=0, interval="15m", reason="test")
    market = next(m for m in fx.markets() if m.coin == "SOL")
    s = settings.defaults()
    d = sizing.compute(market, 10_000, 10_000, 150.0, 153.0, s)
    return order_service.open_trade(fx, market, sig, d, s, [])


def test_tp_breakeven_and_close_are_reported(fake_exchange, fixed_clock, sent):
    notifier.notify_pass()                   # set the cursor on an empty trail
    t = _open(fake_exchange)
    now_ms = int(fixed_clock.now() * 1000)
    fake_exchange.fire(t["tp_oids"][0], 3030.0, now_ms + 1000)
    manager.manage(fake_exchange)
    fake_exchange.fire(trades_repo.get(t["id"])["sl_oid"], 3000.0, now_ms + 2000)
    manager.manage(fake_exchange)
    notifier.notify_pass()
    texts = [x[2] for x in sent]
    assert texts[0].startswith("[PAPER] OPENED")
    assert any(x.startswith("[PAPER] TP") for x in texts)
    assert any("Stop moved" in x and "breakeven" in x for x in texts)
    assert texts[-1].startswith("[PAPER] CLOSED") and "breakeven stop" in texts[-1]


def test_a_failed_send_is_retried_next_pass_not_skipped(fake_exchange, fixed_clock, monkeypatch):
    monkeypatch.setattr(notifier, "_credentials", lambda: ("tok", "42"))
    notifier.notify_pass()
    _open(fake_exchange)

    def boom(*_a):
        raise RuntimeError("telegram down")
    monkeypatch.setattr(telegram, "send", boom)
    assert notifier.notify_pass() == 0
    got = []
    monkeypatch.setattr(telegram, "send", lambda tok, chat, text: got.append(text))
    assert notifier.notify_pass() == 1 and "OPENED" in got[0]


def test_off_without_credentials(fake_exchange, monkeypatch):
    monkeypatch.setattr(notifier, "_credentials", lambda: None)
    assert notifier.notify_pass() == 0
    assert database.get_app_config(notifier.CURSOR_KEY) is None


def test_message_text_never_contains_a_key():
    text = telegram.format_event({"id": 1, "coin": "ETH", "direction": "long", "engine": "x",
                                  "network": "paper"},
                                 {"kind": "opened", "detail": {"fill": 1.0, "size": 2.0,
                                                               "risk_usd": 3.0}})
    assert text and "key" not in text.lower()
