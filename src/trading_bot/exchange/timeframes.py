import re
from datetime import datetime, timedelta

from trading_bot.errors import ConfigurationError

_TIMEFRAME = re.compile(r"^(?P<amount>\d+)(?P<unit>[mhdw])$")
_UNITS = {
    "m": "minutes",
    "h": "hours",
    "d": "days",
    "w": "weeks",
}


def parse_timeframe(timeframe: str) -> timedelta:
    """Translate an exchange timeframe such as `15m` into a duration."""
    match = _TIMEFRAME.match(timeframe)
    if match is None:
        raise ConfigurationError(f"unsupported timeframe: {timeframe!r}")

    amount = int(match.group("amount"))
    if amount < 1:
        raise ConfigurationError(f"timeframe amount must be positive: {timeframe!r}")

    return timedelta(**{_UNITS[match.group("unit")]: amount})


def floor_to_timeframe(moment: datetime, timeframe: str) -> datetime:
    """Round a moment down to the start of its bar.

    Bars are aligned on the Unix epoch, as exchanges align them, so the same
    wall-clock instant maps to the same bar whatever the timezone.
    """
    step = parse_timeframe(timeframe)
    epoch = datetime.fromtimestamp(0, tz=moment.tzinfo)
    elapsed = moment - epoch
    return epoch + step * (elapsed // step)


def is_stale(as_of: datetime, *, timeframe: str, now: datetime, max_age_factor: int) -> bool:
    """Whether the newest candle is too old to act on.

    A venue that keeps answering with stale data is more dangerous than one that
    fails outright, because the pipeline would trade on it without noticing.
    """
    return (now - as_of) > parse_timeframe(timeframe) * max_age_factor
