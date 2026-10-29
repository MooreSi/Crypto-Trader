"""Strategies: named sets of the risk settings that shape a trade.

A strategy owns the settings in `KEYS`: how much is risked, which signals
pass, how the trade is exited and the portfolio limits. Activating one
writes its values into the risk settings (`settings.update`), which is what
the executor and the position manager read, so nothing downstream knows
strategies exist. Editing the active strategy re-applies it. The master
switch, margin mode and the watch/block lists are never part of one.

Values go through `settings.normalise`, so a strategy is clamped to the same
envelope as the Risk page and cannot hold anything the Risk page could not.

`ensure_default()` creates and activates the built-in "TP1 80% at 1.5R +
trailed runner" once per account database, copying every non-exit value from
the settings in force so only the exits change (owner, 2026-10-29; see
docs/specs/001-strategies.md for the trail-distance study).
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from backend.src.services.risk import settings, strategies_repo
from backend.src.utils import clock

KEYS: tuple[str, ...] = (
    # sizing
    "risk_per_trade_pct", "max_leverage", "max_position_notional_pct", "min_stop_pct",
    "entry_slippage_pct",
    # entry filters
    "min_reward_risk", "ml_min_probability", "ml_require_model", "max_funding_rate_pct",
    "blackout_enabled", "blackout_include_medium", "blackout_minutes_before",
    "blackout_minutes_after",
    # exits
    "tp_ladder", "breakeven_after_tp", "stop_lock_r", "trail_atr_mult",
    # portfolio and day
    "max_open_positions", "max_same_direction", "daily_loss_limit_pct",
    "daily_profit_target_usd",
)

DEFAULT_NAME = "TP1 80% at 1.5R + trailed runner"
DEFAULT_NOTES = ("Closes 80% at 1.5R, moves the stop to TP1 and trails the last 20% at "
                 "1.5 x ATR(15m). A runner under $11.20 is closed at TP1 with the rest.")
DEFAULT_EXITS: dict[str, Any] = {"tp_ladder": [[1.5, 0.8]], "breakeven_after_tp": 1,
                                 "stop_lock_r": 1.5, "trail_atr_mult": 1.5}
MAX_NAME = 60


def _load() -> Optional[dict]:
    raw = strategies_repo.load()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _store() -> dict:
    return _load() or {"active": None, "items": []}


def _save(data: dict) -> None:
    strategies_repo.save(json.dumps(data))


def _find(data: dict, sid: str) -> dict:
    for item in data["items"]:
        if item["id"] == sid:
            return item
    raise KeyError(sid)


def _params(raw: dict, base: dict) -> dict:
    extra = sorted(set(raw) - set(KEYS))
    if extra:
        raise ValueError(f"a strategy cannot set {', '.join(extra)}")
    out = {k: base[k] for k in KEYS}
    out.update(settings.normalise(raw))
    return out


def _name(data: dict, name: str, sid: Optional[str] = None) -> str:
    name = (name or "").strip()
    if not name or len(name) > MAX_NAME:
        raise ValueError(f"a strategy needs a name of 1 to {MAX_NAME} characters")
    if any(i["name"].lower() == name.lower() and i["id"] != sid for i in data["items"]):
        raise ValueError(f"a strategy called {name!r} already exists")
    return name


def list_all() -> dict:
    data = _store()
    current = settings.get()
    drift: list[str] = []
    if data["active"]:
        try:
            active = _find(data, data["active"])["params"]
            drift = [k for k in KEYS if k in active and active[k] != current[k]]
        except KeyError:
            data["active"] = None
    return {"active": data["active"], "items": data["items"], "drift": drift,
            "keys": list(KEYS), "current": {k: current[k] for k in KEYS}}


def create(name: str, params: dict, notes: str = "") -> dict:
    data = _store()
    now = clock.now()
    item = {"id": uuid.uuid4().hex[:12], "name": _name(data, name),
            "notes": (notes or "").strip()[:500], "params": _params(params, settings.get()),
            "created_at": now, "updated_at": now}
    data["items"].append(item)
    _save(data)
    return item


def update(sid: str, name: str, params: dict, notes: str = "") -> dict:
    data = _store()
    item = _find(data, sid)
    item.update(name=_name(data, name, sid), notes=(notes or "").strip()[:500],
                params=_params(params, item["params"]), updated_at=clock.now())
    _save(data)
    if data["active"] == sid:
        settings.update(item["params"])
    return item


def delete(sid: str) -> None:
    data = _store()
    _find(data, sid)
    if data["active"] == sid:
        raise ValueError("activate another strategy before deleting the active one")
    data["items"] = [i for i in data["items"] if i["id"] != sid]
    _save(data)


def activate(sid: str) -> dict:
    data = _store()
    item = _find(data, sid)
    settings.update(item["params"])
    data["active"] = sid
    _save(data)
    return list_all()


def ensure_default() -> Optional[dict]:
    """Create and activate the built-in strategy once. None if already done."""
    if _load() is not None:
        return None
    _save({"active": None, "items": []})
    item = create(DEFAULT_NAME, DEFAULT_EXITS, DEFAULT_NOTES)
    activate(item["id"])
    return item
