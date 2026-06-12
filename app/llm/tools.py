READ_ONLY_TOOLS = [
    {
        "name": "get_asset_price_history",
        "description": "Read verified daily OHLCV price history for a symbol. Call this when price evidence is needed.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
    {
        "name": "run_risk_check",
        "description": "Run deterministic risk checks before presenting any trade suggestion.",
        "input_schema": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"],
            "additionalProperties": False,
        },
    },
]
