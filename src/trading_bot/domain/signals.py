from decimal import Decimal
from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class SignalAction(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class Signal(BaseModel):
    """What the strategy concluded from a market snapshot.

    A signal is an opinion, never an instruction: it carries no quantity and no
    price. Turning it into something executable is the policy engine's job, and
    keeping the two apart is what makes the risk limits impossible to bypass.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    action: SignalAction
    strength: Decimal = Field(ge=0, le=1)
    as_of: AwareDatetime
    strategy: str
    reason: str
    context: dict[str, str] = Field(default_factory=dict)
