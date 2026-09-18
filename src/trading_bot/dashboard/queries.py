from datetime import UTC, datetime, timedelta
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from trading_bot.persistence.models import (
    EquitySnapshotRecord,
    FillRecord,
    OrderRecord,
    PositionRecord,
    SignalRecord,
)

# The dashboard reads and never writes. Every query in this module is a select,
# which is what lets the page be served by an identity holding nothing but read
# access to the same database the bot owns.


class EquityPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    taken_at: datetime
    equity: Decimal
    drawdown_ratio: Decimal


class OrderRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    created_at: datetime
    client_order_id: str
    symbol: str
    side: str
    quantity: Decimal
    reference_price: Decimal
    status: str
    decision_reason: str
    filled_quantity: Decimal
    fees_quote: Decimal


class PositionRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: str
    quantity: Decimal
    average_price: Decimal
    updated_at: datetime


class DecisionRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    as_of: datetime
    action: str
    reason: str
    strategy: str


class Overview(BaseModel):
    """Everything the page needs, resolved in one place.

    Assembled here rather than in the route so the template receives finished
    values and cannot trigger a query while rendering: a lazy relationship read
    from a template is the classic way a page ends up issuing one query per row.
    """

    model_config = ConfigDict(frozen=True)

    equity_curve: tuple[EquityPoint, ...]
    orders: tuple[OrderRow, ...]
    positions: tuple[PositionRow, ...]
    decisions: tuple[DecisionRow, ...]
    latest: EquityPoint | None
    minutes_since_last_cycle: int | None

    @property
    def is_stale(self) -> bool:
        """Whether the bot appears to have stopped.

        Forty-five minutes is three missed cycles at the default cadence, the
        same threshold the no-cycle alert uses. The page and the alert agreeing
        matters: a dashboard that looks healthy while an alert is firing is
        worse than no dashboard.
        """
        return self.minutes_since_last_cycle is None or self.minutes_since_last_cycle > 45


def load_overview(session: Session, *, history_hours: int = 24, limit: int = 20) -> Overview:
    since = datetime.now(tz=UTC) - timedelta(hours=history_hours)

    snapshots = session.scalars(
        select(EquitySnapshotRecord)
        .where(EquitySnapshotRecord.taken_at >= since)
        .order_by(EquitySnapshotRecord.taken_at.asc())
    ).all()

    curve = tuple(
        EquityPoint(
            taken_at=row.taken_at,
            equity=row.equity_quote,
            drawdown_ratio=_drawdown(row),
        )
        for row in snapshots
    )

    # The most recent snapshot overall, not the most recent within the window,
    # so an idle bot still shows its last known equity instead of an empty page.
    latest_record = session.scalars(
        select(EquitySnapshotRecord).order_by(desc(EquitySnapshotRecord.taken_at)).limit(1)
    ).first()
    latest = (
        EquityPoint(
            taken_at=latest_record.taken_at,
            equity=latest_record.equity_quote,
            drawdown_ratio=_drawdown(latest_record),
        )
        if latest_record is not None
        else None
    )

    minutes_since = (
        int((datetime.now(tz=UTC) - latest_record.taken_at).total_seconds() // 60)
        if latest_record is not None
        else None
    )

    return Overview(
        equity_curve=curve,
        orders=_orders(session, limit),
        positions=_positions(session),
        decisions=_decisions(session, limit),
        latest=latest,
        minutes_since_last_cycle=minutes_since,
    )


def _drawdown(record: EquitySnapshotRecord) -> Decimal:
    loss = record.day_opening_equity - record.equity_quote
    if loss <= 0:
        return Decimal(0)
    return loss / record.day_opening_equity


def _orders(session: Session, limit: int) -> tuple[OrderRow, ...]:
    # Fills are aggregated in the query rather than walked per order, so the
    # page costs one round trip no matter how many orders it shows.
    filled = (
        select(
            FillRecord.order_id.label("order_id"),
            func.sum(FillRecord.quantity).label("filled_quantity"),
            func.sum(FillRecord.fee_quote).label("fees_quote"),
        )
        .group_by(FillRecord.order_id)
        .subquery()
    )

    rows = session.execute(
        select(OrderRecord, filled.c.filled_quantity, filled.c.fees_quote)
        .outerjoin(filled, filled.c.order_id == OrderRecord.id)
        .order_by(desc(OrderRecord.created_at))
        .limit(limit)
    ).all()

    return tuple(
        OrderRow(
            created_at=order.created_at,
            client_order_id=order.client_order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            reference_price=order.reference_price,
            status=order.status,
            decision_reason=order.decision_reason,
            filled_quantity=filled_quantity or Decimal(0),
            fees_quote=fees_quote or Decimal(0),
        )
        for order, filled_quantity, fees_quote in rows
    )


def _positions(session: Session) -> tuple[PositionRow, ...]:
    rows = session.scalars(
        select(PositionRecord).where(PositionRecord.quantity > 0).order_by(PositionRecord.symbol)
    ).all()
    return tuple(
        PositionRow(
            symbol=row.symbol,
            quantity=row.quantity,
            average_price=row.average_price,
            updated_at=row.updated_at,
        )
        for row in rows
    )


def _decisions(session: Session, limit: int) -> tuple[DecisionRow, ...]:
    rows = session.scalars(
        select(SignalRecord).order_by(desc(SignalRecord.as_of)).limit(limit)
    ).all()
    return tuple(
        DecisionRow(
            as_of=row.as_of,
            action=row.action,
            reason=row.reason,
            strategy=row.strategy,
        )
        for row in rows
    )
