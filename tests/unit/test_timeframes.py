from datetime import UTC, datetime, timedelta

import pytest

from trading_bot.errors import ConfigurationError
from trading_bot.exchange.timeframes import floor_to_timeframe, is_stale, parse_timeframe


@pytest.mark.parametrize(
    ("timeframe", "expected"),
    [
        ("1m", timedelta(minutes=1)),
        ("15m", timedelta(minutes=15)),
        ("4h", timedelta(hours=4)),
        ("1d", timedelta(days=1)),
    ],
)
def test_supported_timeframes(timeframe: str, expected: timedelta) -> None:
    assert parse_timeframe(timeframe) == expected


@pytest.mark.parametrize("timeframe", ["", "15", "m15", "0m", "15s", "1M"])
def test_unsupported_timeframes_are_rejected(timeframe: str) -> None:
    with pytest.raises(ConfigurationError):
        parse_timeframe(timeframe)


def test_flooring_aligns_on_the_epoch() -> None:
    moment = datetime(2026, 1, 1, 12, 7, 31, tzinfo=UTC)

    assert floor_to_timeframe(moment, "15m") == datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def test_data_within_the_tolerance_is_fresh() -> None:
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)

    assert not is_stale(now - timedelta(minutes=30), timeframe="15m", now=now, max_age_factor=3)


def test_data_beyond_the_tolerance_is_stale() -> None:
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)

    assert is_stale(now - timedelta(minutes=50), timeframe="15m", now=now, max_age_factor=3)
