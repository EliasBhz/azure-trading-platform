from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import AliasChoices, Field, PostgresDsn, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from trading_bot.errors import ConfigurationError, SandboxGuardError


class ExchangeBackend(StrEnum):
    """Supported execution backends.

    There is deliberately no live member. Adding one violates the paper-trading
    invariant documented in CLAUDE.md.
    """

    SIMULATED = "simulated"
    CCXT_SANDBOX = "ccxt_sandbox"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="BOT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        frozen=True,
    )

    environment: str = "local"

    exchange_backend: ExchangeBackend = ExchangeBackend.SIMULATED
    exchange_id: str = "binance"
    sandbox: bool = True
    exchange_api_key: SecretStr | None = None
    exchange_api_secret: SecretStr | None = None

    symbol: str = "BTC/USDT"
    timeframe: str = "15m"
    candle_limit: int = Field(default=200, ge=2, le=1000)

    sma_fast: int = Field(default=12, ge=2)
    sma_slow: int = Field(default=48, ge=3)

    initial_cash_quote: Decimal = Field(default=Decimal(10_000), gt=0)
    max_position_quote: Decimal = Field(default=Decimal(1_000), gt=0)
    max_daily_loss_quote: Decimal = Field(default=Decimal(100), gt=0)
    min_order_notional_quote: Decimal = Field(default=Decimal(10), gt=0)
    kill_switch: bool = False

    fee_bps: Decimal = Field(default=Decimal(10), ge=0)
    slippage_bps: Decimal = Field(default=Decimal(5), ge=0)

    simulator_seed: int = 1
    simulator_start_price: Decimal = Field(default=Decimal(30_000), gt=0)
    simulator_volatility_bps: Decimal = Field(default=Decimal(40), gt=0)

    database_url: PostgresDsn | None = None
    log_level: LogLevel = LogLevel.INFO

    # Read from the unprefixed name every Azure tool expects, rather than
    # BOT_-prefixed like the rest. Renaming it would break automatic detection
    # in the OpenTelemetry distro and in anything else that looks for it.
    applicationinsights_connection_string: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("APPLICATIONINSIGHTS_CONNECTION_STRING"),
    )

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

    @model_validator(mode="after")
    def check_strategy_windows(self) -> Self:
        if self.sma_fast >= self.sma_slow:
            raise ConfigurationError("sma_fast must be strictly shorter than sma_slow")
        if self.candle_limit <= self.sma_slow:
            raise ConfigurationError("candle_limit must exceed sma_slow to produce a crossover")
        return self

    @model_validator(mode="after")
    def check_backend_credentials(self) -> Self:
        needs_credentials = self.exchange_backend is ExchangeBackend.CCXT_SANDBOX
        has_credentials = self.exchange_api_key is not None and self.exchange_api_secret is not None
        if needs_credentials and not has_credentials:
            raise ConfigurationError(
                "the ccxt_sandbox backend requires BOT_EXCHANGE_API_KEY and "
                "BOT_EXCHANGE_API_SECRET, which must be testnet keys without "
                "withdrawal permission"
            )
        return self

    def require_database_url(self) -> str:
        """Return the database DSN, or fail loudly.

        The DSN has no default: a hardcoded fallback would put credentials in the
        repository and would let a misconfigured deployment quietly write to the
        wrong database.
        """
        if self.database_url is None:
            raise ConfigurationError("BOT_DATABASE_URL is not set")
        return str(self.database_url)
