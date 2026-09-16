from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(StrEnum):
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"


class OrderIntent(BaseModel):
    """An order the policy engine has approved but that nobody has sent yet.

    `client_order_id` is derived deterministically from the cycle, so replaying
    a cycle cannot create a duplicate order on the venue.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    client_order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal = Field(gt=0)
    reference_price: Decimal = Field(gt=0)
    created_at: AwareDatetime

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.reference_price


class Fill(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    client_order_id: str
    symbol: str
    side: OrderSide
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fee_quote: Decimal = Field(ge=0)
    filled_at: AwareDatetime

    @property
    def notional(self) -> Decimal:
        return self.quantity * self.price


class OrderExecution(BaseModel):
    """The venue's answer to one intent: a status, zero or more fills, and, when
    rejected, the reason the venue gave."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent: OrderIntent
    status: OrderStatus
    venue_order_id: str | None = None
    fills: tuple[Fill, ...] = ()
    rejection_reason: str | None = None

    @property
    def filled_quantity(self) -> Decimal:
        return sum((fill.quantity for fill in self.fills), Decimal(0))

    @property
    def fees_quote(self) -> Decimal:
        return sum((fill.fee_quote for fill in self.fills), Decimal(0))
