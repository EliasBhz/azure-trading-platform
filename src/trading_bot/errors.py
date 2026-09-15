class TradingBotError(Exception):
    """Base class for every error raised by this package."""


class SandboxGuardError(TradingBotError):
    """Raised when the configuration would allow trading outside a sandbox.

    This is a fatal, non-recoverable condition. Callers must not catch it to
    continue execution.
    """
