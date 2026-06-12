from app.recommendations.risk_gate import enforce_human_confirmation, validate_recommendation_text


def test_forbidden_claims_are_blocked():
    decision = validate_recommendation_text("这个策略保证收益")
    assert not decision.allowed
    assert decision.flags


def test_human_confirmation_is_forced():
    recommendation = enforce_human_confirmation({"requires_human_confirmation": False})
    assert recommendation["requires_human_confirmation"] is True
