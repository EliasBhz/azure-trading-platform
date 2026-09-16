class TradingBotError(Exception):
    """Base class for every error raised by this package."""


class SandboxGuardError(TradingBotError):
    """Raised when the configuration would allow trading outside a sandbox.

    This is a fatal, non-recoverable condition. Callers must not catch it to
    continue execution.
    """


class ConfigurationError(TradingBotError):
    """Raised when the configuration is internally inconsistent or incomplete."""


class ExchangeError(TradingBotError):
    """Raised when the venue cannot be reached or returns something unusable."""
