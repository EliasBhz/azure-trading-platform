from datetime import datetime
from decimal import Decimal
from typing import Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Candle(BaseModel):
    """One OHLCV bar.

    Prices are Decimal rather than float: exchange APIs return decimal strings,
    and rounding them through binary floating point before sizing an order
    introduces errors that are invisible in tests and expensive in production.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    open_time: AwareDatetime
    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)
    volume: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def check_bounds(self) -> Self:
        if self.high < self.low:
            raise ValueError("high is below low")
        if not (self.low <= self.open <= self.high):
            raise ValueError("open is outside the low-high range")
        if not (self.low <= self.close <= self.high):
            raise ValueError("close is outside the low-high range")
        return self


class MarketSnapshot(BaseModel):
    """The market data a single cycle observed, kept together so that the
    strategy and the policy engine see exactly the same view."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    timeframe: str
    candles: tuple[Candle, ...] = Field(min_length=1)

    @property
    def last(self) -> Candle:
        return self.candles[-1]

    @property
    def last_price(self) -> Decimal:
        return self.last.close

    @property
    def as_of(self) -> datetime:
        return self.last.open_time

    @model_validator(mode="after")
    def check_ordering(self) -> Self:
        times = [candle.open_time for candle in self.candles]
        if times != sorted(times):
            raise ValueError("candles are not in ascending time order")
        if len(set(times)) != len(times):
            raise ValueError("candles contain duplicate open times")
        if any(candle.symbol != self.symbol for candle in self.candles):
            raise ValueError("candles do not all belong to the snapshot symbol")
        return self
