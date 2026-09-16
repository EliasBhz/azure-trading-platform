import pytest

from trading_bot.config import ExchangeBackend, Settings
from trading_bot.errors import ConfigurationError, SandboxGuardError
from trading_bot.exchange.ccxt_sandbox import CcxtSandboxExchange


def test_defaults_are_paper_trading() -> None:
    settings = Settings(_env_file=None)

    assert settings.sandbox is True
    assert settings.exchange_backend is ExchangeBackend.SIMULATED


def test_disabling_sandbox_is_rejected() -> None:
    with pytest.raises(SandboxGuardError):
        Settings(_env_file=None, sandbox=False)


def test_disabling_sandbox_from_the_environment_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOT_SANDBOX", "false")

    with pytest.raises(SandboxGuardError):
        Settings(_env_file=None)


def test_backend_enum_exposes_no_live_member() -> None:
    assert {member.value for member in ExchangeBackend} == {"simulated", "ccxt_sandbox"}


def test_ccxt_backend_requires_credentials() -> None:
    with pytest.raises(ConfigurationError):
        Settings(_env_file=None, exchange_backend=ExchangeBackend.CCXT_SANDBOX)


def test_ccxt_gateway_refuses_to_be_built_outside_sandbox() -> None:
    """The gateway guard is independent of the Settings guard.

    Both have to be defeated to reach a real venue, and they fail for different
    reasons: one on configuration, one on the client's actual endpoints.
    """
    with pytest.raises(SandboxGuardError):
        CcxtSandboxExchange(
            exchange_id="binance",
            api_key="unused",
            api_secret="unused",
            sandbox=False,
        )


def test_settings_reject_unknown_fields() -> None:
    with pytest.raises(ValueError, match="extra_forbidden"):
        Settings(_env_file=None, force_live=True)  # type: ignore[call-arg]


def test_fast_window_must_be_shorter_than_slow_window() -> None:
    with pytest.raises(ConfigurationError):
        Settings(_env_file=None, sma_fast=50, sma_slow=20)
