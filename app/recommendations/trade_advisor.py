from datetime import date

from app.config import get_settings
from app.llm.client import ClaudeClient
from app.llm.prompts import TRADE_ADVICE_INSTRUCTIONS
from app.recommendations.risk_gate import enforce_human_confirmation, validate_recommendation_text
from app.schemas.advice import DISCLAIMER, TradeAdviceOutput


def generate_trade_advice(symbol: str, context: dict, as_of: date | None = None) -> TradeAdviceOutput:
    if get_settings().anthropic_api_key:
        output = ClaudeClient().structured(
            instruction=TRADE_ADVICE_INSTRUCTIONS,
            context={"symbol": symbol, "as_of": as_of.isoformat() if as_of else None, **context},
            output_model=TradeAdviceOutput,
        )
    else:
        output = TradeAdviceOutput(
            action="watch",
            asset=symbol,
            confidence=0.0,
            rationale="Claude API key is not configured, so the system will not generate an actionable suggestion.",
            supporting_data=context.get("supporting_data", []),
            risks=["ANTHROPIC_API_KEY is not configured; no LLM analysis was generated."],
            invalidating_conditions=["Configure Claude and rerun analysis before using this suggestion."],
            suggested_position_limit=0.0,
            requires_human_confirmation=True,
            disclaimer=DISCLAIMER,
        )

    cleaned = enforce_human_confirmation(output.model_dump())
    decision = validate_recommendation_text(cleaned.get("rationale", ""), " ".join(cleaned.get("risks", [])))
    if not decision.allowed:
        cleaned["action"] = "watch"
        cleaned["confidence"] = 0.0
        cleaned["risks"] = [*cleaned.get("risks", []), *decision.flags]
    return TradeAdviceOutput.model_validate(cleaned)
