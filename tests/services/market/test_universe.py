"""Which markets the engines scan.

Defect (2026-10-25): Hyperliquid names some perpetuals in mixed case
(`kPEPE`, `kBONK`, `kSHIB`: thousands of the token). The risk settings
store the watchlist upper-cased, so a watched `kPEPE` became `KPEPE`, never
matched, and was silently not scanned.
"""
from backend.src.services.exchange.types import MarketSnapshot
from backend.src.services.market import universe


def _snap(coin, volume=1e9):
    return MarketSnapshot(coin, 1.0, 1.0, 1.0, 0.0, 1000.0, volume, 1.0)


def test_a_watched_mixed_case_coin_is_scanned_under_its_exchange_name():
    snaps = [_snap("BTC"), _snap("kPEPE")]
    assert universe.select(snaps, {"watchlist": ["KPEPE"], "blocklist": []}) == ["kPEPE"]


def test_watchlist_keeps_its_order_and_drops_unknown_coins():
    snaps = [_snap("BTC"), _snap("ETH"), _snap("SOL")]
    assert universe.select(snaps, {"watchlist": ["SOL", "NOPE", "BTC"]}) == ["SOL", "BTC"]


def test_blocklist_wins_over_the_watchlist_whatever_the_case():
    snaps = [_snap("BTC"), _snap("kPEPE")]
    assert universe.select(snaps, {"watchlist": ["KPEPE", "BTC"], "blocklist": ["KPEPE"]}) == ["BTC"]


def test_auto_mode_ranks_by_volume_and_honours_the_minimum():
    snaps = [_snap("A", 5e6), _snap("B", 9e6), _snap("C", 1e5)]
    s = {"auto_top_n": 5, "min_day_volume_usd": 1e6}
    assert universe.select(snaps, s) == ["B", "A"]
