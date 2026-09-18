from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from tests.integration.conftest import TIMEFRAME, RecordingTelemetry, StubExchange
from trading_bot.cycle import TradingCycle
from trading_bot.domain.decisions import DecisionOutcome
from trading_bot.persistence.models import (
    EquitySnapshotRecord,
    FillRecord,
    OrderRecord,
    PositionRecord,
    SignalRecord,
)
from trading_bot.policy.engine import PolicyEngine
from trading_bot.policy.kill_switch import StaticKillSwitch
from trading_bot.policy.limits import RiskLimits
from trading_bot.strategy.sma_crossover import SmaCrossoverStrategy

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)
NEXT_BAR = NOW + timedelta(minutes=15)
SYMBOL = "BTC/USDT"

FLAT = ["100"] * 8
CROSS_UP = [*FLAT, "104"]
CROSS_DOWN_AFTER_UP = [*FLAT, "104", "104", "98"]

LIMITS = RiskLimits(
    max_position_quote=Decimal(1000),
    max_daily_loss_quote=Decimal(100),
    min_order_notional_quote=Decimal(10),
)

# Wide enough that neither the position limit nor cash binds, so a replayed
# cycle still reaches the execution stage and the duplicate guard is what stops
# it, rather than a risk check that happens to fire first.
UNCONSTRAINED = RiskLimits(
    max_position_quote=Decimal(100_000),
    max_daily_loss_quote=Decimal(100_000),
    min_order_notional_quote=Decimal(10),
)


def build_cycle(
    gateway: StubExchange,
    *,
    now: datetime = NOW,
    kill_switch: bool = False,
    limits: RiskLimits = LIMITS,
    initial_cash: Decimal = Decimal(10_000),
    telemetry: RecordingTelemetry | None = None,
) -> TradingCycle:
    return TradingCycle(
        gateway=gateway,
        strategy=SmaCrossoverStrategy(fast_window=2, slow_window=4),
        policy=PolicyEngine(limits),
        kill_switch=StaticKillSwitch(kill_switch),
        telemetry=telemetry,
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        candle_limit=50,
        initial_cash_quote=initial_cash,
        clock=lambda: now,
    )


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_a_hold_cycle_records_the_signal_and_the_equity_but_no_order(
    session_factory: sessionmaker[Session],
) -> None:
    gateway = StubExchange(FLAT, now=NOW)

    with session_factory() as session:
        result = build_cycle(gateway).run(session)
        session.commit()

    assert result.decision.outcome is DecisionOutcome.HOLD
    with session_factory() as session:
        assert count(session, SignalRecord) == 1
        assert count(session, EquitySnapshotRecord) == 1
        assert count(session, OrderRecord) == 0
    assert gateway.submitted == []


def test_a_buy_cycle_persists_the_order_the_fill_and_the_position(
    session_factory: sessionmaker[Session],
) -> None:
    gateway = StubExchange(CROSS_UP, now=NOW)

    with session_factory() as session:
        result = build_cycle(gateway).run(session)
        session.commit()

    assert result.decision.outcome is DecisionOutcome.SUBMIT
    assert result.execution is not None

    with session_factory() as session:
        order = session.scalars(select(OrderRecord)).one()
        fill = session.scalars(select(FillRecord)).one()
        position = session.scalars(select(PositionRecord)).one()
        equity = session.scalars(select(EquitySnapshotRecord)).one()

        assert order.side == "buy"
        assert order.status == "filled"
        assert order.cycle_id == result.cycle_id
        assert fill.order_id == order.id
        assert position.quantity == fill.quantity
        assert equity.cash_quote == Decimal(10_000) - fill.quantity * fill.price
        assert equity.equity_quote == equity.cash_quote + position.quantity * equity.mark_price


def test_the_position_limit_is_enforced_against_the_persisted_position(
    session_factory: sessionmaker[Session],
) -> None:
    """The limit binds across invocations, not just within one.

    The process holds no state between cycles, so a limit that was only checked
    in memory would reset on every job execution.
    """
    gateway = StubExchange(CROSS_UP, now=NOW)

    with session_factory() as session:
        build_cycle(gateway).run(session)
        session.commit()

    with session_factory() as session:
        second = build_cycle(gateway, now=NEXT_BAR).run(session)
        session.commit()

    assert second.decision.outcome is DecisionOutcome.HOLD
    assert len(gateway.submitted) == 1


