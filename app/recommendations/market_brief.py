from datetime import date

from app.config import get_settings
from app.llm.client import ClaudeClient
from app.llm.prompts import MARKET_BRIEF_INSTRUCTIONS
from app.schemas.advice import DISCLAIMER, MarketBriefOutput


def generate_market_brief(context: dict, as_of: date | None = None) -> MarketBriefOutput:
    if get_settings().anthropic_api_key:
        return ClaudeClient().structured(
            instruction=MARKET_BRIEF_INSTRUCTIONS,
            context={"as_of": as_of.isoformat() if as_of else None, **context},
            output_model=MarketBriefOutput,
        )
    return MarketBriefOutput(
        summary="Claude API key is not configured. This placeholder brief summarizes stored data only.",
        key_news=context.get("key_news", []),
        market_regime="unknown",
        watchlist_impacts=[],
        risk_flags=["ANTHROPIC_API_KEY is not configured; no LLM analysis was generated."],
        sources=context.get("sources", []),
        disclaimer=DISCLAIMER,
    )
