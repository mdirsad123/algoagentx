from app.services.funded_backtest.report_exports import build_funded_excel, build_funded_pdf


def _report():
    return {
        "status": "PAYOUT_READY",
        "initial_capital": "5000",
        "final_balance": "6058.7250000002197",
        "trading_days": 35,
        "qualifying_days": 19,
        "calendar_days": 45,
        "summary": {
            "return_pct": "0.211745",
            "max_drawdown_pct": "0.034",
            "source_strategy_name": "XAUUSD 5M Resistance Rejection V1",
            "engine_version": "2.0.4-trade-level",
            "drawdown_evaluation_mode": "TRADE_LEVEL",
            "payout": {
                "estimated_payout_amount": "952.85250000019773",
                "gross_eligible_profit": "1058.7250000002197",
                "consistency_pct": "0.21006996218887158",
                "profit_split_pct": "0.9",
            },
        },
        "account_snapshot": {"profile": {"name": "Instant Zero", "account_currency": "USD", "challenge_type": "INSTANT", "account_size": "5000"}},
    }


def test_funded_excel_export_is_valid_xlsx_container():
    payload = build_funded_excel(_report(), [], [], [], [])
    assert payload.startswith(b"PK")
    assert len(payload) > 1000


def test_funded_pdf_export_is_valid_pdf():
    payload = build_funded_pdf(_report(), [], [], [])
    assert payload.startswith(b"%PDF")
    assert len(payload) > 1000
