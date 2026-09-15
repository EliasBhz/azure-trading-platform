from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from trading_bot.domain.market import Candle, MarketSnapshot
from trading_bot.domain.signals import SignalAction
from trading_bot.errors import ConfigurationError
from trading_bot.strategy.sma_crossover import SmaCrossoverStrategy

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def snapshot(closes: list[str]) -> MarketSnapshot:
    candles = tuple(
        Candle(
            symbol="BTC/USDT",
            open_time=BASE_TIME + timedelta(minutes=15 * index),
            open=Decimal(close),
            high=Decimal(close),
            low=Decimal(close),
            close=Decimal(close),
            volume=Decimal(1),
        )
        for index, close in enumerate(closes)
    )
    return MarketSnapshot(symbol="BTC/USDT", timeframe="15m", candles=candles)


def test_windows_must_be_ordered() -> None:
    with pytest.raises(ConfigurationError):
        SmaCrossoverStrategy(fast_window=5, slow_window=5)


def test_holds_when_history_is_too_short() -> None:
    strategy = SmaCrossoverStrategy(fast_window=2, slow_window=4)

    signal = strategy.evaluate(snapshot(["100", "100", "100"]))

    assert signal.action is SignalAction.HOLD
    assert "not enough history" in signal.reason


def test_buys_when_the_fast_average_crosses_above() -> None:
    strategy = SmaCrossoverStrategy(fast_window=2, slow_window=4)

    signal = strategy.evaluate(snapshot(["100", "100", "100", "100", "100", "140"]))

    assert signal.action is SignalAction.BUY
    assert signal.strength > 0


def test_sells_when_the_fast_average_crosses_below() -> None:
    strategy = SmaCrossoverStrategy(fast_window=2, slow_window=4)

    signal = strategy.evaluate(snapshot(["100", "100", "100", "100", "100", "60"]))

    assert signal.action is SignalAction.SELL


def test_holds_while_a_trend_merely_continues() -> None:
    """A signal fires on the transition, not on the state.

    Acting on the state would re-enter on every cycle for as long as the fast
    average stayed above the slow one, which is how a position limit gets
    reached by accident rather than by decision.
    """
    strategy = SmaCrossoverStrategy(fast_window=2, slow_window=4)
    rising = ["100", "100", "100", "100", "100", "140", "180", "220"]

    signal = strategy.evaluate(snapshot(rising))

    assert signal.action is SignalAction.HOLD
    assert signal.reason == "no crossover on the latest candle"


def test_strength_is_clamped_to_one() -> None:
    strategy = SmaCrossoverStrategy(fast_window=2, slow_window=4)

    signal = strategy.evaluate(snapshot(["100", "100", "100", "100", "100", "10000"]))

    assert signal.strength == Decimal(1)


def test_signal_carries_the_snapshot_time_not_the_wall_clock() -> None:
    strategy = SmaCrossoverStrategy(fast_window=2, slow_window=4)
    market = snapshot(["100", "100", "100", "100", "100", "140"])

    signal = strategy.evaluate(market)

    assert signal.as_of == market.as_of
