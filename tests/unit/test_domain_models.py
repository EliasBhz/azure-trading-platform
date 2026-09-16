from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from trading_bot.domain.market import Candle, MarketSnapshot
from trading_bot.domain.orders import Fill, OrderSide
from trading_bot.domain.portfolio import EquitySnapshot, Position

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def candle(close: str, *, index: int = 0, symbol: str = "BTC/USDT") -> Candle:
    price = Decimal(close)
    return Candle(
        symbol=symbol,
        open_time=BASE_TIME + timedelta(minutes=15 * index),
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal(1),
    )


def test_candle_rejects_a_close_outside_the_range() -> None:
    with pytest.raises(ValidationError, match="close is outside"):
        Candle(
            symbol="BTC/USDT",
            open_time=BASE_TIME,
            open=Decimal(100),
            high=Decimal(110),
            low=Decimal(90),
            close=Decimal(200),
            volume=Decimal(1),
        )


def test_candle_rejects_a_naive_timestamp() -> None:
    with pytest.raises(ValidationError):
        Candle(
            symbol="BTC/USDT",
            open_time=datetime(2026, 1, 1),  # noqa: DTZ001
            open=Decimal(100),
            high=Decimal(100),
            low=Decimal(100),
            close=Decimal(100),
            volume=Decimal(1),
        )


def test_snapshot_rejects_out_of_order_candles() -> None:
    with pytest.raises(ValidationError, match="ascending time order"):
        MarketSnapshot(
            symbol="BTC/USDT",
            timeframe="15m",
            candles=(candle("100", index=1), candle("101", index=0)),
        )


def test_snapshot_rejects_a_foreign_symbol() -> None:
    with pytest.raises(ValidationError, match="snapshot symbol"):
        MarketSnapshot(
            symbol="BTC/USDT",
            timeframe="15m",
            candles=(candle("100", index=0), candle("101", index=1, symbol="ETH/USDT")),
        )


def test_snapshot_exposes_the_last_close() -> None:
    snapshot = MarketSnapshot(
        symbol="BTC/USDT",
        timeframe="15m",
        candles=(candle("100", index=0), candle("101", index=1)),
    )

    assert snapshot.last_price == Decimal(101)
    assert snapshot.as_of == BASE_TIME + timedelta(minutes=15)


def fill(side: OrderSide, quantity: str, price: str) -> Fill:
    return Fill(
        client_order_id="c1",
        symbol="BTC/USDT",
        side=side,
        quantity=Decimal(quantity),
        price=Decimal(price),
        fee_quote=Decimal(0),
        filled_at=BASE_TIME,
    )


def test_buying_twice_averages_the_cost() -> None:
    position = Position(symbol="BTC/USDT", quantity=Decimal(0), average_price=Decimal(0))

    position = position.apply(fill(OrderSide.BUY, "1", "100"))
    position = position.apply(fill(OrderSide.BUY, "1", "200"))

    assert position.quantity == Decimal(2)
    assert position.average_price == Decimal(150)


def test_selling_leaves_the_average_price_untouched() -> None:
    position = Position(symbol="BTC/USDT", quantity=Decimal(2), average_price=Decimal(150))

    position = position.apply(fill(OrderSide.SELL, "1", "500"))

    assert position.quantity == Decimal(1)
    assert position.average_price == Decimal(150)


def test_closing_a_position_exactly_resets_the_average_price() -> None:
    position = Position(symbol="BTC/USDT", quantity=Decimal(2), average_price=Decimal(150))

    position = position.apply(fill(OrderSide.SELL, "2", "500"))

    assert position.quantity == Decimal(0)
    assert position.average_price == Decimal(0)


def test_selling_more_than_held_is_refused() -> None:
    position = Position(symbol="BTC/USDT", quantity=Decimal(1), average_price=Decimal(150))

    with pytest.raises(ValueError, match="short selling is not supported"):
        position.apply(fill(OrderSide.SELL, "2", "500"))


def equity(equity_quote: str, opening: str = "10000") -> EquitySnapshot:
    return EquitySnapshot(
        taken_at=BASE_TIME,
        symbol="BTC/USDT",
        mark_price=Decimal(100),
        cash_quote=Decimal(equity_quote),
        position_quantity=Decimal(0),
        equity_quote=Decimal(equity_quote),
        day_opening_equity=Decimal(opening),
    )


def test_drawdown_is_zero_on_a_profitable_day() -> None:
    assert equity("11000").drawdown_ratio == Decimal(0)


def test_drawdown_is_a_positive_fraction_of_the_opening_equity() -> None:
    assert equity("9000").drawdown_ratio == Decimal("0.1")
