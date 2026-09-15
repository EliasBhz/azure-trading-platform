import pytest

from trading_bot.observability.logging import REDACTED, redact_sensitive


@pytest.mark.parametrize(
    "key",
    [
        "api_key",
        "apiKey",
        "exchange_api_secret",
        "password",
        "access_token",
        "database_connection_string",
        "sas_url",
    ],
)
def test_credential_shaped_keys_are_masked(key: str) -> None:
    result = redact_sensitive(None, "info", {key: "hunter2"})

    assert result[key] == REDACTED


def test_ordinary_fields_are_left_alone() -> None:
    result = redact_sensitive(None, "info", {"symbol": "BTC/USDT", "equity_quote": "10000"})

    assert result == {"symbol": "BTC/USDT", "equity_quote": "10000"}


def test_nested_credentials_are_masked_too() -> None:
    result = redact_sensitive(None, "info", {"venue": {"id": "binance", "secret": "hunter2"}})

    assert result["venue"] == {"id": "binance", "secret": REDACTED}
