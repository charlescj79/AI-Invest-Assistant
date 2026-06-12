from dataclasses import dataclass

FORBIDDEN_CLAIMS = ("必涨", "稳赚", "保证收益", "无风险")


@dataclass(frozen=True)
class RiskGateDecision:
    allowed: bool
    flags: list[str]


def validate_recommendation_text(*texts: str) -> RiskGateDecision:
    joined = " ".join(texts)
    flags = [f"Forbidden investment claim detected: {claim}" for claim in FORBIDDEN_CLAIMS if claim in joined]
    return RiskGateDecision(allowed=not flags, flags=flags)


def enforce_human_confirmation(recommendation: dict) -> dict:
    recommendation["requires_human_confirmation"] = True
    return recommendation
