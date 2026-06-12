from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Asset, DailyBrief, RecommendationStatus, TradeRecommendation
from app.db.session import get_db
from app.recommendations.market_brief import generate_market_brief
from app.recommendations.trade_advisor import generate_trade_advice
from app.schemas.advice import (
    GenerateAdviceRequest,
    GenerateBriefRequest,
    MarketBriefOutput,
    TradeRecommendationRead,
)

router = APIRouter(tags=["advice"])


@router.post("/briefs/daily/generate", response_model=MarketBriefOutput)
def generate_daily_brief(payload: GenerateBriefRequest, db: Session = Depends(get_db)) -> MarketBriefOutput:
    as_of = payload.date or date.today()
    context = {"symbols": payload.symbols or [], "key_news": [], "sources": []}
    output = generate_market_brief(context=context, as_of=as_of)
    existing = db.scalar(select(DailyBrief).where(DailyBrief.date == as_of))
    if existing is None:
        existing = DailyBrief(date=as_of, market_summary=output.summary)
        db.add(existing)
    existing.market_summary = output.summary
    existing.key_news = output.key_news
    existing.risk_flags = output.risk_flags
    db.commit()
    return output


@router.get("/briefs/daily/{brief_date}", response_model=MarketBriefOutput)
def get_daily_brief(brief_date: date, db: Session = Depends(get_db)) -> MarketBriefOutput:
    brief = db.scalar(select(DailyBrief).where(DailyBrief.date == brief_date))
    if brief is None:
        raise HTTPException(status_code=404, detail="Daily brief not found")
    return MarketBriefOutput(
        summary=brief.market_summary,
        key_news=brief.key_news,
        risk_flags=brief.risk_flags,
        sources=[],
    )


@router.post("/advice/generate", response_model=TradeRecommendationRead)
def create_trade_advice(payload: GenerateAdviceRequest, db: Session = Depends(get_db)) -> TradeRecommendation:
    symbol = payload.symbol.upper()
    asset = db.scalar(select(Asset).where(Asset.symbol == symbol))
    if asset is None:
        raise HTTPException(status_code=404, detail="Symbol not found")
    output = generate_trade_advice(symbol=symbol, context={"supporting_data": []}, as_of=payload.as_of)
    recommendation = TradeRecommendation(
        asset_id=asset.id,
        action=output.action,
        suggested_position_change=output.suggested_position_limit,
        rationale=output.rationale,
        risk_assessment="\n".join(output.risks),
        evidence=output.supporting_data,
        requires_human_confirmation=True,
        status=RecommendationStatus.REVIEW_REQUIRED,
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.get("/advice/{recommendation_id}", response_model=TradeRecommendationRead)
def get_trade_advice(recommendation_id: int, db: Session = Depends(get_db)) -> TradeRecommendation:
    recommendation = db.get(TradeRecommendation, recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return recommendation


@router.post("/advice/{recommendation_id}/approve", response_model=TradeRecommendationRead)
def approve_trade_advice(recommendation_id: int, db: Session = Depends(get_db)) -> TradeRecommendation:
    recommendation = db.get(TradeRecommendation, recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    recommendation.status = RecommendationStatus.APPROVED
    db.commit()
    db.refresh(recommendation)
    return recommendation


@router.post("/advice/{recommendation_id}/reject", response_model=TradeRecommendationRead)
def reject_trade_advice(recommendation_id: int, db: Session = Depends(get_db)) -> TradeRecommendation:
    recommendation = db.get(TradeRecommendation, recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    recommendation.status = RecommendationStatus.REJECTED
    db.commit()
    db.refresh(recommendation)
    return recommendation
