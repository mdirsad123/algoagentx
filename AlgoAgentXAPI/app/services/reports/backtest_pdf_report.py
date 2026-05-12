from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .report_formatters import (
    format_money,
    format_number,
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
NEUTRAL_BG = colors.HexColor("#FAFAFA")
GREEN_BG = colors.HexColor("#ECFDF5")
RED_BG = colors.HexColor("#FFF1F2")
BLUE_BG = colors.HexColor("#EFF6FF")


def _register_report_font() -> tuple[str, str]:
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
    account_currency = (
        summary.get("account_currency")
        or instrument_spec.get("account_currency")
        or (runtime_config.get("risk") or {}).get("account_currency")
        or first_trade.get("account_currency")
    )
    if not account_currency:
        if (instrument_symbol or "").upper() in {"XAUUSD", "BTCUSD", "ETHUSD"} or (asset_class or "").upper() in {"METAL", "FOREX", "CRYPTO"}:
            account_currency = "USD"
        else:
            account_currency = "INR"

    currency_symbol = summary.get("currency_symbol") or instrument_spec.get("currency_symbol") or first_trade.get("currency_symbol") or _currency_symbol_for_code(account_currency)
    quantity_mode = summary.get("quantity_mode") or instrument_spec.get("quantity_mode") or first_trade.get("quantity_mode")
    if not quantity_mode:
        quantity_mode = "LOTS" if (asset_class or "").upper() in {"METAL", "FOREX", "CRYPTO"} else "SHARES"

    summary.update(
        {
            "instrument_symbol": instrument_symbol,
            "asset_class": asset_class or "Legacy",
            "account_currency": account_currency,
            "currency_symbol": currency_symbol,
            "quantity_mode": quantity_mode,
            "instrument_spec_snapshot": instrument_spec,
            "runtime_config_snapshot": runtime_config,
        }
    )
    for trade in trades:
        trade.setdefault("account_currency", account_currency)
        trade.setdefault("currency_symbol", currency_symbol)
        trade.setdefault("quantity_mode", quantity_mode)
        trade.setdefault("asset_class", summary.get("asset_class"))
        trade.setdefault("instrument_spec_snapshot", instrument_spec)
        trade.setdefault("runtime_config_snapshot", runtime_config)
    return {"summary": summary, "trades": trades, "pnl_calendar": pnl_calendar, "equity_curve": equity_curve}


def _slug(text: Any) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", safe_text(text, "report").strip().lower()).strip("_")
    return value or "report"


def _escape(text: Any) -> str:
    return safe_text(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _p(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_escape(text), style)


def _money_color(value: Any):
    numeric = _as_float(value, 0.0) or 0.0
    return BRAND_GREEN if numeric > 0 else BRAND_RED if numeric < 0 else TEXT_DARK


def _safe_percent_value(value: Any) -> float | None:
    numeric = _as_float(value, None)
    if numeric is None:
        return None
    # Some legacy rows store 0.3504 for 35.04%; newer rows may store 35.04.
    if -1 <= numeric <= 1:
        return numeric * 100
    return numeric


def _format_percent_safe(value: Any, decimals: int = 2, fallback: str = "-") -> str:
    numeric = _safe_percent_value(value)
    if numeric is None:
        return fallback
    return f"{numeric:.{decimals}f}%"


def _build_table(data: list[list[Any]], col_widths: list[float] | None = None, header: bool = True, font_size: int = 8) -> Table:
    table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0, hAlign="LEFT")
    style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
            ("FONTSIZE", (0, 0), (-1, -1), font_size),
            ("TEXTCOLOR", (0, 0), (-1, -1), TEXT_DARK),
            ("GRID", (0, 0), (-1, -1), 0.25, BRAND_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )
    if header and data:
        style.add("BACKGROUND", (0, 0), (-1, 0), BRAND_PURPLE)
        style.add("TEXTCOLOR", (0, 0), (-1, 0), colors.white)
        style.add("FONTNAME", (0, 0), (-1, 0), FONT_BOLD)
    for idx in range(1 if header else 0, len(data)):
        if idx % 2 == 0:
            style.add("BACKGROUND", (0, idx), (-1, idx), NEUTRAL_BG)
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
    pdf_mode_label = safe_text(getattr(doc, "pdf_mode_label", "Executive"))
    canvas.drawString(doc.leftMargin, height - 19 * mm, f"Professional Backtest {pdf_mode_label} Report")
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
    canvas.drawCentredString(width / 2, 8 * mm, f"PDF mode: {pdf_mode_label}")
    canvas.drawRightString(width - doc.rightMargin, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _kpi_card(label: str, value: str, value_color=TEXT_DARK, width=45 * mm) -> Table:
    label_style = ParagraphStyle("KpiLabel", fontName=FONT_BOLD, fontSize=7, textColor=TEXT_MUTED, leading=9)
    value_style = ParagraphStyle("KpiValue", fontName=FONT_BOLD, fontSize=12, textColor=value_color, leading=14)
    table = Table([[_p(label, label_style)], [_p(value, value_style)]], colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_GRAY),
                ("BOX", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _section_title(text: str, styles) -> Paragraph:
    return Paragraph(_escape(text), styles["AXSection"])


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _exit_blob(trade: dict[str, Any]) -> str:
    return f"{safe_text(trade.get('exit_reason'), '')} {safe_text(trade.get('exit_type'), '')}".upper()


def _compute_trade_outcome(summary: dict[str, Any], trades: list[dict[str, Any]]) -> dict[str, Any]:
    pnls = [_as_float(t.get("pnl"), 0.0) or 0.0 for t in trades]
    r_values = [_as_float(t.get("r_multiple"), None) for t in trades]
    r_values = [v for v in r_values if v is not None]
    total = len(trades)

    computed = {
        "total_trades": total,
        "winning_trades_count": sum(1 for v in pnls if v > 0),
        "losing_trades_count": sum(1 for v in pnls if v < 0),
        "breakeven_trades_count": sum(1 for v in pnls if abs(v) < 0.000001),
        "tp_hit_count": sum(1 for t in trades if any(token in _exit_blob(t) for token in ("TAKE_PROFIT", "TARGET", "TP"))),
        "sl_hit_count": sum(1 for t in trades if any(token in _exit_blob(t) for token in ("STOP_LOSS", "STOPLOSS", "SL"))),
        "best_trade_pnl": max(pnls) if pnls else None,
        "worst_trade_pnl": min(pnls) if pnls else None,
        "avg_r_multiple": (sum(r_values) / len(r_values)) if r_values else None,
        "total_r_multiple": sum(r_values) if r_values else None,
        "best_r_multiple": max(r_values) if r_values else None,
        "worst_r_multiple": min(r_values) if r_values else None,
    }
    computed["other_exit_count"] = max(total - computed["tp_hit_count"] - computed["sl_hit_count"], 0)

    # Prefer backend summary values when they exist, but keep safe frontend/backend fallback.
    for key, value in list(computed.items()):
        computed[key] = _first_present(summary.get(key), value)
    return computed


def _day_key(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return text[:10] if len(text) >= 10 else text


def _daily_rows(pnl_calendar: list[dict[str, Any]], trades: list[dict[str, Any]], symbol: str, currency: str) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    trade_count: dict[str, int] = defaultdict(int)
    wins: dict[str, int] = defaultdict(int)
    losses: dict[str, int] = defaultdict(int)
    for trade in trades:
        key = _day_key(trade.get("exit_time") or trade.get("entry_time"))
        if not key:
            continue
        trade_count[key] += 1
        pnl = _as_float(trade.get("pnl"), 0.0) or 0.0
        if pnl > 0:
            wins[key] += 1
        elif pnl < 0:
            losses[key] += 1

    daily: list[dict[str, Any]] = []
    if pnl_calendar:
        for item in pnl_calendar:
            date_key = safe_text(item.get("date"))
            pnl = _as_float(item.get("pnl") if item.get("pnl") is not None else item.get("daily_pnl"), 0.0) or 0.0
            daily.append(
                {
                    "date": date_key,
                    "pnl": pnl,
                    "trades": trade_count.get(date_key, _as_float(item.get("trades") or item.get("trade_count"), 0) or 0),
                    "wins": wins.get(date_key, 0),
                    "losses": losses.get(date_key, 0),
                }
            )
    else:
        daily_pnl: dict[str, float] = defaultdict(float)
        for trade in trades:
            key = _day_key(trade.get("exit_time") or trade.get("entry_time"))
            if key:
                daily_pnl[key] += _as_float(trade.get("pnl"), 0.0) or 0.0
        for key in sorted(daily_pnl):
            daily.append({"date": key, "pnl": daily_pnl[key], "trades": trade_count.get(key, 0), "wins": wins.get(key, 0), "losses": losses.get(key, 0)})

    pnls = [d["pnl"] for d in daily]
    best = max(daily, key=lambda d: d["pnl"], default=None)
    worst = min(daily, key=lambda d: d["pnl"], default=None)
    stats = {
        "total_days": len(daily),
        "green_days": sum(1 for v in pnls if v > 0),
        "red_days": sum(1 for v in pnls if v < 0),
        "best_day": best,
        "worst_day": worst,
        "total_daily_pnl": sum(pnls),
    }

    monthly_map: dict[str, dict[str, Any]] = defaultdict(lambda: {"month": "", "days": 0, "green": 0, "red": 0, "net": 0.0, "best": None, "worst": None})
    for day in daily:
        month = safe_text(day.get("date"))[:7] or "Unknown"
        entry = monthly_map[month]
        entry["month"] = month
        entry["days"] += 1
        pnl = _as_float(day.get("pnl"), 0.0) or 0.0
        entry["net"] += pnl
        entry["green"] += 1 if pnl > 0 else 0
        entry["red"] += 1 if pnl < 0 else 0
        entry["best"] = pnl if entry["best"] is None else max(entry["best"], pnl)
        entry["worst"] = pnl if entry["worst"] is None else min(entry["worst"], pnl)
    monthly = [monthly_map[k] for k in sorted(monthly_map.keys())]
    return stats, daily, monthly


def _format_day(day: dict[str, Any] | None, symbol: str, currency: str) -> str:
    if not day:
        return "-"
    return f"{safe_text(day.get('date'))} ({format_money(day.get('pnl'), symbol, currency)})"


def _advanced_filter_text(summary: dict[str, Any], runtime_config: dict[str, Any]) -> list[list[str]]:
    filters = summary.get("advanced_filters") or summary.get("filter_summary")
    advanced = runtime_config.get("advanced_filters") if isinstance(runtime_config, dict) else None
    if not filters and isinstance(advanced, dict):
        filters = advanced
    if not filters:
        return [["Status", "Advanced filters were not used for this run."]]
    if isinstance(filters, str):
        return [["Summary", filters]]
    if not isinstance(filters, dict):
        return [["Summary", safe_text(filters)]]

    rows = []
    for label, keys in [
        ("Summary", ("summary", "label", "description")),
        ("Days", ("days", "day_filter", "allowed_days")),
        ("Session", ("session", "session_name")),
        ("Custom Time Window", ("custom_time_window", "time_window")),
        ("Timezone", ("timezone", "tz")),
        ("Candles Before", ("candles_before", "before_count")),
        ("Candles After", ("candles_after", "after_count")),
        ("Filter Reduction", ("filter_reduction_pct", "reduction_pct")),
    ]:
        value = None
        for key in keys:
            if key in filters:
                value = filters.get(key)
                break
        if value is None:
            continue
        if label == "Filter Reduction":
            value = _format_percent_safe(value)
        elif isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)[:500]
        rows.append([label, safe_text(value)])
    return rows or [["Summary", json.dumps(filters, ensure_ascii=False)[:900]]]


def _runtime_snapshot_rows(runtime_config: dict[str, Any], summary: dict[str, Any]) -> list[list[str]]:
    if not isinstance(runtime_config, dict) or not runtime_config:
        return [["Runtime Snapshot", "Runtime settings snapshot was not available for this older backtest."]]
    risk = runtime_config.get("risk") or {}
    sl_tp = runtime_config.get("sl_tp") or {}
    execution = runtime_config.get("execution") or {}
    trade_mgmt = runtime_config.get("trade_management") or {}
    strategy_params = runtime_config.get("strategy_params") or runtime_config.get("parameters") or {}
    rows = [
        ["Position Size Mode", safe_text(summary.get("position_size_mode") or risk.get("position_size_mode")), "Risk %", _format_percent_safe(summary.get("risk_percent") or risk.get("risk_percent"))],
        ["SL Mode", safe_text(summary.get("sl_mode") or sl_tp.get("sl_mode")), "RR Ratio", safe_text(summary.get("rr_ratio") or sl_tp.get("rr_ratio"))],
        ["Entry Mode", safe_text(execution.get("entry_mode")), "Exit on Opposite", "Yes" if execution.get("exit_on_opposite") else "No"],
        ["Break-even", "Yes" if trade_mgmt.get("break_even_enabled") else "No", "Trailing", "Yes" if trade_mgmt.get("trailing_enabled") else "No"],
        ["Strategy Parameters", json.dumps(strategy_params, ensure_ascii=False)[:700] if strategy_params else "-", "", ""],
    ]
    return rows


def _trade_sample_row(trade: dict[str, Any], label: str, q_mode: str, symbol: str, currency: str, price_precision: int) -> list[Any]:
    return [
        label,
        parse_datetime_label(trade.get("entry_time")),
        safe_text(trade.get("side")),
        format_trade_size(trade, q_mode),
        format_price(trade.get("entry_price"), price_precision),
        format_price(trade.get("exit_price"), price_precision),
        format_money(trade.get("pnl"), trade.get("currency_symbol") or symbol, trade.get("account_currency") or currency),
        format_number(trade.get("r_multiple")),
        safe_text(trade.get("exit_reason") or trade.get("exit_type")),
    ]



def _trade_row_tone(trade: dict[str, Any]):
    exit_blob = _exit_blob(trade)
    pnl = _as_float(trade.get("pnl"), 0.0) or 0.0
    if "TAKE_PROFIT" in exit_blob or "TARGET" in exit_blob or "TP" in exit_blob or pnl > 0:
        return GREEN_BG, BRAND_GREEN
    if "STOP_LOSS" in exit_blob or "STOPLOSS" in exit_blob or "SL" in exit_blob or pnl < 0:
        return RED_BG, BRAND_RED
    if abs(pnl) < 0.000001:
        return BRAND_GRAY, TEXT_DARK
    return BLUE_BG, TEXT_DARK


def _append_daily_monthly_pnl_summary(
    story: list[Any],
    styles,
    daily_stats: dict[str, Any],
    monthly: list[dict[str, Any]],
    symbol: str,
    currency: str,
) -> None:
    story.append(_section_title("Daily / Monthly PnL Summary", styles))
    daily_stat_rows = [
        ["Total Days", format_number(daily_stats.get("total_days"), 0), "Green Days", format_number(daily_stats.get("green_days"), 0), "Red Days", format_number(daily_stats.get("red_days"), 0)],
        ["Best Day", _format_day(daily_stats.get("best_day"), symbol, currency), "Worst Day", _format_day(daily_stats.get("worst_day"), symbol, currency), "Total Daily PnL", format_money(daily_stats.get("total_daily_pnl"), symbol, currency)],
    ]
    story.append(_build_table(daily_stat_rows, col_widths=[35 * mm, 45 * mm, 35 * mm, 60 * mm, 35 * mm, 50 * mm], header=False, font_size=8))
    story.append(Spacer(1, 3 * mm))

    if monthly:
        monthly_rows = [["Month", "Trading Days", "Green Days", "Red Days", "Net PnL", "Best Day", "Worst Day"]]
        for row in monthly[:36]:
            monthly_rows.append([
                safe_text(row.get("month")),
                format_number(row.get("days"), 0),
                format_number(row.get("green"), 0),
                format_number(row.get("red"), 0),
                format_money(row.get("net"), symbol, currency),
                format_money(row.get("best"), symbol, currency),
                format_money(row.get("worst"), symbol, currency),
            ])
        monthly_table = _build_table(monthly_rows, col_widths=[30 * mm, 30 * mm, 28 * mm, 28 * mm, 38 * mm, 38 * mm, 38 * mm], header=True, font_size=7)
        style = TableStyle([])
        for idx, row in enumerate(monthly[:36], start=1):
            bg = GREEN_BG if (_as_float(row.get("net"), 0) or 0) > 0 else RED_BG if (_as_float(row.get("net"), 0) or 0) < 0 else NEUTRAL_BG
            style.add("BACKGROUND", (0, idx), (-1, idx), bg)
        monthly_table.setStyle(style)
        story.append(monthly_table)
    else:
        story.append(Paragraph("Daily or monthly PnL data is not available for this run.", styles["AXMuted"]))


def _trade_audit_table(trades: list[dict[str, Any]], q_mode: str, symbol: str, currency: str, price_precision: int, styles) -> Table:
    signal_style = ParagraphStyle("AXTradeSignal", fontName=FONT_REGULAR, fontSize=5.2, leading=6.2, textColor=TEXT_DARK)
    cell_style = ParagraphStyle("AXTradeCell", fontName=FONT_REGULAR, fontSize=5.2, leading=6.2, textColor=TEXT_DARK)
    rows: list[list[Any]] = [["#", "Entry Time", "Exit Time", "Side", "Size / Lot / Qty", "Entry", "Exit", "SL", "TP", "PnL", "R", "Exit Reason", "Signal Reason"]]
    for idx, trade in enumerate(trades, start=1):
        rows.append([
            str(idx),
            parse_datetime_label(trade.get("entry_time")),
            parse_datetime_label(trade.get("exit_time")),
            safe_text(trade.get("side")),
            format_trade_size(trade, q_mode),
            format_price(trade.get("entry_price"), price_precision),
            format_price(trade.get("exit_price"), price_precision),
            format_price(trade.get("stop_loss"), price_precision),
            format_price(trade.get("target") or trade.get("take_profit"), price_precision),
            format_money(trade.get("pnl"), trade.get("currency_symbol") or symbol, trade.get("account_currency") or currency),
            format_number(trade.get("r_multiple")),
            Paragraph(_escape(trade.get("exit_reason") or trade.get("exit_type") or "-"), cell_style),
            Paragraph(_escape(trade.get("signal_reason") or "-"), signal_style),
        ])

    col_widths = [8 * mm, 25 * mm, 25 * mm, 12 * mm, 19 * mm, 17 * mm, 17 * mm, 17 * mm, 17 * mm, 23 * mm, 12 * mm, 28 * mm, 48 * mm]
    table = Table(rows, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    style = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
        ("FONTSIZE", (0, 0), (-1, -1), 5.2),
        ("FONTSIZE", (0, 0), (-1, 0), 5.5),
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_PURPLE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.2, BRAND_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ])
    for idx, trade in enumerate(trades, start=1):
        bg, accent = _trade_row_tone(trade)
        style.add("BACKGROUND", (0, idx), (-1, idx), bg)
        style.add("TEXTCOLOR", (9, idx), (9, idx), accent)
        style.add("TEXTCOLOR", (11, idx), (11, idx), accent)
    table.setStyle(style)
    return table


def build_backtest_pdf(detail: dict[str, Any], mode: str = "executive") -> tuple[BytesIO, str]:
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
    outcome = _compute_trade_outcome(summary, trades)
    gross_profit = _first_present(summary.get("gross_profit"), sum((_as_float(t.get("pnl"), 0.0) or 0.0) for t in trades if (_as_float(t.get("pnl"), 0.0) or 0.0) > 0))
    gross_loss = _first_present(summary.get("gross_loss"), sum((_as_float(t.get("pnl"), 0.0) or 0.0) for t in trades if (_as_float(t.get("pnl"), 0.0) or 0.0) < 0))
    daily_stats, _daily, monthly = _daily_rows(pnl_calendar, trades, symbol, currency)

    pdf_mode = "full_audit" if mode == "full_audit" else "executive"
    pdf_mode_label = "Full Audit" if pdf_mode == "full_audit" else "Executive"

    output = BytesIO()
    doc = BaseDocTemplate(
        output,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=26 * mm,
        bottomMargin=18 * mm,
        title=f"AlgoAgentX Backtest {pdf_mode_label} Report",
        author="AlgoAgentX",
    )
    doc.backtest_short = safe_text(summary.get("id"), "-")[:8]
    doc.pdf_mode_label = pdf_mode_label
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=_header_footer)])

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("AXTitle", fontName=FONT_BOLD, fontSize=22, leading=26, textColor=BRAND_PURPLE, spaceAfter=5))
    styles.add(ParagraphStyle("AXSubtitle", fontName=FONT_REGULAR, fontSize=10, leading=13, textColor=TEXT_MUTED, spaceAfter=8))
    styles.add(ParagraphStyle("AXSection", fontName=FONT_BOLD, fontSize=13, leading=16, textColor=BRAND_DARK, spaceBefore=7, spaceAfter=6))
    styles.add(ParagraphStyle("AXSmall", fontName=FONT_REGULAR, fontSize=7, leading=9, textColor=TEXT_DARK))
    styles.add(ParagraphStyle("AXSmallWhite", fontName=FONT_BOLD, fontSize=7, leading=9, textColor=colors.white))
    styles.add(ParagraphStyle("AXCell", fontName=FONT_REGULAR, fontSize=7, leading=9, textColor=TEXT_DARK))
    styles.add(ParagraphStyle("AXMuted", fontName=FONT_REGULAR, fontSize=8, leading=10, textColor=TEXT_MUTED))
    styles.add(ParagraphStyle("AXCenterMuted", parent=styles["AXMuted"], alignment=TA_CENTER))

    story: list[Any] = []
    story.append(Paragraph(f"AlgoAgentX Backtest {pdf_mode_label} Report", styles["AXTitle"]))
    subtitle = f"{safe_text(summary.get('strategy_name'))} • {safe_text(summary.get('instrument_symbol'))} • {safe_text(summary.get('timeframe'))} • {safe_text(summary.get('start_date'))} to {safe_text(summary.get('end_date'))}"
    story.append(Paragraph(subtitle, styles["AXSubtitle"]))
    intro = "Executive PDF summarizes the run for sharing. Full trade-by-trade audit data remains available in Excel and CSV exports." if pdf_mode == "executive" else "Full Audit PDF includes the complete trade list for manual verification of entry, exit, SL, TP, PnL, R, exit reason, and signal reason. For faster analysis of very large runs, use Excel."
    story.append(Paragraph(intro, styles["AXMuted"]))
    story.append(Spacer(1, 4 * mm))

    kpis = [
        _kpi_card("Net PnL", format_money(summary.get("net_profit"), symbol, currency), _money_color(summary.get("net_profit"))),
        _kpi_card("Return %", _format_percent_safe(summary.get("return_pct")), _money_color(_safe_percent_value(summary.get("return_pct")))),
        _kpi_card("Win Rate", _format_percent_safe(summary.get("win_rate"))),
        _kpi_card("Profit Factor", format_number(summary.get("profit_factor"))),
        _kpi_card("Max Drawdown", _format_percent_safe(summary.get("max_drawdown")), BRAND_RED),
        _kpi_card("Sharpe", format_number(summary.get("sharpe_ratio"))),
        _kpi_card("Total Trades", format_number(summary.get("total_trades") or len(trades), 0)),
        _kpi_card("Final Capital", format_money(summary.get("final_capital"), symbol, currency), _money_color(summary.get("final_capital"))),
    ]
    story.append(Table([kpis[:4], kpis[4:]], hAlign="LEFT", colWidths=[45 * mm] * 4, style=TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)])))
    story.append(Spacer(1, 4 * mm))

    story.append(_section_title("Run Summary", styles))
    meta_rows = [
        ["Backtest ID", safe_text(summary.get("id")), "Status", safe_text(summary.get("status"))],
        ["Strategy", safe_text(summary.get("strategy_name")), "Instrument", safe_text(summary.get("instrument_symbol"))],
        ["Asset Class", safe_text(summary.get("asset_class")), "Timeframe", safe_text(summary.get("timeframe"))],
        ["Date Range", f"{safe_text(summary.get('start_date'))} to {safe_text(summary.get('end_date'))}", "Created At", parse_datetime_label(summary.get("created_at"))],
        ["Account Currency", safe_text(currency), "Quantity Mode", safe_text(q_mode)],
    ]
    story.append(_build_table(meta_rows, col_widths=[35 * mm, 75 * mm, 35 * mm, 75 * mm], header=False, font_size=8))

    story.append(_section_title("Performance Breakdown", styles))
    if pdf_mode == "full_audit":
        # Compact the full-audit cover page so the section does not spill a single orphan row
        # onto page 2. Drawdown is already visible in the KPI strip.
        perf_rows = [
            ["Initial Capital", format_money(summary.get("initial_capital"), symbol, currency), "Final Capital", format_money(summary.get("final_capital"), symbol, currency), "Net PnL", format_money(summary.get("net_profit"), symbol, currency)],
            ["Gross Profit", format_money(gross_profit, symbol, currency), "Gross Loss", format_money(gross_loss, symbol, currency), "Profit Factor", format_number(summary.get("profit_factor"))],
            ["Expectancy", format_money(summary.get("expectancy"), symbol, currency), "Avg Win", format_money(summary.get("avg_win"), symbol, currency), "Avg Loss", format_money(summary.get("avg_loss"), symbol, currency)],
        ]
        story.append(_build_table(perf_rows, col_widths=[30 * mm, 43 * mm, 30 * mm, 43 * mm, 30 * mm, 43 * mm], header=False, font_size=8))
    else:
        perf_rows = [
            ["Initial Capital", format_money(summary.get("initial_capital"), symbol, currency), "Final Capital", format_money(summary.get("final_capital"), symbol, currency)],
            ["Gross Profit", format_money(gross_profit, symbol, currency), "Gross Loss", format_money(gross_loss, symbol, currency)],
            ["Net PnL", format_money(summary.get("net_profit"), symbol, currency), "Profit Factor", format_number(summary.get("profit_factor"))],
            ["Expectancy", format_money(summary.get("expectancy"), symbol, currency), "Avg Win", format_money(summary.get("avg_win"), symbol, currency)],
            ["Avg Loss", format_money(summary.get("avg_loss"), symbol, currency), "Drawdown", _format_percent_safe(summary.get("max_drawdown"))],
        ]
        story.append(_build_table(perf_rows, col_widths=[40 * mm, 70 * mm, 40 * mm, 70 * mm], header=False, font_size=8))

    if pdf_mode == "executive":
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 4 * mm))
    story.append(_section_title("Trade Outcome", styles))
    outcome_rows = [
        ["Total Trades", format_number(outcome.get("total_trades"), 0), "Winning Trades", format_number(outcome.get("winning_trades_count"), 0), "Losing Trades", format_number(outcome.get("losing_trades_count"), 0)],
        ["Breakeven Trades", format_number(outcome.get("breakeven_trades_count"), 0), "TP Hits", format_number(outcome.get("tp_hit_count"), 0), "SL Hits", format_number(outcome.get("sl_hit_count"), 0)],
        ["Other Exits", format_number(outcome.get("other_exit_count"), 0), "Best Trade", format_money(outcome.get("best_trade_pnl"), symbol, currency), "Worst Trade", format_money(outcome.get("worst_trade_pnl"), symbol, currency)],
        ["Avg R", format_number(outcome.get("avg_r_multiple")), "Best R", format_number(outcome.get("best_r_multiple")), "Worst R", format_number(outcome.get("worst_r_multiple"))],
    ]
    story.append(_build_table(outcome_rows, col_widths=[35 * mm, 45 * mm, 35 * mm, 45 * mm, 35 * mm, 45 * mm], header=False, font_size=8))

    story.append(_section_title("Runtime Settings Snapshot", styles))
    story.append(_build_table(_runtime_snapshot_rows(runtime_config, summary), col_widths=[38 * mm, 72 * mm, 38 * mm, 72 * mm], header=False, font_size=7))

    story.append(_section_title("Advanced Filters Summary", styles))
    story.append(_build_table(_advanced_filter_text(summary, runtime_config), col_widths=[55 * mm, 170 * mm], header=False, font_size=8))

    if pdf_mode == "executive":
        story.append(PageBreak())
        _append_daily_monthly_pnl_summary(story, styles, daily_stats, monthly, symbol, currency)
    else:
        story.append(Spacer(1, 4 * mm))
        _append_daily_monthly_pnl_summary(story, styles, daily_stats, monthly, symbol, currency)
        story.append(Spacer(1, 4 * mm))

    story.append(_section_title("Equity Summary", styles))
    equities = [_as_float(row.get("equity"), None) for row in equity_curve]
    equities = [v for v in equities if v is not None]
    equity_rows = [
        ["Starting Equity", format_money(equities[0] if equities else summary.get("initial_capital"), symbol, currency), "Ending Equity", format_money(equities[-1] if equities else summary.get("final_capital"), symbol, currency)],
        ["Highest Equity", format_money(max(equities) if equities else None, symbol, currency), "Lowest Equity", format_money(min(equities) if equities else None, symbol, currency)],
        ["Max Drawdown", _format_percent_safe(summary.get("max_drawdown")), "Equity Points", format_number(len(equities), 0)],
    ]
    story.append(_build_table(equity_rows, col_widths=[45 * mm, 70 * mm, 45 * mm, 70 * mm], header=False, font_size=8))

    if pdf_mode == "executive":
        story.append(PageBreak())
    else:
        story.append(Spacer(1, 4 * mm))
    story.append(_section_title("Best / Worst Trade Samples", styles))
    if trades:
        sorted_by_pnl = sorted(trades, key=lambda t: _as_float(t.get("pnl"), 0.0) or 0.0)
        worst_trade = sorted_by_pnl[0]
        best_trade = sorted_by_pnl[-1]
        sample_rows = [["Sample", "Entry Time", "Side", "Size", "Entry", "Exit", "PnL", "R", "Exit Reason"]]
        sample_rows.append(_trade_sample_row(best_trade, "Best Trade", q_mode, symbol, currency, price_precision))
        if worst_trade is not best_trade:
            sample_rows.append(_trade_sample_row(worst_trade, "Worst Trade", q_mode, symbol, currency, price_precision))
        story.append(_build_table(sample_rows, col_widths=[25 * mm, 35 * mm, 18 * mm, 18 * mm, 25 * mm, 25 * mm, 30 * mm, 18 * mm, 55 * mm], header=True, font_size=7))
    else:
        story.append(Paragraph("No trades are available for sample analysis.", styles["AXMuted"]))

    if pdf_mode == "full_audit":
        story.append(PageBreak())
        story.append(_section_title("Complete Trade List", styles))
        story.append(Paragraph("Verification columns include entry/exit, SL, TP, PnL, R, exit reason, and signal reason. Risk internals remain available in Excel for deeper analysis.", styles["AXMuted"]))
        story.append(Spacer(1, 2 * mm))
        if trades:
            story.append(_trade_audit_table(trades, q_mode, symbol, currency, price_precision, styles))
        else:
            story.append(Paragraph("No trades are available for this run.", styles["AXMuted"]))
    else:
        story.append(Spacer(1, 5 * mm))
        story.append(_section_title("Full Audit Data", styles))
        story.append(
            Paragraph(
                "This executive PDF intentionally excludes the complete trade list to keep the report short, readable, and shareable. Use Trades CSV or Export Excel for the full trade-by-trade audit log, risk details, signal reasons, daily PnL rows, and workbook analysis sheets.",
                styles["AXMuted"],
            )
        )

    doc.build(story)
    output.seek(0)
    suffix = "full_audit_report" if pdf_mode == "full_audit" else "executive_report"
    filename = f"backtest_report_{_slug(summary.get('strategy_name'))}_{_slug(summary.get('instrument_symbol'))}_{_slug(summary.get('timeframe'))}_{suffix}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    return output, filename
