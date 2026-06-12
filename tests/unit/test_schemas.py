from app.schemas.advice import DISCLAIMER, TradeAdviceOutput


def test_trade_advice_defaults_to_human_confirmation_and_disclaimer():
    output = TradeAdviceOutput(
        action="watch",
        asset="SPY",
        confidence=0.2,
        rationale="Evidence is insufficient.",
    )
    assert output.requires_human_confirmation is True
    assert output.disclaimer == DISCLAIMER
