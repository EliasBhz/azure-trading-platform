from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from trading_bot.errors import SandboxGuardError


class ExchangeBackend(StrEnum):
    """Supported execution backends.

    There is deliberately no live member. Adding one violates the paper-trading
    invariant documented in CLAUDE.md.
    """

    SIMULATED = "simulated"
    CCXT_SANDBOX = "ccxt_sandbox"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        frozen=True,
    )

    exchange_backend: ExchangeBackend = ExchangeBackend.SIMULATED
    exchange_id: str = "binance"
    sandbox: bool = True
    symbol: str = "BTC/USDT"

    max_position_quote: float = Field(default=1_000.0, gt=0)
    max_daily_loss_quote: float = Field(default=100.0, gt=0)
    kill_switch: bool = False

    @model_validator(mode="after")
    def enforce_sandbox(self) -> Self:
        """Refuse to start unless the process is provably confined to paper trading.

        Runs on every instantiation rather than at the call site so that no code
        path can obtain a Settings object that permits real orders.
        """
        if not self.sandbox:
            raise SandboxGuardError(
                "sandbox mode is disabled: this build only supports paper trading"
            )
        return self
