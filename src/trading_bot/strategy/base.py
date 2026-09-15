from typing import Protocol

from trading_bot.domain.market import MarketSnapshot
from trading_bot.domain.signals import Signal


class Strategy(Protocol):
    """Turns a market snapshot into an opinion.

    Implementations must be pure: no network, no database, no clock. The only
    time a strategy may reference is the snapshot's own timestamp. That is what
    makes a cycle reproducible from persisted market data.
    """

    @property
    def name(self) -> str: ...

    def evaluate(self, snapshot: MarketSnapshot) -> Signal: ...
