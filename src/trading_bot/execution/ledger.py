from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from trading_bot.domain.orders import OrderExecution, OrderSide
from trading_bot.domain.portfolio import Position


class LedgerUpdate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cash_quote: Decimal
    position: Position
    fees_quote: Decimal


def apply_execution(
    *,
    cash_quote: Decimal,
    position: Position,
    execution: OrderExecution,
) -> LedgerUpdate:
    """Fold an execution into the ledger.

    Pure, so the arithmetic that decides how much money the bot thinks it has
    can be tested without a database. Fees are always subtracted from cash,
    never netted into the position's average price: keeping them visible is what
    makes the difference between gross and net performance measurable.
    """
    new_cash = cash_quote
    new_position = position
    fees = Decimal(0)

    for fill in execution.fills:
        fees += fill.fee_quote
        if fill.side is OrderSide.BUY:
            new_cash -= fill.notional + fill.fee_quote
        else:
            new_cash += fill.notional - fill.fee_quote
        new_position = new_position.apply(fill)

    return LedgerUpdate(cash_quote=new_cash, position=new_position, fees_quote=fees)
