"""Parsers against the response shapes in the SDK's own docstrings (0.24.0)."""
from backend.src.services.exchange import hyperliquid_client as hl


def test_parse_account_reads_signed_size_and_leverage():
    state = {
        "marginSummary": {"accountValue": "1234.5", "totalMarginUsed": "100"},
        "withdrawable": "1000.25",
        "assetPositions": [
            {"position": {"coin": "ETH", "szi": "-0.5", "entryPx": "3000", "unrealizedPnl": "12.5",
                          "leverage": {"type": "isolated", "value": 3}, "liquidationPx": "3900",
                          "marginUsed": "500"}, "type": "oneWay"},
            {"position": {"coin": "BTC", "szi": "0", "entryPx": None, "unrealizedPnl": "0",
                          "leverage": {"type": "cross", "value": 1}, "liquidationPx": None,
                          "marginUsed": "0"}, "type": "oneWay"},
        ],
    }
    acc = hl.parse_account(state)
    assert acc.equity == 1234.5 and acc.available == 1000.25
    assert len(acc.positions) == 1                      # flat BTC dropped
    eth = acc.position("ETH")
    assert eth.size == -0.5 and eth.direction == "short" and eth.leverage == 3
    assert eth.liquidation_price == 3900.0


def test_parse_order_response_variants():
    filled = {"status": "ok", "response": {"type": "order", "data": {"statuses": [
        {"filled": {"totalSz": "0.02", "avgPx": "1891.4", "oid": 77747314}}]}}}
    resting = {"status": "ok", "response": {"type": "order", "data": {"statuses": [
        {"resting": {"oid": 77738308}}]}}}
    error = {"status": "ok", "response": {"type": "order", "data": {"statuses": [
        {"error": "Order must have minimum value of $10."}]}}}
    r1, r2, r3 = (hl.parse_order_response(x) for x in (filled, resting, error))
    assert r1.ok and r1.filled_size == 0.02 and r1.avg_price == 1891.4 and r1.oid == 77747314
    assert r2.ok and r2.oid == 77738308 and r2.filled_size == 0
    assert not r3.ok and "minimum value" in r3.error
    assert not hl.parse_order_response({"status": "err", "response": "bad"}).ok
    assert not hl.parse_order_response(None).ok


def test_parse_snapshots_skips_delisted():
    meta = {"universe": [{"name": "BTC", "szDecimals": 5, "maxLeverage": 40},
                         {"name": "OLD", "szDecimals": 0, "maxLeverage": 3, "isDelisted": True}]}
    ctx = [{"funding": "0.0000125", "openInterest": "100", "prevDayPx": "100", "dayNtlVlm": "5",
            "markPx": "110", "midPx": "110.5", "oraclePx": "109"},
           {"funding": "0", "openInterest": "0", "prevDayPx": "1", "dayNtlVlm": "0",
            "markPx": "1", "midPx": None, "oraclePx": "1"}]
    snaps = hl.parse_snapshots([meta, ctx])
    assert [s.coin for s in snaps] == ["BTC"]
    assert abs(snaps[0].change_24h_pct - 10.0) < 1e-9


def test_open_orders_classify_stop_and_take_profit():
    rows = [{"coin": "SOL", "oid": 1, "side": "A", "sz": "2", "limitPx": "90", "isTrigger": True,
             "orderType": "Stop Market", "triggerPx": "95", "reduceOnly": True},
            {"coin": "SOL", "oid": 2, "side": "A", "sz": "1", "limitPx": "200", "isTrigger": True,
             "orderType": "Take Profit Market", "triggerPx": "180", "reduceOnly": True}]
    a, b = hl.parse_open_orders(rows)
    assert a.kind == "stop" and a.trigger_price == 95.0 and not a.is_buy
    assert b.kind == "take_profit"


def test_network_urls():
    assert hl.base_url("mainnet") == "https://api.hyperliquid.xyz"
    assert hl.base_url("testnet") == "https://api.hyperliquid-testnet.xyz"
