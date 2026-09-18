from trading_bot.config import ExchangeBackend, Settings
from trading_bot.cycle import TradingCycle
from trading_bot.errors import ConfigurationError
from trading_bot.exchange.base import ExchangeGateway
from trading_bot.exchange.simulated import SimulatedExchange
from trading_bot.observability.telemetry import Telemetry, build_telemetry
from trading_bot.policy.engine import PolicyEngine
from trading_bot.policy.kill_switch import KillSwitchSource, StaticKillSwitch
from trading_bot.policy.limits import RiskLimits
from trading_bot.strategy.sma_crossover import SmaCrossoverStrategy


def build_gateway(settings: Settings) -> ExchangeGateway:
    """Select the venue.

    The composition root is the only place that knows which backend is in use.
    Nothing downstream can tell the difference, which is what keeps the
    simulated and testnet paths honest about each other.
    """
    if settings.exchange_backend is ExchangeBackend.SIMULATED:
        return SimulatedExchange(
            seed=settings.simulator_seed,
            start_price=settings.simulator_start_price,
            volatility_bps=settings.simulator_volatility_bps,
            fee_bps=settings.fee_bps,
            slippage_bps=settings.slippage_bps,
        )

    if settings.exchange_api_key is None or settings.exchange_api_secret is None:
        raise ConfigurationError("exchange credentials are missing")

    from trading_bot.exchange.ccxt_sandbox import CcxtSandboxExchange

    return CcxtSandboxExchange(
        exchange_id=settings.exchange_id,
        api_key=settings.exchange_api_key.get_secret_value(),
        api_secret=settings.exchange_api_secret.get_secret_value(),
        sandbox=settings.sandbox,
    )


def build_kill_switch(settings: Settings) -> KillSwitchSource:
    return StaticKillSwitch(settings.kill_switch)


def build_telemetry_exporter(settings: Settings) -> Telemetry:
    connection_string = settings.applicationinsights_connection_string
    return build_telemetry(
        connection_string.get_secret_value() if connection_string is not None else None
    )


def build_cycle(settings: Settings, telemetry: Telemetry | None = None) -> TradingCycle:
    limits = RiskLimits(
        max_position_quote=settings.max_position_quote,
        max_daily_loss_quote=settings.max_daily_loss_quote,
        min_order_notional_quote=settings.min_order_notional_quote,
    )
    return TradingCycle(
        gateway=build_gateway(settings),
        strategy=SmaCrossoverStrategy(
            fast_window=settings.sma_fast,
            slow_window=settings.sma_slow,
        ),
        policy=PolicyEngine(limits),
        kill_switch=build_kill_switch(settings),
        telemetry=telemetry if telemetry is not None else build_telemetry_exporter(settings),
        symbol=settings.symbol,
        timeframe=settings.timeframe,
        candle_limit=settings.candle_limit,
        initial_cash_quote=settings.initial_cash_quote,
    )
