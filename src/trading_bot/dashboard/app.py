from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from trading_bot.config import Settings
from trading_bot.dashboard.queries import Overview, load_overview
from trading_bot.observability.logging import configure_logging, get_logger
from trading_bot.persistence.database import create_database_engine, create_session_factory

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
STATIC_DIR = Path(__file__).parent / "static"

logger = get_logger(__name__)


def create_app(session_factory: sessionmaker[Session] | None = None) -> FastAPI:
    """Build the dashboard.

    The session factory is injectable so tests drive the real application
    against a real database rather than a mocked one. A dashboard whose tests
    mock the database tests the template and nothing else.
    """
    settings = Settings()
    configure_logging(settings.log_level.value, environment=settings.environment)

    factory = session_factory
    engine = None
    if factory is None:
        engine = create_database_engine(settings.require_database_url())
        factory = create_session_factory(engine)

    app = FastAPI(
        title="Trading bot",
        description="Read-only view of a paper trading bot.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    # htmx is vendored into the image rather than loaded from a CDN. An
    # external script in the request path of an authenticated page is a
    # third-party dependency that can change, disappear, or see who is looking.
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def get_session() -> Iterator[Session]:
        with factory() as session:
            yield session

    # A type alias, not a variable, despite the assignment syntax.
    SessionDep = Annotated[Session, Depends(get_session)]  # noqa: N806

    @app.get("/healthz", response_class=PlainTextResponse)
    def healthz() -> str:
        """Liveness only. Deliberately does not touch the database.

        A health check that fails when the database is briefly unreachable makes
        Container Apps replace a perfectly good replica during an outage it
        cannot fix, turning a database problem into a restart loop.
        """
        return "ok"

    @app.get("/readyz", response_class=PlainTextResponse)
    def readyz(session: SessionDep) -> PlainTextResponse:
        try:
            session.execute(text("SELECT 1"))
        except Exception as error:
            logger.warning("dashboard.not_ready", error_type=type(error).__name__)
            return PlainTextResponse("database unreachable", status_code=503)
        return PlainTextResponse("ok")

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request, session: SessionDep) -> HTMLResponse:
        overview = load_overview(session)
        return TEMPLATES.TemplateResponse(
            request=request,
            name="index.html",
            context={"overview": overview, "sparkline": _sparkline(overview)},
        )

    # HTMX polls this and swaps it into the page. Returning a fragment rather
    # than JSON keeps the rendering in one place: with JSON, the same table
    # exists twice, once in Jinja and once in JavaScript, and the two drift.
    @app.get("/fragments/overview", response_class=HTMLResponse)
    def overview_fragment(request: Request, session: SessionDep) -> HTMLResponse:
        overview = load_overview(session)
        return TEMPLATES.TemplateResponse(
            request=request,
            name="_overview.html",
            context={"overview": overview, "sparkline": _sparkline(overview)},
        )

    app.state.engine = engine
    return app


def _sparkline(overview: Overview, width: int = 720, height: int = 120) -> str:
    """Build the equity curve as an SVG polyline.

    Server-rendered rather than drawn by a charting library: the page then has
    no external script, which keeps it inside a strict content security policy
    and means it renders identically with JavaScript disabled.
    """
    points = overview.equity_curve
    if len(points) < 2:
        return ""

    values = [point.equity for point in points]
    lowest, highest = min(values), max(values)
    span = highest - lowest

    def y_for(value: Decimal) -> float:
        if span == 0:
            return height / 2
        # Inverted: SVG y grows downwards, and a rising equity must rise.
        return float(Decimal(1) - (value - lowest) / span) * (height - 8) + 4

    step = width / (len(values) - 1)
    return " ".join(f"{index * step:.1f},{y_for(value):.1f}" for index, value in enumerate(values))
