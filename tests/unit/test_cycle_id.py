from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_bot.cycle import build_cycle_id
from trading_bot.domain.market import Candle, MarketSnapshot

BASE_TIME = datetime(2026, 1, 1, 12, tzinfo=UTC)


def snapshot(*, offset_minutes: int = 0, symbol: str = "BTC/USDT") -> MarketSnapshot:
    open_time = BASE_TIME + timedelta(minutes=offset_minutes)
    candle = Candle(
        symbol=symbol,
        open_time=open_time,
        open=Decimal(100),
        high=Decimal(100),
        low=Decimal(100),
        close=Decimal(100),
        volume=Decimal(1),
    )
    return MarketSnapshot(symbol=symbol, timeframe="15m", candles=(candle,))


def test_the_same_bar_yields_the_same_id() -> None:
    """Two invocations for one bar must produce one order, not two.

    Container Apps Jobs retry a failed execution. If the id moved with the wall
    clock, a crash between submitting an order and committing the transaction
    would double the position on the retry.
    """
    assert build_cycle_id(snapshot()) == build_cycle_id(snapshot())


def test_a_later_bar_yields_a_different_id() -> None:
    assert build_cycle_id(snapshot()) != build_cycle_id(snapshot(offset_minutes=15))


def test_the_symbol_separator_is_stripped() -> None:
    assert build_cycle_id(snapshot()) == "BTCUSDT-15m-1767268800"
