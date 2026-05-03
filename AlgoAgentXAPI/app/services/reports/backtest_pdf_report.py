from __future__ import annotations

import json
import re
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

from .report_formatters import (
    format_money,
    format_number,
    format_percent,
    format_price,
    format_trade_size,
    parse_datetime_label,
    safe_text,
)

BRAND_PURPLE = colors.HexColor("#4C1D95")
BRAND_DARK = colors.HexColor("#241047")
BRAND_ACCENT = colors.HexColor("#A855F7")
BRAND_GREEN = colors.HexColor("#047857")
BRAND_RED = colors.HexColor("#B91C1C")
BRAND_GRAY = colors.HexColor("#F3F4F6")
BRAND_BORDER = colors.HexColor("#DDD6FE")
TEXT_DARK = colors.HexColor("#111827")
TEXT_MUTED = colors.HexColor("#6B7280")


def _register_report_font() -> tuple[str, str]:
    # Try Unicode fonts first so INR symbol renders in PDF. Fall back to Helvetica.
    candidates = [
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("Arial", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("NirmalaUI", "C:/Windows/Fonts/Nirmala.ttf", "C:/Windows/Fonts/NirmalaB.ttf"),
    ]
    for name, regular, bold in candidates:
        try:
            if Path(regular).exists():
                pdfmetrics.registerFont(TTFont(name, regular))
                if Path(bold).exists():
                    pdfmetrics.registerFont(TTFont(f"{name}-Bold", bold))
                    return name, f"{name}-Bold"
                return name, name
        except Exception:
            continue
    return "Helvetica", "Helvetica-Bold"

FONT_REGULAR, FONT_BOLD = _register_report_font()


def _as_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _jsonish(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _currency_symbol_for_code(code: str | None) -> str:
    code = (code or "").upper()
    if code == "USD":
        return "$"
    if code == "INR":
        return "₹"
    return code or "-"


def _normalise_report_data(detail: dict[str, Any]) -> dict[str, Any]:
    summary = dict(detail.get("summary") or {})
    trades = [dict(t or {}) for t in (detail.get("trades") or [])]
    pnl_calendar = [dict(p or {}) for p in (detail.get("pnl_calendar") or [])]
    equity_curve = [dict(e or {}) for e in (detail.get("equity_curve") or [])]

    # Pull snapshots from summary or first trade.
    first_trade = trades[0] if trades else {}
    instrument_spec = _jsonish(summary.get("instrument_spec_snapshot"))
    if not isinstance(instrument_spec, dict):
        instrument_spec = _jsonish(first_trade.get("instrument_spec_snapshot"))
    if not isinstance(instrument_spec, dict):
        instrument_spec = {}
    runtime_config = _jsonish(summary.get("runtime_config_snapshot"))
    if not isinstance(runtime_config, dict):
        runtime_config = _jsonish(first_trade.get("runtime_config_snapshot"))
    if not isinstance(runtime_config, dict):
        runtime_config = {}

    instrument_symbol = summary.get("instrument_symbol") or instrument_spec.get("symbol") or first_trade.get("instrument")
    asset_class = summary.get("asset_class") or instrument_spec.get("asset_class") or first_trade.get("asset_class")
    account_currency = summary.get("account_currency") or instrument_spec.get("account_currency") or (runtime_config.get("risk") or {}).get("account_currency") or first_trade.get("account_currency")
    if not account_currency:
        if (instrument_symbol or "").upper() in {"XAUUSD", "BTCUSD", "ETHUSD"} or (asset_class or "").upper() in {"METAL", "FOREX", "CRYPTO"}:
            account_currency = "USD"
        else:
            account_currency = "INR"
    currency_symbol = summary.get("currency_symbol") or instrument_spec.get("currency_symbol") or first_trade.get("currency_symbol") or _currency_symbol_for_code(account_currency)
    quantity_mode = summary.get("quantity_mode") or instrument_spec.get("quantity_mode") or first_trade.get("quantity_mode")
    if not quantity_mode:
        if (asset_class or "").upper() in {"METAL", "FOREX", "CRYPTO"}:
            quantity_mode = "LOTS"
        elif (asset_class or "").upper() in {"INDIAN_EQUITY"}:
            quantity_mode = "SHARES"
        else:
            quantity_mode = "SHARES"

    summary.update({
        "instrument_symbol": instrument_symbol,
        "asset_class": asset_class or "Legacy",
        "account_currency": account_currency,
        "currency_symbol": currency_symbol,
        "quantity_mode": quantity_mode,
        "instrument_spec_snapshot": instrument_spec,
        "runtime_config_snapshot": runtime_config,
    })
    for trade in trades:
        trade.setdefault("account_currency", account_currency)
        trade.setdefault("currency_symbol", currency_symbol)
        trade.setdefault("quantity_mode", quantity_mode)
        trade.setdefault("asset_class", summary.get("asset_class"))
        if trade.get("instrument_spec_snapshot") is None:
            trade["instrument_spec_snapshot"] = instrument_spec
        if trade.get("runtime_config_snapshot") is None:
            trade["runtime_config_snapshot"] = runtime_config
    return {"summary": summary, "trades": trades, "pnl_calendar": pnl_calendar, "equity_curve": equity_curve}


def _slug(text: Any) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", safe_text(text, "report").strip().lower()).strip("_")
    return value or "report"


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    # Keep table cells safe and readable.
    return Paragraph(safe_text(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), style)


def _money_color(value: Any):
    numeric = _as_float(value, 0.0) or 0.0
    return BRAND_GREEN if numeric > 0 else BRAND_RED if numeric < 0 else TEXT_DARK


def _build_table(data: list[list[Any]], col_widths: list[float] | None = None, header: bool = True, font_size: int = 8) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_DARK),
        ("GRID", (0, 0), (-1, -1), 0.25, BRAND_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ])
    if header and data:
        style.add("BACKGROUND", (0, 0), (-1, 0), BRAND_PURPLE)
        style.add("TEXTCOLOR", (0, 0), (-1, 0), colors.white)
        style.add("FONTNAME", (0, 0), (-1, 0), FONT_BOLD)
    for idx in range(1 if header else 0, len(data)):
        if idx % 2 == 0:
            style.add("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#FAFAFA"))
    table.setStyle(style)
    return table


