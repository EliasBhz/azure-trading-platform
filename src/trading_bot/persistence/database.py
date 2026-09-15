from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

PSYCOPG_DRIVER = "postgresql+psycopg"


def normalise_dsn(dsn: str) -> str:
    """Pin the DSN to psycopg 3.

    A bare `postgresql://` URL makes SQLAlchemy pick whichever driver happens to
    be importable. Naming the driver means the container and a developer's
    machine cannot end up on different ones.
    """
    scheme, separator, rest = dsn.partition("://")
    if not separator:
        raise ValueError(f"not a database URL: {dsn!r}")
    if scheme in {"postgres", "postgresql"}:
        return f"{PSYCOPG_DRIVER}://{rest}"
    return dsn


def create_database_engine(dsn: str) -> Engine:
    """Build an engine sized for a short-lived job.

    `pool_pre_ping` costs one round trip per checkout and removes the class of
    failure where a connection that the server closed in the meantime surfaces
    as a cycle failure.
    """
    return create_engine(
        normalise_dsn(dsn),
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        future=True,
    )


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
