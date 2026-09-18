import sys

from trading_bot.bootstrap import build_cycle, build_telemetry_exporter
from trading_bot.config import Settings
from trading_bot.errors import TradingBotError
from trading_bot.observability.logging import configure_logging, get_logger
from trading_bot.persistence.database import create_database_engine, create_session_factory

EXIT_OK = 0
EXIT_FAILED = 1


def main() -> int:
    """Run exactly one trading cycle and exit.

    The process owns no scheduler and no retry loop: Container Apps Jobs supply
    both, and a non-zero exit is what makes a failed cycle visible to Azure
    Monitor. Swallowing an error here would turn an alertable failure into
    silence. See ADR-0003.
    """
    settings = Settings()
    configure_logging(settings.log_level.value, environment=settings.environment)
    logger = get_logger(__name__)

    telemetry = build_telemetry_exporter(settings)
    engine = create_database_engine(settings.require_database_url())
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            result = build_cycle(settings, telemetry).run(session)
            session.commit()
    except TradingBotError as error:
        telemetry.record_error(error_type=type(error).__name__)
        logger.error("cycle.failed", error_type=type(error).__name__, error=str(error))
        return EXIT_FAILED
    except Exception as error:
        telemetry.record_error(error_type=type(error).__name__)
        logger.exception("cycle.crashed", error_type=type(error).__name__, error=str(error))
        return EXIT_FAILED
    finally:
        # Before engine.dispose and before returning: the exporter publishes on
        # a timer measured in tens of seconds, and this process lives for two.
        # Without this, every metric is lost and nothing reports an error.
        telemetry.flush()
        engine.dispose()

    logger.info("cycle.exit", cycle_id=result.cycle_id, outcome=result.decision.outcome.value)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
