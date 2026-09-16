from collections.abc import Sequence
from decimal import Decimal

from trading_bot.domain.market import MarketSnapshot
from trading_bot.domain.signals import Signal, SignalAction
from trading_bot.errors import ConfigurationError


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values))


class SmaCrossoverStrategy:
    """Moving average crossover.

    Deliberately the simplest strategy that still produces both entries and
    exits. The project demonstrates the platform around the bot, so the strategy
    must be short enough to be verified by reading it. Anything more elaborate
    would need its own backtesting evidence to be defensible, which is out of
    scope.

    A signal is emitted only on the bar where the fast average crosses the slow
    one, not on every bar where they are merely on one side. Acting on the state
    rather than the transition would re-submit an order every cycle for as long
    as the trend lasts.
    """

    def __init__(
        self,
        fast_window: int,
        slow_window: int,
        strength_scale_ratio: Decimal = Decimal("0.01"),
    ) -> None:
        if fast_window < 2:
            raise ConfigurationError("fast_window must be at least 2")
        if fast_window >= slow_window:
            raise ConfigurationError("fast_window must be strictly shorter than slow_window")
        if strength_scale_ratio <= 0:
            raise ConfigurationError("strength_scale_ratio must be positive")

        self._fast_window = fast_window
        self._slow_window = slow_window
        self._strength_scale_ratio = strength_scale_ratio

    @property
    def name(self) -> str:
        return f"sma_crossover_{self._fast_window}_{self._slow_window}"

    def evaluate(self, snapshot: MarketSnapshot) -> Signal:
        closes = [candle.close for candle in snapshot.candles]
        required = self._slow_window + 1

        if len(closes) < required:
            return self._hold(
                snapshot,
                f"not enough history: {len(closes)} candles, {required} required",
            )

        current_fast = _mean(closes[-self._fast_window :])
        current_slow = _mean(closes[-self._slow_window :])
        previous_fast = _mean(closes[-self._fast_window - 1 : -1])
        previous_slow = _mean(closes[-self._slow_window - 1 : -1])

        crossed_up = previous_fast <= previous_slow and current_fast > current_slow
        crossed_down = previous_fast >= previous_slow and current_fast < current_slow

        if not (crossed_up or crossed_down):
            return self._hold(
                snapshot, "no crossover on the latest candle", current_fast, current_slow
            )

        action = SignalAction.BUY if crossed_up else SignalAction.SELL
        return Signal(
            symbol=snapshot.symbol,
            action=action,
            strength=self._strength(current_fast, current_slow),
            as_of=snapshot.as_of,
            strategy=self.name,
            reason=(
                "fast average crossed above slow"
                if crossed_up
                else "fast average crossed below slow"
            ),
            context=self._context(current_fast, current_slow),
        )

    def _strength(self, fast: Decimal, slow: Decimal) -> Decimal:
        """Scale the average spread into [0, 1].

        A crossover that barely happens is noise; one with a wide spread is a
        clearer move. The policy engine turns this into a size, so the strategy
        never expresses conviction in currency units.
        """
        spread_ratio = abs(fast - slow) / slow
        scaled = spread_ratio / self._strength_scale_ratio
        return min(Decimal(1), scaled)

    def _hold(
        self,
        snapshot: MarketSnapshot,
        reason: str,
        fast: Decimal | None = None,
        slow: Decimal | None = None,
    ) -> Signal:
        return Signal(
            symbol=snapshot.symbol,
            action=SignalAction.HOLD,
            strength=Decimal(0),
            as_of=snapshot.as_of,
            strategy=self.name,
            reason=reason,
            context=self._context(fast, slow) if fast is not None and slow is not None else {},
        )

    def _context(self, fast: Decimal, slow: Decimal) -> dict[str, str]:
        return {
            "fast_sma": str(fast),
            "slow_sma": str(slow),
            "fast_window": str(self._fast_window),
            "slow_window": str(self._slow_window),
        }
