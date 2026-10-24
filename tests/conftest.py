"""Suite-wide safety and fixtures.

Two sentinels run before any test module imports the app:

1. **A throwaway data directory.** `CRYPTO_TRADER_DATA_DIR` is set before
   `backend.src.config` is imported, so no test can read or write a real
   install's config, database, keyring-adjacent files or admin token.
2. **No exchange.** The Hyperliquid SDK's `Exchange` (signs orders) and `Info`
   (reads the network) constructors are replaced with ones that raise. A test
   that reached the real exchange would fail loudly instead of trading or
   depending on the network. Tests use tests/fakes.py.

Golden rule 1: the automated suite touches no exchange at all -- not mainnet,
not testnet. Testnet is for a human-watched session.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="crypto_trader_tests_")
os.environ["CRYPTO_TRADER_DATA_DIR"] = _TMP
os.environ.pop("CRYPTO_TRADER_NETWORK", None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


class ExchangeSentinel(RuntimeError):
    pass


def _forbidden(*_a, **_k):
    raise ExchangeSentinel("a test tried to construct a real Hyperliquid client")


import hyperliquid.exchange  # noqa: E402
import hyperliquid.info  # noqa: E402

hyperliquid.exchange.Exchange.__init__ = _forbidden
hyperliquid.info.Info.__init__ = _forbidden


@pytest.fixture
def fresh_db(tmp_path):
    from backend.src.db import database
    db = database.init(tmp_path / "main.db")
    yield db
    database.close()


@pytest.fixture
def fixed_clock():
    from backend.src.utils import clock
    clock.set_fixed(1_792_850_000.0)   # 2026-10-24 (a Saturday) 13:53:20 UTC
    yield clock
    clock.set_fixed(None)


@pytest.fixture
def fake_exchange(fresh_db):
    from backend.src.services.exchange import provider
    from tests.fakes import FakeExchange
    fx = FakeExchange()
    provider.set_for_tests(fx)
    yield fx
    provider.set_for_tests(None)


@pytest.fixture(autouse=True)
def _clear_candle_cache():
    from backend.src.services.market import candles
    candles.clear_cache()
    yield
    candles.clear_cache()
