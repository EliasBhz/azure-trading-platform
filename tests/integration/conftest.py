import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from trading_bot.domain.market import Candle, MarketSnapshot
from trading_bot.domain.orders import Fill, OrderExecution, OrderIntent, OrderStatus
from trading_bot.persistence.database import create_database_engine, create_session_factory
from trading_bot.persistence.models import Base

BASE_TIME = datetime(2026, 1, 1, 12, tzinfo=UTC)
TIMEFRAME = "15m"


class StubExchange:
    """A gateway with scripted market data.

    The simulator is exercised by unit tests; here the point is the pipeline and
    what it writes to PostgreSQL, so the candles are fixed by hand to make the
    strategy produce a chosen signal.
    """

    def __init__(self, closes: list[str], *, now: datetime) -> None:
        self._closes = closes
        self._now = now
        self.submitted: list[OrderIntent] = []

    @property
    def name(self) -> str:
        return "stub"

    def fetch_snapshot(self, symbol: str, timeframe: str, limit: int) -> MarketSnapshot:
        closes = self._closes[-limit:]
        first_open = self._now - timedelta(minutes=15 * len(closes))
        candles = tuple(
            Candle(
                symbol=symbol,
                open_time=first_open + timedelta(minutes=15 * index),
                open=Decimal(close),
                high=Decimal(close),
                low=Decimal(close),
                close=Decimal(close),
                volume=Decimal(1),
            )
            for index, close in enumerate(closes)
        )
        return MarketSnapshot(symbol=symbol, timeframe=timeframe, candles=candles)

    def submit(self, intent: OrderIntent) -> OrderExecution:
        self.submitted.append(intent)
        return OrderExecution(
            intent=intent,
            status=OrderStatus.FILLED,
            venue_order_id=f"stub-{intent.client_order_id}",
            fills=(
                Fill(
                    client_order_id=intent.client_order_id,
                    symbol=intent.symbol,
                    side=intent.side,
                    quantity=intent.quantity,
                    price=intent.reference_price,
                    fee_quote=Decimal(0),
                    filled_at=self._now,
                ),
            ),
        )


class RecordingTelemetry:
    """Telemetry that keeps what it was told, so the wiring can be asserted.

    The exporter itself is not worth testing: it belongs to the Azure SDK. What
    is worth testing is that the cycle calls it at all, because a metric nobody
    records fails silently and is only noticed when a dashboard stays empty.
    """

    def __init__(self) -> None:
        self.equity: list[tuple[Decimal, Decimal]] = []
        self.decisions: list[str] = []
        self.order_latencies: list[str] = []
        self.cycle_durations: list[float] = []
        self.errors: list[str] = []
        self.flushes = 0

    def record_equity(self, *, equity: Decimal, drawdown_ratio: Decimal, symbol: str) -> None:
        self.equity.append((equity, drawdown_ratio))

    def record_decision(self, *, outcome: str, symbol: str) -> None:
        self.decisions.append(outcome)

    def record_order_latency(self, *, milliseconds: float, symbol: str, side: str) -> None:
        self.order_latencies.append(side)

    def record_cycle_duration(self, *, milliseconds: float, symbol: str) -> None:
        self.cycle_durations.append(milliseconds)

    def record_error(self, *, error_type: str) -> None:
        self.errors.append(error_type)

    def flush(self) -> None:
        self.flushes += 1


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set: start PostgreSQL with `make up-db`")
    return url


@pytest.fixture(scope="session")
def engine(database_url: str) -> Iterator[Engine]:
    """Migrate the test database with Alembic rather than `create_all`.

    Creating tables from the models would test the models against themselves and
    leave the migrations unverified, which is exactly the file that breaks a
    deployment.
    """
    os.environ["BOT_DATABASE_URL"] = database_url
    command.upgrade(Config("alembic.ini"), "head")

    engine = create_database_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> Iterator[sessionmaker[Session]]:
    tables = ", ".join(table.name for table in reversed(Base.metadata.sorted_tables))
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield create_session_factory(engine)
