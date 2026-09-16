from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RiskLimits(BaseModel):
    """The hard bounds the policy engine enforces.

    Kept as a value object rather than read from Settings inside the engine so
    that the engine stays pure and every limit combination is trivially
    testable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_position_quote: Decimal = Field(gt=0)
    max_daily_loss_quote: Decimal = Field(gt=0)
    min_order_notional_quote: Decimal = Field(gt=0)
