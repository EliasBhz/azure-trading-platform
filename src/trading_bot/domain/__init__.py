"""Data contracts exchanged between pipeline stages.

Nothing but these models crosses a module boundary. Dictionaries do not.
"""

from trading_bot.domain.decisions import (
    DecisionOutcome,
    PolicyDecision,
    RiskCheck,
    RiskCheckName,
)
from trading_bot.domain.market import Candle, MarketSnapshot
from trading_bot.domain.orders import (
    Fill,
    OrderExecution,
    OrderIntent,
    OrderSide,
    OrderStatus,
)
from trading_bot.domain.portfolio import AccountState, EquitySnapshot, Position
from trading_bot.domain.signals import Signal, SignalAction

__all__ = [
    "AccountState",
    "Candle",
    "DecisionOutcome",
    "EquitySnapshot",
    "Fill",
    "MarketSnapshot",
    "OrderExecution",
    "OrderIntent",
    "OrderSide",
    "OrderStatus",
    "PolicyDecision",
    "Position",
    "RiskCheck",
    "RiskCheckName",
    "Signal",
    "SignalAction",
]
