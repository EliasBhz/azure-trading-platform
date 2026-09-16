import re
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from trading_bot.domain.decisions import DecisionOutcome, PolicyDecision
from trading_bot.domain.market import MarketSnapshot
from trading_bot.domain.orders import OrderExecution
from trading_bot.domain.portfolio import EquitySnapshot
from trading_bot.domain.signals import Signal
from trading_bot.errors import ExchangeError, TradingBotError
from trading_bot.exchange.base import ExchangeGateway
from trading_bot.exchange.timeframes import is_stale
from trading_bot.execution.ledger import apply_execution
from trading_bot.observability.logging import get_logger
from trading_bot.persistence import repository
from trading_bot.policy.engine import PolicyEngine
from trading_bot.policy.kill_switch import KillSwitchSource
from trading_bot.strategy.base import Strategy

logger = get_logger(__name__)

MAX_SNAPSHOT_AGE_FACTOR = 3
_NON_ALPHANUMERIC = re.compile(r"[^A-Za-z0-9]+")


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


class CycleResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    cycle_id: str
    signal: Signal
    decision: PolicyDecision
    execution: OrderExecution | None
    equity: EquitySnapshot
    duplicate_suppressed: bool = False


def build_cycle_id(snapshot: MarketSnapshot) -> str:
    """Identify a cycle by the bar it acted on, not by the wall clock.

    Two invocations for the same bar produce the same id and therefore the same
    client order id. The venue rejects a repeated client order id, which is what
    actually prevents a retried Container Apps Job execution from doubling the
    position; the database check in the cycle is the local fast path that avoids
    the round trip when the earlier order was committed.
    """
    symbol = _NON_ALPHANUMERIC.sub("", snapshot.symbol).upper()
    bar_epoch = int(snapshot.as_of.timestamp())
    return f"{symbol}-{snapshot.timeframe}-{bar_epoch}"


class TradingCycle:
    """One pass of the pipeline: market data, signal, policy, execution, persistence."""

    def __init__(
        self,
        *,
        gateway: ExchangeGateway,
        strategy: Strategy,
        policy: PolicyEngine,
        kill_switch: KillSwitchSource,
        symbol: str,
        timeframe: str,
        candle_limit: int,
        initial_cash_quote: Decimal,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._gateway = gateway
        self._strategy = strategy
        self._policy = policy
        self._kill_switch = kill_switch
        self._symbol = symbol
        self._timeframe = timeframe
        self._candle_limit = candle_limit
        self._initial_cash_quote = initial_cash_quote
        self._clock = clock

    def run(self, session: Session) -> CycleResult:
        now = self._clock()
        snapshot = self._gateway.fetch_snapshot(self._symbol, self._timeframe, self._candle_limit)

        if is_stale(
            snapshot.as_of,
            timeframe=self._timeframe,
            now=now,
            max_age_factor=MAX_SNAPSHOT_AGE_FACTOR,
        ):
            raise ExchangeError(
                f"market data is stale: newest candle at {snapshot.as_of.isoformat()}, "
                f"now {now.isoformat()}"
            )

        cycle_id = build_cycle_id(snapshot)
        mark_price = snapshot.last_price

        signal = self._strategy.evaluate(snapshot)
        repository.record_signal(session, cycle_id=cycle_id, signal=signal)

        account = repository.load_account_state(
            session,
            symbol=self._symbol,
            initial_cash_quote=self._initial_cash_quote,
            mark_price=mark_price,
            now=now,
        )

        kill_switch_engaged = self._kill_switch.is_engaged()
        decision = self._policy.decide(
            signal=signal,
            account=account,
            mark_price=mark_price,
            kill_switch_engaged=kill_switch_engaged,
            now=now,
            cycle_id=cycle_id,
        )

        logger.info(
            "cycle.decision",
            cycle_id=cycle_id,
            venue=self._gateway.name,
            symbol=self._symbol,
            mark_price=str(mark_price),
            signal_action=signal.action.value,
            signal_strength=str(signal.strength),
            outcome=decision.outcome.value,
            reason=decision.reason,
            kill_switch_engaged=kill_switch_engaged,
            failed_checks=[check.name.value for check in decision.failed_checks],
        )

        execution: OrderExecution | None = None
        duplicate_suppressed = False
        cash = account.cash_quote
        position = account.position

        if decision.outcome is DecisionOutcome.SUBMIT:
            intent = decision.intent
            if intent is None:
                raise TradingBotError("a submit decision reached execution without an intent")
            if repository.already_executed(session, client_order_id=intent.client_order_id):
                duplicate_suppressed = True
                logger.warning(
                    "cycle.duplicate_suppressed",
                    cycle_id=cycle_id,
                    client_order_id=intent.client_order_id,
                )
            else:
                execution = self._gateway.submit(intent)
                repository.record_execution(
                    session, cycle_id=cycle_id, decision=decision, execution=execution
                )
                update = apply_execution(cash_quote=cash, position=position, execution=execution)
                cash = update.cash_quote
                position = update.position
                repository.save_position(session, position=position, now=now)
                logger.info(
                    "cycle.executed",
                    cycle_id=cycle_id,
                    client_order_id=intent.client_order_id,
                    status=execution.status.value,
                    filled_quantity=str(execution.filled_quantity),
                    fees_quote=str(update.fees_quote),
                )

        equity = EquitySnapshot(
            taken_at=now,
            symbol=self._symbol,
            mark_price=mark_price,
            cash_quote=cash,
            position_quantity=position.quantity,
            equity_quote=cash + position.notional_at(mark_price),
            day_opening_equity=account.day_opening_equity,
        )
        repository.record_equity_snapshot(session, cycle_id=cycle_id, snapshot=equity)

        logger.info(
            "cycle.completed",
            cycle_id=cycle_id,
            equity_quote=str(equity.equity_quote),
            cash_quote=str(equity.cash_quote),
            position_quantity=str(equity.position_quantity),
            drawdown_ratio=str(equity.drawdown_ratio),
        )

        return CycleResult(
            cycle_id=cycle_id,
            signal=signal,
            decision=decision,
            execution=execution,
            equity=equity,
            duplicate_suppressed=duplicate_suppressed,
        )
