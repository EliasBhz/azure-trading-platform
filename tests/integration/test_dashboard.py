from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from tests.integration.conftest import TIMEFRAME, StubExchange
from trading_bot.cycle import TradingCycle
from trading_bot.dashboard.app import create_app
from trading_bot.policy.engine import PolicyEngine
from trading_bot.policy.kill_switch import StaticKillSwitch
from trading_bot.policy.limits import RiskLimits
from trading_bot.strategy.sma_crossover import SmaCrossoverStrategy

pytestmark = pytest.mark.integration

FLAT = ["100"] * 8
CROSS_UP = [*FLAT, "104"]

LIMITS = RiskLimits(
    max_position_quote=Decimal(1000),
    max_daily_loss_quote=Decimal(100),
    min_order_notional_quote=Decimal(10),
)


def run_one_cycle(session_factory: sessionmaker[Session], closes: list[str]) -> None:
    """Populate the database the way the bot does.

    The dashboard is tested against rows the real pipeline wrote, not against
    hand-built fixtures: a fixture can satisfy a query the production writer
    would never produce.
    """
    now = datetime.now(tz=UTC)
    cycle = TradingCycle(
        gateway=StubExchange(closes, now=now),
        strategy=SmaCrossoverStrategy(fast_window=2, slow_window=4),
        policy=PolicyEngine(LIMITS),
        kill_switch=StaticKillSwitch(engaged=False),
        symbol="BTC/USDT",
        timeframe=TIMEFRAME,
        candle_limit=50,
        initial_cash_quote=Decimal(10_000),
        clock=lambda: now,
    )
    with session_factory() as session:
        cycle.run(session)
        session.commit()


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> TestClient:
    return TestClient(create_app(session_factory))


def test_liveness_does_not_touch_the_database(client: TestClient) -> None:
    """A health check that fails during a database outage makes the platform
    replace healthy replicas, turning an outage into a restart loop."""
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.text == "ok"


def test_readiness_reports_the_database(client: TestClient) -> None:
    response = client.get("/readyz")

    assert response.status_code == 200


def test_an_empty_database_renders_rather_than_failing(client: TestClient) -> None:
    """A fresh environment has no rows at all. The page has to say so instead of
    raising, because that is exactly when someone looks at it."""
    response = client.get("/")

    assert response.status_code == 200
    assert "No cycle has ever completed" in response.text
    assert "Flat. The bot holds nothing." in response.text


def test_the_page_shows_a_filled_order_and_its_reason(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    run_one_cycle(session_factory, CROSS_UP)

    response = client.get("/")

    assert response.status_code == 200
    assert "fast average crossed above slow" in response.text
    assert "buy" in response.text


def test_refusals_appear_beside_orders(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """Why the bot did nothing is the question this project has to answer, so a
    hold has to be visible on the page and not only in the database."""
    run_one_cycle(session_factory, FLAT)

    response = client.get("/")

    assert "no crossover on the latest candle" in response.text
    assert "hold" in response.text


def test_the_fragment_carries_its_own_polling_attributes(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    """The fragment replaces itself, so losing the attributes would stop the
    page updating after exactly one swap."""
    run_one_cycle(session_factory, CROSS_UP)

    response = client.get("/fragments/overview")

    assert response.status_code == 200
    assert 'hx-get="/fragments/overview"' in response.text
    assert 'hx-swap="outerHTML"' in response.text
    assert "<html" not in response.text


def test_a_stale_database_is_reported_as_stale(
    client: TestClient, session_factory: sessionmaker[Session]
) -> None:
    from trading_bot.persistence.models import EquitySnapshotRecord

    old = datetime.now(tz=UTC) - timedelta(hours=3)
    with session_factory() as session:
        session.add(
            EquitySnapshotRecord(
                cycle_id="OLD",
                symbol="BTC/USDT",
                mark_price=Decimal(100),
                cash_quote=Decimal(10_000),
                position_quantity=Decimal(0),
                equity_quote=Decimal(10_000),
                day_opening_equity=Decimal(10_000),
                taken_at=old,
            )
        )
        session.commit()

    response = client.get("/")

    assert "scheduled runs have been missed" in response.text


def test_the_page_serves_its_own_htmx(client: TestClient) -> None:
    """Vendored rather than loaded from a CDN: an external script in the request
    path of an authenticated page can change, vanish, or observe its readers."""
    response = client.get("/static/htmx.min.js")

    assert response.status_code == 200
    assert "htmx" in response.text[:200]
