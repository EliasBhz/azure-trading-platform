from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from trading_bot.domain.orders import Fill, OrderSide


class Position(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    quantity: Decimal = Field(ge=0)
    average_price: Decimal = Field(ge=0)

    def notional_at(self, price: Decimal) -> Decimal:
        return self.quantity * price

    def apply(self, fill: Fill) -> "Position":
        """Return the position after `fill`, using weighted average cost.

        Selling does not change the average price: realised profit and loss is
        derived from the cash side instead, which keeps this function total and
        free of division by zero when a position is closed exactly.
        """
        if fill.symbol != self.symbol:
            raise ValueError("fill symbol does not match position symbol")

        if fill.side is OrderSide.BUY:
            new_quantity = self.quantity + fill.quantity
            cost = self.quantity * self.average_price + fill.notional
            return Position(
                symbol=self.symbol,
                quantity=new_quantity,
                average_price=cost / new_quantity,
            )

        if fill.quantity > self.quantity:
            raise ValueError("sell fill exceeds the held quantity: short selling is not supported")

        new_quantity = self.quantity - fill.quantity
        return Position(
            symbol=self.symbol,
            quantity=new_quantity,
            average_price=self.average_price if new_quantity > 0 else Decimal(0),
        )


class AccountState(BaseModel):
    """The bot's own ledger, not the venue's.

    Our database is authoritative: the exchange is an execution venue, and every
    balance the bot reasons about is derived from fills we recorded. That keeps
    the simulator and the testnet backends behaviourally identical, and it means
    a venue outage cannot silently change the risk calculation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    cash_quote: Decimal
    position: Position
    day_opening_equity: Decimal = Field(gt=0)

    def equity_at(self, price: Decimal) -> Decimal:
        return self.cash_quote + self.position.notional_at(price)

    def daily_pnl_at(self, price: Decimal) -> Decimal:
        return self.equity_at(price) - self.day_opening_equity


class EquitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    taken_at: AwareDatetime
    symbol: str
    mark_price: Decimal = Field(gt=0)
    cash_quote: Decimal
    position_quantity: Decimal = Field(ge=0)
    equity_quote: Decimal
    day_opening_equity: Decimal = Field(gt=0)

    @property
    def drawdown_ratio(self) -> Decimal:
        """Intraday drawdown against the day's opening equity, as a positive
        fraction. Zero when the day is flat or profitable."""
        loss = self.day_opening_equity - self.equity_quote
        if loss <= 0:
            return Decimal(0)
        return loss / self.day_opening_equity
