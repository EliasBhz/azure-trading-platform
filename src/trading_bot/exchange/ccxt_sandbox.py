from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from trading_bot.domain.market import Candle, MarketSnapshot
from trading_bot.domain.orders import (
    Fill,
    OrderExecution,
    OrderIntent,
    OrderStatus,
)
from trading_bot.errors import ExchangeError, SandboxGuardError


class CcxtSandboxExchange:
    """A ccxt client locked to an exchange testnet.

    The sandbox assertion is re-checked after `set_sandbox_mode`, rather than
    trusted: an exchange whose ccxt implementation silently ignores sandbox mode
    must fail closed, not trade. This is the second line of defence behind the
    Settings guard, and the reason it is worth having two is that they fail for
    different reasons.
    """

    def __init__(
        self,
        *,
        exchange_id: str,
        api_key: str,
        api_secret: str,
        sandbox: bool = True,
    ) -> None:
        if not sandbox:
            raise SandboxGuardError(
                "CcxtSandboxExchange cannot be constructed outside sandbox mode"
            )

        # Imported here so that the simulated backend, and therefore CI, does
        # not need ccxt installed.
        import ccxt

        try:
            exchange_class = getattr(ccxt, exchange_id)
        except AttributeError as error:
            raise ExchangeError(f"unknown ccxt exchange: {exchange_id!r}") from error

        client: Any = exchange_class(
            {
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
            }
        )
        client.set_sandbox_mode(True)

        if not self._urls_look_like_a_testnet(client):
            raise SandboxGuardError(
                f"{exchange_id} did not switch to testnet endpoints after set_sandbox_mode"
            )

        self._exchange_id = exchange_id
        self._client = client

    @property
    def name(self) -> str:
        return f"ccxt_sandbox_{self._exchange_id}"

    def fetch_snapshot(self, symbol: str, timeframe: str, limit: int) -> MarketSnapshot:
        try:
            rows: list[list[Any]] = self._client.fetch_ohlcv(symbol, timeframe, limit=limit)
        except Exception as error:  # ccxt error hierarchy varies by version
            raise ExchangeError(f"fetch_ohlcv failed for {symbol} {timeframe}") from error

        if not rows:
            raise ExchangeError(f"the venue returned no candles for {symbol} {timeframe}")

        candles = tuple(self._to_candle(symbol, row) for row in rows)
        return MarketSnapshot(symbol=symbol, timeframe=timeframe, candles=candles)

    def submit(self, intent: OrderIntent) -> OrderExecution:
        try:
            response: dict[str, Any] = self._client.create_order(
                symbol=intent.symbol,
                type="market",
                side=intent.side.value,
                amount=float(intent.quantity),
                params={"clientOrderId": intent.client_order_id},
            )
        except Exception as error:  # ccxt error hierarchy varies by version
            return OrderExecution(
                intent=intent,
                status=OrderStatus.REJECTED,
                rejection_reason=f"{type(error).__name__}: {error}",
            )

        return self._to_execution(intent, response)

    @staticmethod
    def _urls_look_like_a_testnet(client: Any) -> bool:
        urls = client.urls.get("api")
        candidates = urls.values() if isinstance(urls, dict) else [urls]
        flattened = " ".join(str(candidate) for candidate in candidates).lower()
        return any(marker in flattened for marker in ("testnet", "sandbox", "test.", "demo"))

    @staticmethod
    def _to_candle(symbol: str, row: list[Any]) -> Candle:
        """Convert one ccxt OHLCV row.

        ccxt returns floats. They are stringified before reaching Decimal so
        that the binary representation is not carried into the ledger: the
        precision was already lost upstream, but it stops here.
        """
        timestamp_ms, open_, high, low, close, volume = row[:6]
        return Candle(
            symbol=symbol,
            open_time=datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC),
            open=Decimal(str(open_)),
            high=Decimal(str(high)),
            low=Decimal(str(low)),
            close=Decimal(str(close)),
            volume=Decimal(str(volume)),
        )

    @staticmethod
    def _to_execution(intent: OrderIntent, response: dict[str, Any]) -> OrderExecution:
        filled = Decimal(str(response.get("filled") or 0))
        average = response.get("average") or response.get("price")

        if filled <= 0 or average is None:
            return OrderExecution(
                intent=intent,
                status=OrderStatus.REJECTED,
                venue_order_id=str(response.get("id")) if response.get("id") else None,
                rejection_reason=f"venue reported no fill: status={response.get('status')!r}",
            )

        fee_cost = Decimal(str((response.get("fee") or {}).get("cost") or 0))
        fill = Fill(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=filled,
            price=Decimal(str(average)),
            fee_quote=fee_cost,
            filled_at=datetime.now(tz=UTC),
        )
        status = OrderStatus.FILLED if filled >= intent.quantity else OrderStatus.PARTIALLY_FILLED
        return OrderExecution(
            intent=intent,
            status=status,
            venue_order_id=str(response.get("id")) if response.get("id") else None,
            fills=(fill,),
        )
