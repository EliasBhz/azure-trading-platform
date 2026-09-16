from typing import Protocol

from trading_bot.domain.market import MarketSnapshot
from trading_bot.domain.orders import OrderExecution, OrderIntent


class ExchangeGateway(Protocol):
    """Every interaction with a trading venue.

    This is the only module allowed to perform exchange I/O, which makes it the
    single place where the paper-trading invariant is enforced and audited. See
    ADR-0004.

    The gateway does not report balances. The bot's own database is the
    authoritative ledger: every balance it reasons about is derived from fills
    it recorded, so a venue outage cannot silently change a risk calculation,
    and the simulated and testnet backends behave identically.
    """

    @property
    def name(self) -> str: ...

    def fetch_snapshot(self, symbol: str, timeframe: str, limit: int) -> MarketSnapshot: ...

    def submit(self, intent: OrderIntent) -> OrderExecution: ...
