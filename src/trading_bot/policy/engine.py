from datetime import datetime
from decimal import ROUND_DOWN, Decimal

from trading_bot.domain.decisions import (
    DecisionOutcome,
    PolicyDecision,
    RiskCheck,
    RiskCheckName,
)
from trading_bot.domain.orders import OrderIntent, OrderSide
from trading_bot.domain.portfolio import AccountState
from trading_bot.domain.signals import Signal, SignalAction
from trading_bot.policy.limits import RiskLimits

QUANTITY_STEP = Decimal("0.00000001")


class PolicyEngine:
    """Turns a signal into an order intent, or into a recorded refusal.

    Pure and deterministic: same inputs, same decision. It never reads the
    clock, the network or the database, which is what allows a disputed decision
    to be replayed exactly from persisted data.

    This is the only place where an order acquires a size. A strategy cannot
    express conviction in currency, so no strategy change can breach a limit.
    """

    def __init__(self, limits: RiskLimits) -> None:
        self._limits = limits

    def decide(
        self,
        *,
        signal: Signal,
        account: AccountState,
        mark_price: Decimal,
        kill_switch_engaged: bool,
        now: datetime,
        cycle_id: str,
    ) -> PolicyDecision:
        checks: list[RiskCheck] = []

        if kill_switch_engaged:
            checks.append(
                RiskCheck(
                    name=RiskCheckName.KILL_SWITCH,
                    passed=False,
                    detail="kill switch is engaged",
                )
            )
            return self._hold(checks, "kill switch is engaged")
        checks.append(
            RiskCheck(name=RiskCheckName.KILL_SWITCH, passed=True, detail="kill switch is clear")
        )

        daily_pnl = account.daily_pnl_at(mark_price)
        loss_budget_breached = daily_pnl <= -self._limits.max_daily_loss_quote
        checks.append(
            RiskCheck(
                name=RiskCheckName.DAILY_LOSS,
                passed=not loss_budget_breached,
                detail=(
                    f"daily pnl {daily_pnl} against a limit of -{self._limits.max_daily_loss_quote}"
                ),
            )
        )
        if loss_budget_breached:
            return self._hold(checks, "daily loss limit reached")

        actionable = signal.action is not SignalAction.HOLD
        checks.append(
            RiskCheck(
                name=RiskCheckName.ACTIONABLE_SIGNAL,
                passed=actionable,
                detail=f"signal action is {signal.action}",
            )
        )
        if not actionable:
            return self._hold(checks, signal.reason)

        if signal.action is SignalAction.BUY:
            return self._decide_buy(
                signal=signal,
                account=account,
                mark_price=mark_price,
                now=now,
                cycle_id=cycle_id,
                checks=checks,
            )
        return self._decide_sell(
            signal=signal,
            account=account,
            mark_price=mark_price,
            now=now,
            cycle_id=cycle_id,
            checks=checks,
        )

    def _decide_buy(
        self,
        *,
        signal: Signal,
        account: AccountState,
        mark_price: Decimal,
        now: datetime,
        cycle_id: str,
        checks: list[RiskCheck],
    ) -> PolicyDecision:
        held_notional = account.position.notional_at(mark_price)
        headroom = self._limits.max_position_quote - held_notional
        checks.append(
            RiskCheck(
                name=RiskCheckName.POSITION_LIMIT,
                passed=headroom > 0,
                detail=(
                    f"position {held_notional} of a maximum "
                    f"{self._limits.max_position_quote}, headroom {headroom}"
                ),
            )
        )
        if headroom <= 0:
            return self._hold(checks, "position limit reached")

        desired = self._limits.max_position_quote * signal.strength
        notional = min(desired, headroom)

        affordable = account.cash_quote > 0
        checks.append(
            RiskCheck(
                name=RiskCheckName.AVAILABLE_CASH,
                passed=affordable,
                detail=f"cash {account.cash_quote}, requested notional {notional}",
            )
        )
        if not affordable:
            return self._hold(checks, "no cash available")
        notional = min(notional, account.cash_quote)

        quantity = self._quantize(notional / mark_price)
        return self._finalise(
            side=OrderSide.BUY,
            signal=signal,
            quantity=quantity,
            mark_price=mark_price,
            now=now,
            cycle_id=cycle_id,
            checks=checks,
        )

    def _decide_sell(
        self,
        *,
        signal: Signal,
        account: AccountState,
        mark_price: Decimal,
        now: datetime,
        cycle_id: str,
        checks: list[RiskCheck],
    ) -> PolicyDecision:
        held = account.position.quantity
        checks.append(
            RiskCheck(
                name=RiskCheckName.AVAILABLE_INVENTORY,
                passed=held > 0,
                detail=f"holding {held} {signal.symbol}",
            )
        )
        if held <= 0:
            return self._hold(checks, "nothing to sell: short selling is not supported")

        quantity = self._quantize(held * signal.strength)
        return self._finalise(
            side=OrderSide.SELL,
            signal=signal,
            quantity=quantity,
            mark_price=mark_price,
            now=now,
            cycle_id=cycle_id,
            checks=checks,
        )

    def _finalise(
        self,
        *,
        side: OrderSide,
        signal: Signal,
        quantity: Decimal,
        mark_price: Decimal,
        now: datetime,
        cycle_id: str,
        checks: list[RiskCheck],
    ) -> PolicyDecision:
        notional = quantity * mark_price
        large_enough = quantity > 0 and notional >= self._limits.min_order_notional_quote
        checks.append(
            RiskCheck(
                name=RiskCheckName.MIN_NOTIONAL,
                passed=large_enough,
                detail=(
                    f"notional {notional} against a minimum of "
                    f"{self._limits.min_order_notional_quote}"
                ),
            )
        )
        if not large_enough:
            return self._hold(checks, "order would be below the minimum notional")

        intent = OrderIntent(
            client_order_id=f"{cycle_id}-{side.value}",
            symbol=signal.symbol,
            side=side,
            quantity=quantity,
            reference_price=mark_price,
            created_at=now,
        )
        return PolicyDecision(
            outcome=DecisionOutcome.SUBMIT,
            reason=signal.reason,
            checks=tuple(checks),
            intent=intent,
        )

    @staticmethod
    def _quantize(quantity: Decimal) -> Decimal:
        """Round down to the venue's smallest increment.

        Rounding down rather than to nearest: rounding up can ask for slightly
        more than the limit allows or slightly more than the cash on hand.
        """
        return quantity.quantize(QUANTITY_STEP, rounding=ROUND_DOWN)

    @staticmethod
    def _hold(checks: list[RiskCheck], reason: str) -> PolicyDecision:
        return PolicyDecision(
            outcome=DecisionOutcome.HOLD,
            reason=reason,
            checks=tuple(checks),
            intent=None,
        )
