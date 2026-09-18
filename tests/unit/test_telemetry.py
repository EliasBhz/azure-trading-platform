from decimal import Decimal

from trading_bot.observability.telemetry import NullTelemetry, build_telemetry, measure


def test_no_connection_string_yields_a_no_op_exporter() -> None:
    assert isinstance(build_telemetry(None), NullTelemetry)
    assert isinstance(build_telemetry(""), NullTelemetry)


def test_an_unusable_connection_string_does_not_stop_the_bot() -> None:
    """Losing telemetry must never stop trading.

    The inverse, a cycle that fails because a monitoring dependency is
    unavailable, turns an observability problem into an outage.
    """
    telemetry = build_telemetry("not-a-connection-string")

    assert isinstance(telemetry, NullTelemetry)


def test_the_no_op_exporter_accepts_every_call() -> None:
    telemetry = NullTelemetry()

    telemetry.record_equity(equity=Decimal(1), drawdown_ratio=Decimal(0), symbol="BTC/USDT")
    telemetry.record_decision(outcome="hold", symbol="BTC/USDT")
    telemetry.record_order_latency(milliseconds=1.0, symbol="BTC/USDT", side="buy")
    telemetry.record_cycle_duration(milliseconds=1.0, symbol="BTC/USDT")
    telemetry.record_error(error_type="ExchangeError")
    telemetry.flush()


def test_measure_reports_a_duration_even_when_the_block_raises() -> None:
    try:
        with measure() as elapsed:
            raise ValueError("boom")
    except ValueError:
        pass

    assert len(elapsed) == 1
    assert elapsed[0] >= 0