def _header_footer(canvas, doc):
    canvas.saveState()
    width, height = doc.pagesize
    canvas.setFont(FONT_BOLD, 11)
    canvas.setFillColor(BRAND_PURPLE)
    canvas.drawString(doc.leftMargin, height - 14 * mm, "AlgoAgentX")
    canvas.setFont(FONT_REGULAR, 8)
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawString(doc.leftMargin, height - 19 * mm, "Trading Workspace")
    canvas.setFillColor(TEXT_MUTED)
    canvas.drawRightString(width - doc.rightMargin, height - 14 * mm, f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    canvas.setStrokeColor(BRAND_ACCENT)
    canvas.setLineWidth(1.2)
    canvas.line(doc.leftMargin, height - 22 * mm, width - doc.rightMargin, height - 22 * mm)
    canvas.setStrokeColor(BRAND_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 14 * mm, width - doc.rightMargin, 14 * mm)
    canvas.setFont(FONT_REGULAR, 7)
    canvas.setFillColor(TEXT_MUTED)
    backtest_short = safe_text(getattr(doc, "backtest_short", "-"))
    canvas.drawString(doc.leftMargin, 8 * mm, f"AlgoAgentX | Backtest {backtest_short}")
    canvas.drawCentredString(width / 2, 8 * mm, "Generated by AlgoAgentX Trading Workspace")
    canvas.drawRightString(width - doc.rightMargin, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _kpi_card(label: str, value: str, value_color=TEXT_DARK, width=45 * mm) -> Table:
    label_style = ParagraphStyle("KpiLabel", fontName=FONT_BOLD, fontSize=7, textColor=TEXT_MUTED, leading=9)
    value_style = ParagraphStyle("KpiValue", fontName=FONT_BOLD, fontSize=12, textColor=value_color, leading=14)
    table = Table([[_p(label, label_style)], [_p(value, value_style)]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_GRAY),
        ("BOX", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def build_backtest_pdf(detail: dict[str, Any]) -> tuple[BytesIO, str]:
    data = _normalise_report_data(detail)
    summary = data["summary"]
    trades = data["trades"]
    pnl_calendar = data["pnl_calendar"]
    equity_curve = data["equity_curve"]
    runtime_config = summary.get("runtime_config_snapshot") or {}
    instrument_spec = summary.get("instrument_spec_snapshot") or {}

    symbol = summary.get("currency_symbol") or "$"
    currency = summary.get("account_currency") or "USD"
    q_mode = (summary.get("quantity_mode") or "SHARES").upper()
    price_precision = int(instrument_spec.get("price_precision") or 2) if isinstance(instrument_spec, dict) else 2
    risk_cfg = runtime_config.get("risk") if isinstance(runtime_config, dict) else {}
    sl_cfg = runtime_config.get("sl_tp") if isinstance(runtime_config, dict) else {}
    exec_cfg = runtime_config.get("execution") if isinstance(runtime_config, dict) else {}
    tm_cfg = runtime_config.get("trade_management") if isinstance(runtime_config, dict) else {}

    output = BytesIO()
    doc = BaseDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=26 * mm,
        bottomMargin=18 * mm,
        title="AlgoAgentX Backtest Report",
        author="AlgoAgentX",
    )
    doc.backtest_short = safe_text(summary.get("id"), "-")[:8]
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=_header_footer)])

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("AXTitle", fontName=FONT_BOLD, fontSize=21, leading=25, textColor=BRAND_PURPLE, spaceAfter=5))
    styles.add(ParagraphStyle("AXSubtitle", fontName=FONT_REGULAR, fontSize=10, leading=13, textColor=TEXT_MUTED, spaceAfter=9))
    styles.add(ParagraphStyle("AXSection", fontName=FONT_BOLD, fontSize=13, leading=16, textColor=BRAND_DARK, spaceBefore=8, spaceAfter=6))
    styles.add(ParagraphStyle("AXSmall", fontName=FONT_REGULAR, fontSize=7, leading=9, textColor=TEXT_DARK))
    styles.add(ParagraphStyle("AXSmallWhite", fontName=FONT_BOLD, fontSize=7, leading=9, textColor=colors.white))
    styles.add(ParagraphStyle("AXCell", fontName=FONT_REGULAR, fontSize=7, leading=9, textColor=TEXT_DARK))
    styles.add(ParagraphStyle("AXMuted", fontName=FONT_REGULAR, fontSize=8, leading=10, textColor=TEXT_MUTED))

    story = []
    story.append(Paragraph("AlgoAgentX Backtest Report", styles["AXTitle"]))
    subtitle = f"{safe_text(summary.get('strategy_name'))} • {safe_text(summary.get('instrument_symbol'))} • {safe_text(summary.get('timeframe'))} • {safe_text(summary.get('start_date'))} to {safe_text(summary.get('end_date'))}"
    story.append(Paragraph(subtitle, styles["AXSubtitle"]))
    story.append(Paragraph(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles["AXMuted"]))
    story.append(Spacer(1, 5 * mm))

    kpis = [
        _kpi_card("Net PnL", format_money(summary.get("net_profit"), symbol, currency), _money_color(summary.get("net_profit"))),
        _kpi_card("Return %", format_percent(summary.get("return_pct")), _money_color(summary.get("return_pct"))),
        _kpi_card("Win Rate", format_percent(summary.get("win_rate"))),
        _kpi_card("Profit Factor", format_number(summary.get("profit_factor"))),
        _kpi_card("Max Drawdown", format_percent(summary.get("max_drawdown")), BRAND_RED),
        _kpi_card("Sharpe", format_number(summary.get("sharpe_ratio"))),
        _kpi_card("Total Trades", format_number(summary.get("total_trades"), 0)),
        _kpi_card("Final Capital", format_money(summary.get("final_capital"), symbol, currency), _money_color(summary.get("final_capital"))),
    ]
    story.append(Table([kpis[:4], kpis[4:]], hAlign="LEFT", colWidths=[45 * mm] * 4, style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)])))
    story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("Run Metadata", styles["AXSection"]))
    meta_rows = [
        ["Backtest ID", safe_text(summary.get("id")), "Strategy", safe_text(summary.get("strategy_name"))],
        ["Instrument", safe_text(summary.get("instrument_symbol")), "Asset Class", safe_text(summary.get("asset_class"))],
        ["Timeframe", safe_text(summary.get("timeframe")), "Account Currency", safe_text(currency)],
        ["Quantity Mode", safe_text(q_mode), "Initial Capital", format_money(summary.get("initial_capital"), symbol, currency)],
        ["Final Capital", format_money(summary.get("final_capital"), symbol, currency), "Created At", parse_datetime_label(summary.get("created_at"))],
    ]
    story.append(_build_table(meta_rows, col_widths=[35 * mm, 75 * mm, 35 * mm, 75 * mm], header=False, font_size=8))

    story.append(Paragraph("Risk & Runtime Settings", styles["AXSection"]))
    avg_size_label = "Avg Lot Size" if q_mode == "LOTS" else "Avg Quantity"
    avg_size_value = format_number(summary.get("avg_lot_size"), 2) if q_mode == "LOTS" else format_number(summary.get("avg_quantity"), 2)
    risk_rows = [
        ["Position Size Mode", safe_text(summary.get("position_size_mode") or risk_cfg.get("position_size_mode")), "Risk %", format_percent((_as_float(summary.get("risk_percent"), None) or _as_float(risk_cfg.get("risk_percent"), 0) or 0) * 100 if (_as_float(summary.get("risk_percent"), None) or _as_float(risk_cfg.get("risk_percent"), 0) or 0) <= 1 else (_as_float(summary.get("risk_percent"), 0) or 0))],
        ["SL Mode", safe_text(summary.get("sl_mode") or sl_cfg.get("sl_mode")), "RR Ratio", format_number(summary.get("rr_ratio") or sl_cfg.get("rr_ratio"))],
        ["ATR Period", safe_text(sl_cfg.get("atr_period")), "ATR Multiplier", safe_text(sl_cfg.get("atr_multiplier"))],
        ["Swing Lookback", safe_text(sl_cfg.get("swing_lookback")), "Break-even Enabled", "Yes" if tm_cfg.get("break_even_enabled") else "No"],
        ["Trailing Enabled", "Yes" if tm_cfg.get("trailing_enabled") else "No", "Trailing Mode", safe_text(tm_cfg.get("trailing_mode"))],
        ["Avg Actual Risk", format_money(summary.get("avg_actual_risk"), symbol, currency), avg_size_label, avg_size_value],
    ]
    story.append(_build_table(risk_rows, col_widths=[40 * mm, 70 * mm, 40 * mm, 70 * mm], header=False, font_size=8))

    story.append(Paragraph("Capital & Trade Quality", styles["AXSection"]))
    gross_profit = summary.get("gross_profit")
    gross_loss = summary.get("gross_loss")
    if gross_profit is None or gross_loss is None:
        pnls = [_as_float(t.get("pnl"), 0) or 0 for t in trades]
        gross_profit = sum(v for v in pnls if v > 0)
        gross_loss = sum(v for v in pnls if v < 0)
    quality_rows = [
        ["Avg Win", format_money(summary.get("avg_win"), symbol, currency), "Avg Loss", format_money(summary.get("avg_loss"), symbol, currency)],
        ["Expectancy", format_money(summary.get("expectancy"), symbol, currency), "Profit Factor", format_number(summary.get("profit_factor"))],
        ["Gross Profit", format_money(gross_profit, symbol, currency), "Gross Loss", format_money(gross_loss, symbol, currency)],
        ["Total Trades", format_number(summary.get("total_trades"), 0), "Win Rate", format_percent(summary.get("win_rate"))],
        ["Max Drawdown", format_percent(summary.get("max_drawdown")), "Sharpe", format_number(summary.get("sharpe_ratio"))],
    ]
    story.append(_build_table(quality_rows, col_widths=[40 * mm, 70 * mm, 40 * mm, 70 * mm], header=False, font_size=8))

    story.append(Paragraph("Advanced Filters Used", styles["AXSection"]))
    filters = summary.get("advanced_filters") or summary.get("filter_summary")
    if filters:
        if isinstance(filters, str):
            filters_text = filters
        else:
            filters_text = json.dumps(filters, indent=2)[:1200]
        story.append(Paragraph(filters_text.replace("\n", "<br/>"), styles["AXCell"]))
    else:
        story.append(Paragraph("Advanced filters were not used for this run.", styles["AXMuted"]))

    story.append(PageBreak())
    story.append(Paragraph("Trade List", styles["AXSection"]))
    if not trades:
        story.append(Paragraph("No trades available for this run.", styles["AXMuted"]))
    else:
        size_header = "Lot" if q_mode == "LOTS" else "Qty" if q_mode == "SHARES" else "Size"
        headers = ["#", "Entry Time", "Exit Time", "Side", size_header, "Entry", "Exit", "SL", "TP", "Risk", "Actual Risk", "PnL", "R", "Exit Type"]
        rows = [[_p(h, styles["AXSmallWhite"]) for h in headers]]
        for idx, trade in enumerate(trades, start=1):
            trade_symbol = trade.get("currency_symbol") or symbol
            trade_currency = trade.get("account_currency") or currency
            row = [
                str(idx),
                parse_datetime_label(trade.get("entry_time")),
                parse_datetime_label(trade.get("exit_time")),
                safe_text(trade.get("side")),
                format_trade_size(trade, q_mode),
                format_price(trade.get("entry_price"), price_precision),
                format_price(trade.get("exit_price"), price_precision),
                format_price(trade.get("stop_loss"), price_precision),
                format_price(trade.get("target"), price_precision),
                format_money(trade.get("risk_amount"), trade_symbol, trade_currency),
                format_money(trade.get("actual_risk_amount"), trade_symbol, trade_currency),
                format_money(trade.get("pnl"), trade_symbol, trade_currency),
                format_number(trade.get("r_multiple")),
                safe_text(trade.get("exit_reason") or trade.get("exit_type")),
            ]
            rows.append([_p(v, styles["AXCell"]) for v in row])
        col_widths = [8*mm, 25*mm, 25*mm, 13*mm, 14*mm, 17*mm, 17*mm, 17*mm, 17*mm, 21*mm, 23*mm, 21*mm, 11*mm, 28*mm]
        trade_table = _build_table(rows, col_widths=col_widths, header=True, font_size=6)
        # Color PnL and R columns.
        style = TableStyle([])
        for row_idx, trade in enumerate(trades, start=1):
            pnl_color = _money_color(trade.get("pnl"))
            r_color = _money_color(trade.get("r_multiple"))
            style.add("TEXTCOLOR", (11, row_idx), (11, row_idx), pnl_color)
            style.add("TEXTCOLOR", (12, row_idx), (12, row_idx), r_color)
        trade_table.setStyle(style)
        story.append(trade_table)

    story.append(PageBreak())
    story.append(Paragraph("PnL Calendar / Daily Summary", styles["AXSection"]))
    if pnl_calendar:
        pnl_rows = [["Date", "Trades", "Net PnL", "Result"]]
        for row in pnl_calendar[:500]:
            pnl_value = row.get("pnl") or row.get("daily_pnl")
            pnl_numeric = _as_float(pnl_value, 0) or 0
            pnl_rows.append([
                safe_text(row.get("date")),
                safe_text(row.get("trades") or row.get("trade_count") or "-"),
                format_money(pnl_value, symbol, currency),
                "Profit" if pnl_numeric > 0 else "Loss" if pnl_numeric < 0 else "Flat",
            ])
        story.append(_build_table(pnl_rows, col_widths=[40*mm, 25*mm, 45*mm, 35*mm], header=True, font_size=8))
    else:
        story.append(Paragraph("Daily PnL data is not available for this run.", styles["AXMuted"]))

    story.append(Paragraph("Equity Summary", styles["AXSection"]))
    equities = [_as_float(row.get("equity"), None) for row in equity_curve]
    equities = [v for v in equities if v is not None]
    equity_rows = [
        ["Starting Equity", format_money(equities[0] if equities else summary.get("initial_capital"), symbol, currency), "Ending Equity", format_money(equities[-1] if equities else summary.get("final_capital"), symbol, currency)],
        ["Highest Equity", format_money(max(equities) if equities else None, symbol, currency), "Lowest Equity", format_money(min(equities) if equities else None, symbol, currency)],
        ["Max Drawdown", format_percent(summary.get("max_drawdown")), "Total Equity Points", format_number(len(equities), 0)],
    ]
    story.append(_build_table(equity_rows, col_widths=[45 * mm, 70 * mm, 45 * mm, 70 * mm], header=False, font_size=8))

    doc.build(story)
    output.seek(0)
    filename = f"backtest_report_{_slug(summary.get('strategy_name'))}_{_slug(summary.get('instrument_symbol'))}_{_slug(summary.get('timeframe'))}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    return output, filename
