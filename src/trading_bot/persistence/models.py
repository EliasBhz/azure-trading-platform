from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

QUANTITY = Numeric(38, 18)
PRICE = Numeric(38, 18)


class Base(DeclarativeBase):
    pass


# Every timestamp column is timezone-aware. A naive timestamp in a system that
# runs in containers in one region and is read from another is a bug waiting for
# a daylight saving transition.
TIMESTAMP = DateTime(timezone=True)


class SignalRecord(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cycle_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32))
    strategy: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(8))
    strength: Mapped[Decimal] = mapped_column(Numeric(6, 5))
    reason: Mapped[str] = mapped_column(Text)
    context: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    as_of: Mapped[datetime] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    __table_args__ = (Index("ix_signals_symbol_as_of", "symbol", "as_of"),)


class OrderRecord(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    client_order_id: Mapped[str] = mapped_column(String(64), unique=True)
    cycle_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[Decimal] = mapped_column(QUANTITY)
    reference_price: Mapped[Decimal] = mapped_column(PRICE)
    status: Mapped[str] = mapped_column(String(20))
    venue_order_id: Mapped[str | None] = mapped_column(String(64), default=None)
    rejection_reason: Mapped[str | None] = mapped_column(Text, default=None)
    decision_reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP)

    fills: Mapped[list["FillRecord"]] = relationship(back_populates="order")


class FillRecord(Base):
    __tablename__ = "fills"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    client_order_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[Decimal] = mapped_column(QUANTITY)
    price: Mapped[Decimal] = mapped_column(PRICE)
    fee_quote: Mapped[Decimal] = mapped_column(PRICE)
    filled_at: Mapped[datetime] = mapped_column(TIMESTAMP)

    order: Mapped[OrderRecord] = relationship(back_populates="fills")


class PositionRecord(Base):
    __tablename__ = "positions"

    symbol: Mapped[str] = mapped_column(String(32), primary_key=True)
    quantity: Mapped[Decimal] = mapped_column(QUANTITY)
    average_price: Mapped[Decimal] = mapped_column(PRICE)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class EquitySnapshotRecord(Base):
    __tablename__ = "equity_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cycle_id: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32))
    mark_price: Mapped[Decimal] = mapped_column(PRICE)
    cash_quote: Mapped[Decimal] = mapped_column(PRICE)
    position_quantity: Mapped[Decimal] = mapped_column(QUANTITY)
    equity_quote: Mapped[Decimal] = mapped_column(PRICE)
    day_opening_equity: Mapped[Decimal] = mapped_column(PRICE)
    taken_at: Mapped[datetime] = mapped_column(TIMESTAMP)

    __table_args__ = (Index("ix_equity_snapshots_symbol_taken_at", "symbol", "taken_at"),)
