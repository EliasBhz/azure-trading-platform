from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from time import perf_counter
from typing import Protocol

from trading_bot.observability.logging import get_logger

logger = get_logger(__name__)

METER_NAME = "trading_bot"


class Telemetry(Protocol):
    """Records what the cycle did, for something outside the process to read.

    A protocol rather than a concrete exporter because the pipeline must run
    identically with telemetry switched off. Local runs and tests use the no-op
    implementation, and no call site has to check whether telemetry exists.
    """

    def record_equity(self, *, equity: Decimal, drawdown_ratio: Decimal, symbol: str) -> None: ...

    def record_decision(self, *, outcome: str, symbol: str) -> None: ...

    def record_order_latency(self, *, milliseconds: float, symbol: str, side: str) -> None: ...

    def record_cycle_duration(self, *, milliseconds: float, symbol: str) -> None: ...

    def record_error(self, *, error_type: str) -> None: ...

    def flush(self) -> None: ...


class NullTelemetry:
    """Telemetry that records nothing. The default."""

    def record_equity(self, *, equity: Decimal, drawdown_ratio: Decimal, symbol: str) -> None:
        return None

    def record_decision(self, *, outcome: str, symbol: str) -> None:
        return None

    def record_order_latency(self, *, milliseconds: float, symbol: str, side: str) -> None:
        return None

    def record_cycle_duration(self, *, milliseconds: float, symbol: str) -> None:
        return None

    def record_error(self, *, error_type: str) -> None:
        return None

    def flush(self) -> None:
        return None


class AzureMonitorTelemetry:
    """Custom metrics exported to Application Insights through OpenTelemetry.

    Equity and drawdown are gauges rather than counters: they are a level, not
    an accumulation, and a counter would make every dashboard query wrong in a
    way that is hard to notice.

    The metric names are deliberately flat and prefixed. Application Insights
    exposes custom metrics by name, and a rename silently breaks every alert and
    workbook that referenced the old one.
    """

    def __init__(self, connection_string: str) -> None:
        # Imported here so that a run without the telemetry extra installed, or
        # without a connection string, never touches the Azure SDK at all.
        from azure.monitor.opentelemetry import configure_azure_monitor
        from opentelemetry import metrics

        configure_azure_monitor(connection_string=connection_string)

        meter = metrics.get_meter(METER_NAME)

        self._equity = meter.create_gauge(
            "trading.equity",
            unit="1",
            description="Account equity in the quote currency.",
        )
        self._drawdown = meter.create_gauge(
            "trading.drawdown_ratio",
            unit="1",
            description="Intraday drawdown against the day's opening equity, as a fraction.",
        )
        self._decisions = meter.create_counter(
            "trading.decisions",
            unit="1",
            description="Policy decisions, by outcome.",
        )
        self._order_latency = meter.create_histogram(
            "trading.order.latency",
            unit="ms",
            description="Time between submitting an order and the venue answering.",
        )
        self._cycle_duration = meter.create_histogram(
            "trading.cycle.duration",
            unit="ms",
            description="Wall clock duration of one trading cycle.",
        )
        self._errors = meter.create_counter(
            "trading.errors",
            unit="1",
            description="Failed cycles, by error type.",
        )

    def record_equity(self, *, equity: Decimal, drawdown_ratio: Decimal, symbol: str) -> None:
        attributes = {"symbol": symbol}
        self._equity.set(float(equity), attributes)
        self._drawdown.set(float(drawdown_ratio), attributes)

    def record_decision(self, *, outcome: str, symbol: str) -> None:
        self._decisions.add(1, {"outcome": outcome, "symbol": symbol})

    def record_order_latency(self, *, milliseconds: float, symbol: str, side: str) -> None:
        self._order_latency.record(milliseconds, {"symbol": symbol, "side": side})

    def record_cycle_duration(self, *, milliseconds: float, symbol: str) -> None:
        self._cycle_duration.record(milliseconds, {"symbol": symbol})

    def record_error(self, *, error_type: str) -> None:
        self._errors.add(1, {"error_type": error_type})

    def flush(self) -> None:
        """Export before the process exits.

        This is the detail that makes telemetry work at all in a job. The SDK
        exports metrics on a periodic timer measured in tens of seconds, and a
        trading cycle finishes in a couple of seconds. Without an explicit
        flush, the process exits first and every metric is lost, silently and
        with no error anywhere.
        """
        from opentelemetry import metrics

        provider = metrics.get_meter_provider()
        force_flush = getattr(provider, "force_flush", None)
        if force_flush is None:
            logger.warning("telemetry.flush_unsupported", provider=type(provider).__name__)
            return
        force_flush()


def build_telemetry(connection_string: str | None) -> Telemetry:
    """Return an exporter, or a no-op when there is nowhere to export to."""
    if not connection_string:
        return NullTelemetry()

    try:
        return AzureMonitorTelemetry(connection_string)
    except Exception as error:
        # Losing telemetry must never stop the bot trading. The inverse, a
        # trading cycle that fails because a monitoring dependency is
        # unavailable, turns an observability problem into an outage.
        logger.warning(
            "telemetry.unavailable",
            error_type=type(error).__name__,
            error=str(error),
        )
        return NullTelemetry()


@contextmanager
def measure() -> Iterator[list[float]]:
    """Measure a block in milliseconds.

    The elapsed value is appended on exit, so a caller reads `result[0]` after
    the block. `perf_counter` and not `time`: it is monotonic, so a clock
    adjustment during the block cannot produce a negative duration.
    """
    started = perf_counter()
    result: list[float] = []
    try:
        yield result
    finally:
        result.append((perf_counter() - started) * 1000)
