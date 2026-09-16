from datetime import UTC, datetime, time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from trading_bot.domain.decisions import PolicyDecision
from trading_bot.domain.orders import OrderExecution
from trading_bot.domain.portfolio import AccountState, EquitySnapshot, Position
from trading_bot.domain.signals import Signal
from trading_bot.persistence.models import (
    EquitySnapshotRecord,
    FillRecord,
    OrderRecord,
    PositionRecord,
    SignalRecord,
)


def load_position(session: Session, symbol: str) -> Position:
    record = session.get(PositionRecord, symbol)
    if record is None:
        return Position(symbol=symbol, quantity=Decimal(0), average_price=Decimal(0))
    return Position(
        symbol=record.symbol,
        quantity=record.quantity,
        average_price=record.average_price,
    )


def latest_snapshot_for(session: Session, *, symbol: str) -> EquitySnapshotRecord | None:
    return session.scalars(
        select(EquitySnapshotRecord)
        .where(EquitySnapshotRecord.symbol == symbol)
        .order_by(EquitySnapshotRecord.taken_at.desc())
        .limit(1)
    ).first()


def day_opening_equity(
    session: Session,
    *,
    symbol: str,
    now: datetime,
    fallback: Decimal,
) -> Decimal:
    """Equity at the first snapshot of the current UTC day.

    The daily loss limit is measured against this, so the boundary has to be
    explicit and identical everywhere. UTC is chosen because the venue, the job
    schedule and the logs all use it; a local midnight would move the limit
    twice a year.
    """
    day_start = datetime.combine(now.astimezone(UTC).date(), time.min, tzinfo=UTC)
    first = session.scalars(
        select(EquitySnapshotRecord)
        .where(
            EquitySnapshotRecord.symbol == symbol,
            EquitySnapshotRecord.taken_at >= day_start,
        )
        .order_by(EquitySnapshotRecord.taken_at.asc())
        .limit(1)
    ).first()
    if first is None:
        return fallback
    return first.equity_quote


def load_account_state(
    session: Session,
    *,
    symbol: str,
    initial_cash_quote: Decimal,
    mark_price: Decimal,
    now: datetime,
) -> AccountState:
    """Rebuild the ledger the bot reasons about.

    Cash is carried by the most recent equity snapshot rather than by a separate
    balances table: the snapshot is already the audit record of what the bot
    believed at a point in time, and a second source of truth for the same
    number is how the two drift apart.
    """
    latest = latest_snapshot_for(session, symbol=symbol)
    cash = latest.cash_quote if latest is not None else initial_cash_quote
    position = load_position(session, symbol)
    equity_now = cash + position.notional_at(mark_price)

    return AccountState(
        cash_quote=cash,
        position=position,
        day_opening_equity=day_opening_equity(session, symbol=symbol, now=now, fallback=equity_now),
    )


def record_signal(session: Session, *, cycle_id: str, signal: Signal) -> None:
    session.add(
        SignalRecord(
            cycle_id=cycle_id,
            symbol=signal.symbol,
            strategy=signal.strategy,
            action=signal.action.value,
            strength=signal.strength,
            reason=signal.reason,
            context=signal.context,
            as_of=signal.as_of,
        )
    )


def record_execution(
    session: Session,
    *,
    cycle_id: str,
    decision: PolicyDecision,
    execution: OrderExecution,
) -> OrderRecord:
    intent = execution.intent
    order = OrderRecord(
        client_order_id=intent.client_order_id,
        cycle_id=cycle_id,
        symbol=intent.symbol,
        side=intent.side.value,
        quantity=intent.quantity,
        reference_price=intent.reference_price,
        status=execution.status.value,
        venue_order_id=execution.venue_order_id,
        rejection_reason=execution.rejection_reason,
        decision_reason=decision.reason,
        created_at=intent.created_at,
    )
    order.fills = [
        FillRecord(
            client_order_id=fill.client_order_id,
            symbol=fill.symbol,
            side=fill.side.value,
            quantity=fill.quantity,
            price=fill.price,
            fee_quote=fill.fee_quote,
            filled_at=fill.filled_at,
        )
        for fill in execution.fills
    ]
    session.add(order)
    return order


def save_position(session: Session, *, position: Position, now: datetime) -> None:
    record = session.get(PositionRecord, position.symbol)
    if record is None:
        session.add(
            PositionRecord(
                symbol=position.symbol,
                quantity=position.quantity,
                average_price=position.average_price,
                updated_at=now,
            )
        )
        return
    record.quantity = position.quantity
    record.average_price = position.average_price
    record.updated_at = now


def record_equity_snapshot(
    session: Session,
    *,
    cycle_id: str,
    snapshot: EquitySnapshot,
) -> None:
    session.add(
        EquitySnapshotRecord(
            cycle_id=cycle_id,
            symbol=snapshot.symbol,
            mark_price=snapshot.mark_price,
            cash_quote=snapshot.cash_quote,
            position_quantity=snapshot.position_quantity,
            equity_quote=snapshot.equity_quote,
            day_opening_equity=snapshot.day_opening_equity,
            taken_at=snapshot.taken_at,
        )
    )


def already_executed(session: Session, *, client_order_id: str) -> bool:
    """Whether this exact order was already sent.

    Client order ids are derived from the bar, so a cycle re-run for a bar it
    already traded finds its own earlier order and stops.

    This only covers the case where the order was committed. If the process dies
    between submitting and committing, the row is rolled back and this returns
    False; the venue rejecting the duplicate client order id is what protects
    that window.
    """
    return (
        session.scalars(
            select(OrderRecord.id).where(OrderRecord.client_order_id == client_order_id).limit(1)
        ).first()
        is not None
    )
