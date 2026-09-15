from datetime import UTC, datetime
from decimal import Decimal

from trading_bot.domain.orders import (
    Fill,
    OrderExecution,
    OrderIntent,
    OrderSide,
    OrderStatus,
)
from trading_bot.domain.portfolio import Position
from trading_bot.execution.ledger import apply_execution

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def execution(side: OrderSide, quantity: str, price: str, fee: str) -> OrderExecution:
    intent = OrderIntent(
        client_order_id="CYCLE1",
        symbol="BTC/USDT",
        side=side,
        quantity=Decimal(quantity),
        reference_price=Decimal(price),
        created_at=NOW,
    )
    return OrderExecution(
        intent=intent,
        status=OrderStatus.FILLED,
        fills=(
            Fill(
                client_order_id="CYCLE1",
                symbol="BTC/USDT",
                side=side,
                quantity=Decimal(quantity),
                price=Decimal(price),
                fee_quote=Decimal(fee),
                filled_at=NOW,
            ),
        ),
    )


def flat() -> Position:
    return Position(symbol="BTC/USDT", quantity=Decimal(0), average_price=Decimal(0))


def test_a_buy_removes_the_notional_and_the_fee_from_cash() -> None:
    update = apply_execution(
        cash_quote=Decimal(1000),
        position=flat(),
        execution=execution(OrderSide.BUY, "2", "100", "1"),
    )

    assert update.cash_quote == Decimal(799)
    assert update.position.quantity == Decimal(2)
    assert update.fees_quote == Decimal(1)


def test_a_sell_adds_the_notional_and_still_removes_the_fee() -> None:
    held = Position(symbol="BTC/USDT", quantity=Decimal(2), average_price=Decimal(100))

    update = apply_execution(
        cash_quote=Decimal(0),
        position=held,
        execution=execution(OrderSide.SELL, "2", "150", "1"),
    )

    assert update.cash_quote == Decimal(299)
    assert update.position.quantity == Decimal(0)


def test_an_execution_without_fills_changes_nothing() -> None:
    rejected = OrderExecution(
        intent=execution(OrderSide.BUY, "1", "100", "0").intent,
        status=OrderStatus.REJECTED,
        rejection_reason="venue said no",
    )

    update = apply_execution(cash_quote=Decimal(1000), position=flat(), execution=rejected)

    assert update.cash_quote == Decimal(1000)
    assert update.position == flat()
    assert update.fees_quote == Decimal(0)


def test_a_round_trip_at_the_same_price_loses_exactly_the_fees() -> None:
    bought = apply_execution(
        cash_quote=Decimal(1000),
        position=flat(),
        execution=execution(OrderSide.BUY, "1", "100", "1"),
    )
    sold = apply_execution(
        cash_quote=bought.cash_quote,
        position=bought.position,
        execution=execution(OrderSide.SELL, "1", "100", "1"),
    )

    assert sold.cash_quote == Decimal(998)
