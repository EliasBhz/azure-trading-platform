from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_bot.domain.orders import OrderIntent, OrderSide, OrderStatus
from trading_bot.exchange.simulated import SimulatedExchange

NOW = datetime(2026, 1, 1, 12, 7, 31, tzinfo=UTC)


def build(**overrides: object) -> SimulatedExchange:
    kwargs: dict[str, object] = {
        "seed": 1,
        "start_price": Decimal(30000),
        "volatility_bps": Decimal(40),
        "fee_bps": Decimal(10),
        "slippage_bps": Decimal(5),
        "clock": lambda: NOW,
    }
    kwargs.update(overrides)
    return SimulatedExchange(**kwargs)  # type: ignore[arg-type]


def intent(side: OrderSide) -> OrderIntent:
    return OrderIntent(
        client_order_id="CYCLE1-" + side.value,
        symbol="BTC/USDT",
        side=side,
        quantity=Decimal(1),
        reference_price=Decimal(1000),
        created_at=NOW,
    )


def test_the_same_seed_produces_the_same_candles() -> None:
    first = build().fetch_snapshot("BTC/USDT", "15m", 50)
    second = build().fetch_snapshot("BTC/USDT", "15m", 50)

    assert first == second


def test_a_different_seed_produces_different_candles() -> None:
    first = build().fetch_snapshot("BTC/USDT", "15m", 50)
    second = build(seed=2).fetch_snapshot("BTC/USDT", "15m", 50)

    assert first != second


def test_candles_are_aligned_on_the_timeframe_and_exclude_the_open_bar() -> None:
    snapshot = build().fetch_snapshot("BTC/USDT", "15m", 4)

    assert len(snapshot.candles) == 4
    assert snapshot.as_of == datetime(2026, 1, 1, 11, 45, tzinfo=UTC)
    assert snapshot.candles[0].open_time == snapshot.as_of - timedelta(minutes=45)


def test_a_buy_fills_above_the_reference_price() -> None:
    execution = build().submit(intent(OrderSide.BUY))

    assert execution.status is OrderStatus.FILLED
    assert execution.fills[0].price == Decimal("1000.50")


def test_a_sell_fills_below_the_reference_price() -> None:
    """Slippage always works against the bot, in both directions."""
    execution = build().submit(intent(OrderSide.SELL))

    assert execution.fills[0].price == Decimal("999.50")


def test_the_fee_is_proportional_to_the_filled_notional() -> None:
    execution = build().submit(intent(OrderSide.BUY))

    fill = execution.fills[0]
    assert fill.fee_quote == (fill.quantity * fill.price * Decimal(10) / Decimal(10_000)).quantize(
        Decimal("0.01")
    )