def test_replaying_the_same_bar_does_not_place_a_second_order(
    session_factory: sessionmaker[Session],
) -> None:
    """A cycle re-run for a bar it already traded is a no-op.

    Client order ids are derived from the bar, so the recorded order is found
    before anything is sent. The venue rejecting a duplicate client order id is
    the actual guarantee; this check is the local fast path that avoids the
    round trip.
    """
    gateway = StubExchange(CROSS_UP, now=NOW)
    cycle = build_cycle(gateway, limits=UNCONSTRAINED, initial_cash=Decimal(1_000_000))

    with session_factory() as session:
        first = cycle.run(session)
        session.commit()

    with session_factory() as session:
        replay = cycle.run(session)
        session.commit()

    assert first.decision.outcome is DecisionOutcome.SUBMIT
    assert replay.decision.outcome is DecisionOutcome.SUBMIT
    assert replay.duplicate_suppressed is True
    assert replay.execution is None
    assert len(gateway.submitted) == 1
    with session_factory() as session:
        assert count(session, OrderRecord) == 1


def test_the_kill_switch_stops_an_otherwise_valid_order(
    session_factory: sessionmaker[Session],
) -> None:
    gateway = StubExchange(CROSS_UP, now=NOW)

    with session_factory() as session:
        result = build_cycle(gateway, kill_switch=True).run(session)
        session.commit()

    assert result.decision.outcome is DecisionOutcome.HOLD
    assert result.decision.reason == "kill switch is engaged"
    assert gateway.submitted == []
    with session_factory() as session:
        assert count(session, OrderRecord) == 0


def test_cash_and_position_carry_across_cycles(
    session_factory: sessionmaker[Session],
) -> None:
    """A later cycle reads the ledger the earlier one wrote.

    The process keeps nothing in memory between invocations, so this is the only
    thing that makes a sequence of independent jobs behave like one strategy.
    """
    buy_gateway = StubExchange(CROSS_UP, now=NOW)
    with session_factory() as session:
        build_cycle(buy_gateway).run(session)
        session.commit()

    sell_gateway = StubExchange(CROSS_DOWN_AFTER_UP, now=NEXT_BAR)
    with session_factory() as session:
        result = build_cycle(sell_gateway, now=NEXT_BAR).run(session)
        session.commit()

    assert result.decision.outcome is DecisionOutcome.SUBMIT
    assert result.execution is not None
    assert result.execution.intent.side.value == "sell"

    with session_factory() as session:
        position = session.scalars(select(PositionRecord)).one()
        bought = Decimal(buy_gateway.submitted[0].quantity)
        sold = Decimal(sell_gateway.submitted[0].quantity)

        assert position.quantity == bought - sold
        assert count(session, OrderRecord) == 2
        assert count(session, EquitySnapshotRecord) == 2


def test_the_daily_loss_limit_reads_the_first_snapshot_of_the_day(
    session_factory: sessionmaker[Session],
) -> None:
    gateway = StubExchange(CROSS_UP, now=NOW)
    collapsed = StubExchange([*FLAT, "104", "104", "20"], now=NEXT_BAR)

    with session_factory() as session:
        build_cycle(gateway).run(session)
        session.commit()

    with session_factory() as session:
        result = build_cycle(collapsed, now=NEXT_BAR).run(session)
        session.commit()

    assert result.decision.outcome is DecisionOutcome.HOLD
    assert result.decision.reason == "daily loss limit reached"
    assert collapsed.submitted == []


def test_a_cycle_records_the_metrics_a_dashboard_needs(
    session_factory: sessionmaker[Session],
) -> None:
    """A metric nobody records fails silently and is only noticed when a
    dashboard stays empty. This asserts the wiring, not the exporter."""
    telemetry = RecordingTelemetry()
    gateway = StubExchange(CROSS_UP, now=NOW)

    with session_factory() as session:
        result = build_cycle(gateway, telemetry=telemetry).run(session)
        session.commit()

    assert telemetry.decisions == [result.decision.outcome.value]
    assert telemetry.order_latencies == ["buy"]
    assert len(telemetry.cycle_durations) == 1
    assert telemetry.equity == [(result.equity.equity_quote, result.equity.drawdown_ratio)]


def test_a_hold_cycle_records_no_order_latency(
    session_factory: sessionmaker[Session],
) -> None:
    telemetry = RecordingTelemetry()
    gateway = StubExchange(FLAT, now=NOW)

    with session_factory() as session:
        build_cycle(gateway, telemetry=telemetry).run(session)
        session.commit()

    assert telemetry.order_latencies == []
    assert telemetry.decisions == ["hold"]
