import random
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from trading_bot.domain.market import Candle, MarketSnapshot
from trading_bot.domain.orders import (
    Fill,
    OrderExecution,
    OrderIntent,
    OrderSide,
    OrderStatus,
)
from trading_bot.exchange.timeframes import floor_to_timeframe, parse_timeframe

BPS = Decimal(10_000)
PRICE_STEP = Decimal("0.01")


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class SimulatedExchange:
    """A deterministic in-process venue.

    Given the same seed and the same bar timestamps it produces the same
    candles, so a failing test is reproducible and CI needs neither credentials
    nor network access. See ADR-0004.

    It is an honest simplification, not a market model: orders fill completely,
    immediately, at the reference price adjusted by a fixed slippage, with a
    fixed proportional fee. It does not model an order book, partial fills,
    latency or rejections. Conclusions about strategy performance drawn from it
    are worthless, which is acceptable because performance is not the goal.
    """

    def __init__(
        self,
        *,
        seed: int,
        start_price: Decimal,
        volatility_bps: Decimal,
        fee_bps: Decimal,
        slippage_bps: Decimal,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._seed = seed
        self._start_price = start_price
        self._volatility_bps = volatility_bps
        self._fee_bps = fee_bps
        self._slippage_bps = slippage_bps
        self._clock = clock

    @property
    def name(self) -> str:
        return "simulated"

    def fetch_snapshot(self, symbol: str, timeframe: str, limit: int) -> MarketSnapshot:
        step = parse_timeframe(timeframe)
        last_open = floor_to_timeframe(self._clock(), timeframe) - step
        first_open = last_open - step * (limit - 1)

        rng = random.Random(f"{self._seed}:{symbol}:{timeframe}")
        price = self._start_price
        candles: list[Candle] = []

        for index in range(limit):
            open_price = price
            close_price = self._next_price(open_price, rng)
            high = max(open_price, close_price) * (Decimal(1) + self._drift(rng))
            low = min(open_price, close_price) * (Decimal(1) - self._drift(rng))
            candles.append(
                Candle(
                    symbol=symbol,
                    open_time=first_open + step * index,
                    open=_round(open_price),
                    high=_round(max(high, open_price, close_price)),
                    low=_round(min(low, open_price, close_price)),
                    close=_round(close_price),
                    volume=Decimal(rng.randrange(1, 1000)),
                )
            )
            price = close_price

        return MarketSnapshot(symbol=symbol, timeframe=timeframe, candles=tuple(candles))

    def submit(self, intent: OrderIntent) -> OrderExecution:
        fill_price = _round(
            intent.reference_price * (Decimal(1) + self._signed_slippage(intent.side))
        )
        fee = _round(intent.quantity * fill_price * self._fee_bps / BPS)
        fill = Fill(
            client_order_id=intent.client_order_id,
            symbol=intent.symbol,
            side=intent.side,
            quantity=intent.quantity,
            price=fill_price,
            fee_quote=fee,
            filled_at=self._clock(),
        )
        return OrderExecution(
            intent=intent,
            status=OrderStatus.FILLED,
            venue_order_id=f"sim-{intent.client_order_id}",
            fills=(fill,),
        )

    def _next_price(self, price: Decimal, rng: random.Random) -> Decimal:
        shock = Decimal(str(rng.gauss(0.0, 1.0))) * self._volatility_bps / BPS
        return max(PRICE_STEP, price * (Decimal(1) + shock))

    def _drift(self, rng: random.Random) -> Decimal:
        return Decimal(str(abs(rng.gauss(0.0, 0.5)))) * self._volatility_bps / BPS

    def _signed_slippage(self, side: OrderSide) -> Decimal:
        """Slippage always works against the bot.

        A simulator that fills at a better price than requested flatters the
        strategy and hides execution cost, which is the one thing a paper
        trading platform should not do.
        """
        magnitude = self._slippage_bps / BPS
        return magnitude if side is OrderSide.BUY else -magnitude


def _round(value: Decimal) -> Decimal:
    return value.quantize(PRICE_STEP, rounding=ROUND_HALF_UP)
