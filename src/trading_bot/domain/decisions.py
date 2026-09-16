from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trading_bot.domain.orders import OrderIntent


class RiskCheckName(StrEnum):
    KILL_SWITCH = "kill_switch"
    DAILY_LOSS = "daily_loss"
    ACTIONABLE_SIGNAL = "actionable_signal"
    POSITION_LIMIT = "position_limit"
    AVAILABLE_CASH = "available_cash"
    AVAILABLE_INVENTORY = "available_inventory"
    MIN_NOTIONAL = "min_notional"


class RiskCheck(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: RiskCheckName
    passed: bool
    detail: str


class DecisionOutcome(StrEnum):
    SUBMIT = "submit"
    HOLD = "hold"


class PolicyDecision(BaseModel):
    """The policy engine's verdict for one cycle.

    Every decision carries the full list of checks that were evaluated, passing
    ones included. A refusal without a recorded reason is not auditable, and
    "why did the bot do nothing at 14:00" is the question this project has to be
    able to answer.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    outcome: DecisionOutcome
    reason: str
    checks: tuple[RiskCheck, ...] = Field(min_length=1)
    intent: OrderIntent | None = None

    @property
    def failed_checks(self) -> tuple[RiskCheck, ...]:
        return tuple(check for check in self.checks if not check.passed)

    @model_validator(mode="after")
    def check_intent_matches_outcome(self) -> Self:
        if self.outcome is DecisionOutcome.SUBMIT and self.intent is None:
            raise ValueError("a submit decision must carry an order intent")
        if self.outcome is DecisionOutcome.HOLD and self.intent is not None:
            raise ValueError("a hold decision must not carry an order intent")
        return self
