from app.db.models import AssetType
from app.ingestion.market_ingestor import MarketIngestor


def test_get_or_create_asset_detects_supported_futures(db_session):
    ingestor = MarketIngestor(db_session)
    asset = ingestor._get_or_create_asset("GC")

    assert asset.symbol == "GC"
    assert asset.asset_type == AssetType.FUTURE
    assert asset.name == "Gold Futures"
