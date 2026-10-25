"""Risk settings: every number that decides how much the app may lose.

Defaults are the owner's "conservative" choice for v0.1 (2026-10-24):
isolated margin, at most 3x leverage, 0.5% of equity at risk per trade, at
most 3 open positions, no daily profit cap until one is set.

**Golden rule 3 applies from this release on: a default here never changes
silently.** An upgrade that changed one would change how every existing
install trades. A new setting gets a default that reproduces the behaviour
before it existed. See docs/system/rules/60-adding-a-tunable.md.

Every value is clamped to its `[min, max]` envelope on write, so neither the
dashboard nor a hand-edited database can push the app outside it.
"""
from __future__ import annotations

import json
from typing import Any

from backend.src.services.risk import settings_repo

#: name -> (default, min, max). None bounds mean "not numeric".
NUMERIC: dict[str, tuple[float, float, float]] = {
    "risk_per_trade_pct":        (0.5, 0.05, 100.0),     # cap raised by the owner 2026-10-24
    "max_leverage":              (3, 1, 50),
    "max_open_positions":        (3, 1, 20),
    "max_same_direction":        (2, 1, 20),
    "daily_loss_limit_pct":      (3.0, 0.5, 50.0),
    "daily_profit_target_usd":   (0.0, 0.0, 1_000_000.0),   # 0 = off
    "max_position_notional_pct": (300.0, 5.0, 5000.0),      # notional, % of equity
    "min_reward_risk":           (1.5, 0.5, 10.0),
    "entry_slippage_pct":        (0.5, 0.05, 5.0),
    "auto_top_n":                (20, 1, 100),
    "min_day_volume_usd":        (5_000_000.0, 0.0, 1e12),
    "blackout_minutes_before":   (30, 0, 720),
    "blackout_minutes_after":    (30, 0, 720),
    "max_funding_rate_pct":      (0.05, 0.0, 5.0),          # hourly, against you
    "breakeven_after_tp":        (1, 0, 8),                 # 0 = never
    "trail_atr_mult":            (0.0, 0.0, 10.0),          # 0 = no trailing
    "ml_min_probability":        (0.5, 0.0, 1.0),
    # Refuse a signal whose stop is closer than this % of price (0 = off).
    # A round trip pays ~0.09% in taker fees whatever the stop, so a 0.2% stop
    # starts 0.45R down. Added 2026-10-25, default off.
    "min_stop_pct":              (0.0, 0.0, 5.0),
}

BOOLEAN: dict[str, bool] = {
    "trading_enabled": False,          # master switch: nothing executes until on
    "isolated_margin": True,
    "blackout_enabled": True,
    "blackout_include_medium": False,
    "ml_require_model": False,
}

LISTS: dict[str, list[str]] = {
    "watchlist": [],    # empty = auto: top `auto_top_n` by 24h volume
    "blocklist": [],
}

#: TP ladder: (R multiple, fraction of the ORIGINAL size to close there).
DEFAULT_TP_LADDER: list[list[float]] = [[1.0, 0.5], [2.0, 0.25], [3.0, 0.25]]

_INT_KEYS = {"max_leverage", "max_open_positions", "max_same_direction", "auto_top_n",
             "blackout_minutes_before", "blackout_minutes_after", "breakeven_after_tp"}


def defaults() -> dict[str, Any]:
    out: dict[str, Any] = {k: v[0] for k, v in NUMERIC.items()}
    out.update(BOOLEAN)
    out.update({k: list(v) for k, v in LISTS.items()})
    out["tp_ladder"] = [list(x) for x in DEFAULT_TP_LADDER]
    return out


def _clamp(key: str, value: Any) -> Any:
    _, lo, hi = NUMERIC[key]
    v = min(max(float(value), lo), hi)
    return int(round(v)) if key in _INT_KEYS else v


def _valid_ladder(ladder: Any) -> list[list[float]]:
    rows = []
    for row in ladder or []:
        r, frac = float(row[0]), float(row[1])
        if r <= 0 or not 0 < frac <= 1:
            raise ValueError("each TP needs R > 0 and a fraction in (0, 1]")
        rows.append([r, frac])
    rows.sort(key=lambda x: x[0])
    total = sum(f for _, f in rows)
    if not rows or total > 1.0 + 1e-9:
        raise ValueError("TP fractions must add up to at most 1")
    return rows


def normalise(fields: dict) -> dict:
    """Validate + clamp a partial update. Unknown keys are refused."""
    out: dict[str, Any] = {}
    for key, value in fields.items():
        if key in NUMERIC:
            out[key] = _clamp(key, value)
        elif key in BOOLEAN:
            out[key] = bool(value)
        elif key in LISTS:
            out[key] = sorted({str(c).strip().upper() for c in value if str(c).strip()}) \
                if key == "blocklist" else [str(c).strip().upper() for c in value if str(c).strip()]
        elif key == "tp_ladder":
            out[key] = _valid_ladder(value)
        else:
            raise ValueError(f"unknown risk setting {key!r}")
    return out


def get() -> dict[str, Any]:
    merged = defaults()
    raw = settings_repo.load()
    if raw:
        try:
            stored = json.loads(raw)
            merged.update(normalise({k: v for k, v in stored.items() if k in merged}))
        except (ValueError, TypeError, KeyError, IndexError):
            pass
    return merged


def update(fields: dict) -> dict[str, Any]:
    current = get()
    current.update(normalise(fields))
    settings_repo.save(json.dumps(current))
    return current
