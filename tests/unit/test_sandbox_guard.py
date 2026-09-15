import pytest

from trading_bot.config import ExchangeBackend, Settings
from trading_bot.errors import SandboxGuardError


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
