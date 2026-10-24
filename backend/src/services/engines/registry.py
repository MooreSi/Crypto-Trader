"""The three engines, built once, each with its own database and model.

| engine    | interval | higher timeframe |
|-----------|----------|------------------|
| breakout  | 15m      | -                |
| reversal  | 15m      | 1d (prior day)   |
| trend_pa  | 1h       | 4h               |

Signals and models are keyed by the MARKET DATA they were computed from, not
by the network orders go to: paper and mainnet both read mainnet prices, so
they share `<engine>_mainnet.db` and `models/mainnet/`, and research carries
over when you move from paper to real money. Testnet prices are their own
market (thin, sometimes far from mainnet), so testnet research is kept apart
and never trains a mainnet model.
"""
from __future__ import annotations

import threading
from typing import Optional

from backend.src import config
from backend.src.services.breakout import generator as breakout
from backend.src.services.engines.service import EngineService
from backend.src.services.engines.signal_repo import SignalStore
from backend.src.services.ml.features import BASE_FEATURES
from backend.src.services.ml.model import EngineModel
from backend.src.services.reversal import generator as reversal
from backend.src.services.trend_pa import generator as trend_pa

_SPECS = (
    ("breakout", "15m", None, breakout),
    ("reversal", "15m", "1d", reversal),
    ("trend_pa", "1h", "4h", trend_pa),
)

_lock = threading.Lock()
_engines: Optional[dict[str, EngineService]] = None


def data_source(network: str) -> str:
    return "testnet" if network == "testnet" else "mainnet"


def build() -> dict[str, EngineService]:
    out = {}
    source = data_source(str(config.get("network")))
    for name, interval, htf, module in _SPECS:
        store = SignalStore(config.db_path(f"{name}_{source}.db"))
        names = BASE_FEATURES + tuple(module.EXTRA_FEATURES)
        model = EngineModel(name, names, config.MODELS_DIR / source)
        model.load()
        out[name] = EngineService(name, interval, module.generate, module.EXTRA_FEATURES, store,
                                  model, htf)
    return out


def get() -> dict[str, EngineService]:
    global _engines
    with _lock:
        if _engines is None:
            _engines = build()
        return _engines


def close() -> None:
    global _engines
    with _lock:
        for eng in (_engines or {}).values():
            eng.store.close()
        _engines = None
