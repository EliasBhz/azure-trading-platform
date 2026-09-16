from datetime import UTC, datetime
from decimal import Decimal

from trading_bot.domain.decisions import DecisionOutcome, PolicyDecision, RiskCheckName
from trading_bot.domain.orders import OrderSide
from trading_bot.domain.portfolio import AccountState, Position
from trading_bot.domain.signals import Signal, SignalAction
from trading_bot.policy.engine import PolicyEngine
from trading_bot.policy.limits import RiskLimits

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)
MARK = Decimal(100)

LIMITS = RiskLimits(
    max_position_quote=Decimal(1000),
    max_daily_loss_quote=Decimal(100),
    min_order_notional_quote=Decimal(10),
)


def account(
    *,
    cash: str = "10000",
    quantity: str = "0",
    average_price: str = "0",
    day_opening_equity: str = "10000",
) -> AccountState:
    return AccountState(
        cash_quote=Decimal(cash),
        position=Position(
            symbol="BTC/USDT",
            quantity=Decimal(quantity),
            average_price=Decimal(average_price),
        ),
        day_opening_equity=Decimal(day_opening_equity),
    )


def signal(action: SignalAction, strength: str = "1") -> Signal:
    return Signal(
        symbol="BTC/USDT",
        action=action,
        strength=Decimal(strength),
        as_of=NOW,
        strategy="test",
        reason="test signal",
    )


def decide(
    *,
    action: SignalAction = SignalAction.BUY,
    strength: str = "1",
    state: AccountState | None = None,
    kill_switch: bool = False,
) -> PolicyDecision:
    return PolicyEngine(LIMITS).decide(
        signal=signal(action, strength),
        account=state if state is not None else account(),
        mark_price=MARK,
        kill_switch_engaged=kill_switch,
        now=NOW,
        cycle_id="CYCLE1",
    )


def test_kill_switch_stops_everything_before_any_other_check() -> None:
    decision = decide(kill_switch=True)

    assert decision.outcome is DecisionOutcome.HOLD
    assert [check.name for check in decision.checks] == [RiskCheckName.KILL_SWITCH]
    assert decision.intent is None


def test_daily_loss_limit_blocks_new_orders() -> None:
    state = account(cash="9800", day_opening_equity="10000")

    decision = decide(state=state)

    assert decision.outcome is DecisionOutcome.HOLD
    assert decision.reason == "daily loss limit reached"
    assert RiskCheckName.DAILY_LOSS in {check.name for check in decision.failed_checks}


def test_a_loss_just_inside_the_limit_still_trades() -> None:
    state = account(cash="9901", day_opening_equity="10000")

    decision = decide(state=state)

    assert decision.outcome is DecisionOutcome.SUBMIT


def test_a_hold_signal_produces_a_recorded_refusal() -> None:
    decision = decide(action=SignalAction.HOLD)

    assert decision.outcome is DecisionOutcome.HOLD
    assert decision.reason == "test signal"


def test_buy_size_follows_signal_strength() -> None:
    decision = decide(strength="0.5")

    assert decision.intent is not None
    assert decision.intent.side is OrderSide.BUY
    assert decision.intent.notional == Decimal(500)


def test_buy_is_capped_by_the_remaining_position_headroom() -> None:
    state = account(quantity="8", average_price="100")

    decision = decide(state=state)

    assert decision.intent is not None
    assert decision.intent.notional == Decimal(200)


def test_a_full_position_blocks_further_buying() -> None:
    state = account(quantity="10", average_price="100")

    decision = decide(state=state)

    assert decision.outcome is DecisionOutcome.HOLD
    assert decision.reason == "position limit reached"


def test_buy_is_capped_by_available_cash() -> None:
    state = account(cash="250", day_opening_equity="250")

    decision = decide(state=state)

    assert decision.intent is not None
    assert decision.intent.notional <= Decimal(250)


def test_selling_without_inventory_is_refused() -> None:
    decision = decide(action=SignalAction.SELL)

    assert decision.outcome is DecisionOutcome.HOLD
    assert "short selling is not supported" in decision.reason


def test_sell_size_follows_signal_strength() -> None:
    state = account(quantity="2", average_price="100")

    decision = decide(action=SignalAction.SELL, strength="0.5", state=state)

    assert decision.intent is not None
    assert decision.intent.side is OrderSide.SELL
    assert decision.intent.quantity == Decimal("1")


def test_orders_below_the_minimum_notional_are_refused() -> None:
    state = account(quantity="0.05", average_price="100")

    decision = decide(action=SignalAction.SELL, strength="0.01", state=state)

    assert decision.outcome is DecisionOutcome.HOLD
    assert decision.reason == "order would be below the minimum notional"


def test_quantities_are_rounded_down() -> None:
    """Rounding up could ask for marginally more than the limit or the cash."""
    engine = PolicyEngine(
        RiskLimits(
            max_position_quote=Decimal(1000),
            max_daily_loss_quote=Decimal(100),
            min_order_notional_quote=Decimal(1),
        )
    )

    decision = engine.decide(
        signal=signal(SignalAction.BUY, "1"),
        account=account(),
        mark_price=Decimal(3),
        kill_switch_engaged=False,
        now=NOW,
        cycle_id="CYCLE1",
    )

    assert decision.intent is not None
    assert decision.intent.quantity == Decimal("333.33333333")


def test_the_client_order_id_is_derived_from_the_cycle() -> None:
    decision = decide()

    assert decision.intent is not None
    assert decision.intent.client_order_id == "CYCLE1-buy"


def test_every_evaluated_check_is_recorded_even_when_it_passes() -> None:
    decision = decide()

    assert {check.name for check in decision.checks} == {
        RiskCheckName.KILL_SWITCH,
        RiskCheckName.DAILY_LOSS,
        RiskCheckName.ACTIONABLE_SIGNAL,
        RiskCheckName.POSITION_LIMIT,
        RiskCheckName.AVAILABLE_CASH,
        RiskCheckName.MIN_NOTIONAL,
    }
    assert decision.failed_checks == ()
