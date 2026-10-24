from backend.src.services.exchange import rounding as r


def test_size_rounds_down_never_up():
    assert r.round_size(0.123456789, 5) == 0.12345
    assert r.round_size(1.999, 2) == 1.99


def test_price_respects_five_significant_figures():
    # BTC: szDecimals 5 -> max 1 decimal, but 5 sig figs at 80,000 means integers
    assert r.round_price(80123.456, 5) == 80123.0
    # ETH at 3000: 5 sig figs -> 1 decimal; szDecimals 4 -> max 2 decimals
    assert r.round_price(3000.456, 4) == 3000.5
    # a cheap coin: 0.012345678, szDecimals 0 -> max 6 decimals, 5 sig figs
    assert r.round_price(0.012345678, 0) == 0.012346


def test_integer_prices_above_five_figures_are_always_valid():
    assert r.round_price(123456.7, 5) == 123457.0
    assert r.is_valid_price(123457.0, 5)


def test_stop_rounds_away_from_entry():
    # long: stop below entry rounds DOWN
    assert r.round_stop(2999.96, 3100.0, 4) == 2999.9
    # short: stop above entry rounds UP
    assert r.round_stop(3000.04, 2900.0, 4) == 3000.1
