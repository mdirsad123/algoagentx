"""Source-pinned NAS100 V4.8 closed-right-edge adapter; never order approval.

The frozen source deliberately excludes the right edge from V1.5/V1.7/V1.8,
V2.0/V2.4/V2.6/V2.7/V2.9/V3.1/V3.7/V4.2 additions and V4.3--V4.8
filters. Do NOT append a fictional next bar to activate those overlays.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from functools import lru_cache
from hashlib import sha256
import json
import math

import numpy as np
import pandas as pd

from app.services.live.universal_incremental import make_incremental_strategy_class

SOURCE_SHA256 = "0a7f49b19aa413affbe036d8e12b8c57c22eaf19c16d04e6a179a86d6c7b5b5b"
# Exact, source-pinned variant exported from this user's NAS100 V4.8 DB.
# It is the byte-identical frozen V4.8 strategy PLUS a research-only streaming
# candidate appendix. Only this immutable hash is trusted; never infer adapter
# authorization from symbol, name, an arbitrary environment SHA, or a prefix alone.
DEPLOYED_APPEND_ONLY_SHA256 = "2fc05d1d6116194a5e18b5148ba08bc62dcb0d0556d00e59d664899861bf7434"
COLS = ("Open", "High", "Low", "Close", "Volume")

def source_digest(source):
    return sha256((source.replace("\r\n", "\n").rstrip() + "\n").encode()).hexdigest()


# Compare parsed Python *logic*, not arbitrary editable labels or a manually
# supplied .env hash. Python comments, indentation and line endings do not
# affect executable AST. Literal values, function bodies, imports, assignments,
# class definitions and decorators MUST still be structurally identical.
# The frozen source is bundled inside /app/strategies so Docker can audit it.
from functools import lru_cache as _cache_source_match
import ast as _ast
from pathlib import Path as _Path

_FROZEN_SOURCE_PATH = (_Path(__file__).resolve().parent / "frozen_sources" /
                       "NAS100_M5_V4_8_ALGOAGENTX_STANDALONE_FILTER_ONLY_RESEARCH_ONLY.py")


@_cache_source_match(maxsize=1)
def _frozen_source():
    reference = _FROZEN_SOURCE_PATH.read_text(encoding="utf-8")
    if source_digest(reference) != SOURCE_SHA256:
        raise RuntimeError("Bundled NAS100 V4.8 source integrity mismatch")
    return reference


@_cache_source_match(maxsize=1)
def _frozen_ast():
    reference = _frozen_source()
    if source_digest(reference) != SOURCE_SHA256:
        raise RuntimeError("Bundled NAS100 V4.8 source integrity mismatch")
    return _ast.dump(_ast.parse(reference), include_attributes=False)


@_cache_source_match(maxsize=16)
def source_match_kind(source: str) -> str:
    """exact_sha, same_ast (formatting-only), or different_logic_or_syntax.

    This does NOT prove feed/broker parity. Never accept a title, symbol, or
    arbitrary SHA as proof of source equivalence.
    """
    if not source:
        return "different_logic_or_syntax"
    if source_digest(source) == SOURCE_SHA256:
        return "exact_sha"
    # Recognize ONLY the exact, previously audited DB appendix. Its first
    # 3813 lines are byte-identical to the bundled frozen V4.8 reference.
    # An arbitrary extension, changed indicator, or a new version fails closed.
    if (sha256(source.encode("utf-8")).hexdigest() == DEPLOYED_APPEND_ONLY_SHA256
            and source.startswith(_frozen_source())):
        return "pinned_append_only_db_variant"
    try:
        return ("same_ast" if _ast.dump(_ast.parse(source), include_attributes=False)
                == _frozen_ast() else "different_logic_or_syntax")
    except (SyntaxError, ValueError, TypeError, RecursionError, UnicodeError):
        return "different_logic_or_syntax"


def source_matches_frozen(source: str) -> bool:
    return source_match_kind(source) in {"exact_sha", "same_ast", "pinned_append_only_db_variant"}

def _bar(bar):
    t = pd.Timestamp(bar.get("Date", bar.get("timestamp")))
    if pd.isna(t):
        raise ValueError("Missing candle time")
    t = t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")
    if t.value % (300 * 10**9):
        raise ValueError("M5 alignment required")
    b = {
        "Date": t.isoformat(),
        **{k: float(bar[k] if k in bar else bar[k.lower()]) for k in COLS},
    }
    if not all(math.isfinite(b[k]) for k in COLS):
        raise ValueError("Nonfinite OHLCV")
    if b["High"] < max(b["Open"], b["Close"], b["Low"]) or b["Low"] > min(
        b["Open"], b["Close"]
    ):
        raise ValueError("Invalid OHLC")
    return b

def _ewm(state, key, value, alpha):
    old = state.get(key)
    # Match pandas adjust=False arithmetic, including its constant-value branch.
    state[key] = (
        value
        if old is None
        else old
        if old == value
        else (1 - alpha) * old + alpha * value
    )
    return state[key]

def _hit(groups, values, single=False):
    for group in groups:
        hits = []
        for key, op, bound in group:
            value = values[key]
            if single:
                value, bound = np.float32(value), np.float32(bound)
            if op not in ("<=", ">="):
                raise ValueError("Unsupported frozen comparison")
            hits.append(
                np.isfinite(value)
                and (value <= bound if op == "<=" else value >= bound)
            )
        if all(hits):
            return True
    return False

class _Stream:
    def __init__(self):
        self.s = dict(
            count=0,
            bars=[],
            indicators={},
            trail=[],
            htf={},
            last_base=-100000,
            ny={},
            utc={},
            week={},
            last_output=None,
        )

    def advance(self, b):
        s = self.s
        t = pd.Timestamp(b["Date"])
        ny = t.tz_convert("America/New_York")
        minute = ny.hour * 60 + ny.minute
        o, h, l, c, v = (b[k] for k in COLS)  # noqa: E741 -- frozen OHLC notation
        bars, e, trail = s["bars"], s["indicators"], s["trail"]
        pc = bars[-1]["Close"] if bars else c
        ph, pl = (bars[-1]["High"], bars[-1]["Low"]) if bars else (h, l)
        tr = max(h - l, abs(h - pc), abs(l - pc))
        a = _ewm(e, "atr", tr, 1 / 14)
        for span in (12, 20, 26, 50, 100):
            _ewm(e, "e" + str(span), c, 2 / (span + 1))
        macd = e["e12"] - e["e26"]
        macdh = macd - _ewm(e, "macds", macd, 2 / 10)
        gain = _ewm(e, "gain", max(c - pc, 0), 1 / 14)
        loss = _ewm(e, "loss", max(pc - c, 0), 1 / 14)
        plus, minus = max(h - ph, 0), max(pl - l, 0)
        dp, dm = (plus if plus > minus else 0), (minus if minus > plus else 0)
        sp = _ewm(e, "plus", dp, 1 / 14) / max(a, 1e-9)
        sn = _ewm(e, "minus", dm, 1 / 14) / max(a, 1e-9)
        adx = _ewm(e, "adx", 100 * abs(sp - sn) / max(sp + sn, 1e-9), 1 / 14)
        # _v27_bank updates dmp before comparing dmm: preserve that asymmetry.
        sn27 = _ewm(e, "minus27", minus if minus > dp else 0, 1 / 14) / max(a, 1e-9)
        adx27 = _ewm(e, "adx27", 100 * abs(sp - sn27) / max(sp + sn27, 1e-9), 1 / 14)
        span = max(h - l, 1e-9)
        f = dict(
            o=o,
            h=h,
            l=l,
            c=c,
            pc=pc,
            a=max(a, 1e-8),
            atr=a,
            body=abs(c - o) / max(a, 1e-8),
            q=(c - l) / max(h - l, 1e-8),
            bearq=(h - c) / max(h - l, 1e-8),
            macdh=macdh,
            adx=adx27,
            rsi=100 * gain / max(gain + loss, 1e-8),
            minute=minute,
            dow=ny.dayofweek,
        )
        f.update({k: e[k] for k in ("e20", "e50", "e100")})
        for n in (8, 12, 24, 48, 96):
            f["hi" + str(n)] = (
                max(x["High"] for x in bars[-n:]) if len(bars) >= n else np.nan
            )
            f["lo" + str(n)] = (
                min(x["Low"] for x in bars[-n:]) if len(bars) >= n else np.nan
            )
        closes = [x["Close"] for x in bars[-20:]]
        current20 = (closes + [c])[-20:]
        f["bb"], f["bs"] = np.mean(current20), np.std(current20)
        low14 = min([x["Low"] for x in bars[-13:]] + [l])
        high14 = max([x["High"] for x in bars[-13:]] + [h])
        f["k"] = 100 * (c - low14) / max(high14 - low14, 1e-9)
        f["ks"] = np.mean([x["k"] for x in trail[-2:]] + [f["k"]])
        volumes = [x["Volume"] for x in bars]
        f["rv"] = v / max(np.mean(volumes[-24:]), 1) if volumes else np.nan
        f["ar"] = (
            a / max(np.median([x["atr"] for x in trail[-200:]]), 1e-9)
            if trail
            else np.nan
        )
        atrrel = (
            a / max(np.median([x["atr"] for x in trail[-288:]]), 1e-8)
            if trail
            else np.nan
        )
        for name, key in (
            ("ny", str(ny.date())),
            ("utc", str(t.date())),
            ("week", str(ny.date() - timedelta(days=ny.dayofweek))),
        ):
            g = s[name]
            if g.get("key") != key:
                g = s[name] = dict(
                    key=key,
                    hi=h,
                    lo=l,
                    op=o,
                    prev_hi=g.get("hi"),
                    prev_lo=g.get("lo"),
                    orb_hi=None,
                    orb_lo=None,
                    orb_n=0,
                )
            g["hi"], g["lo"] = max(g["hi"], h), min(g["lo"], l)
        day = s["ny"]
        if 570 <= minute < 600:
            day["orb_hi"] = h if day["orb_hi"] is None else max(day["orb_hi"], h)
            day["orb_lo"] = l if day["orb_lo"] is None else min(day["orb_lo"], l)
            day["orb_n"] += 1
        # pandas groupby.cumsum uses compensated summation.
        for key, value in (
            ("vol", v),
            ("pv", v * (h + l + c) / 3),
            ("vol27", v if minute >= 570 else 0),
            ("pv27", (h + l + c) / 3 * (v if minute >= 570 else 0)),
        ):
            y = value - day.get(key + "_comp", 0)
            total = day.get(key, 0) + y
            day[key + "_comp"] = (total - day.get(key, 0)) - y
            day[key] = total
        f.update(
            dh=day["prev_hi"] if day["prev_hi"] is not None else np.nan,
            dl=day["prev_lo"] if day["prev_lo"] is not None else np.nan,
            wh=s["week"]["prev_hi"] if s["week"]["prev_hi"] is not None else np.nan,
            wl=s["week"]["prev_lo"] if s["week"]["prev_lo"] is not None else np.nan,
            dopen=day["op"],
            vw=day["pv27"] / max(day["vol27"], 1e-9) if minute >= 570 else np.nan,
        )
        for minutes, name in ((15, "m15"), (30, "m30"), (60, "h1"), (240, "h4")):
            ht = s["htf"].setdefault(
                name, dict(indicators={}, completed=[], active=None, projection={})
            )
            bucket = t.floor(str(minutes) + "min").isoformat()
            active = ht["active"]
            if active is None or active["key"] != bucket:
                active = ht["active"] = dict(
                    key=bucket, Open=o, High=h, Low=l, Close=c, count=0
                )
            active.update(
                High=max(active["High"], h),
                Low=min(active["Low"], l),
                Close=c,
                count=active["count"] + 1,
            )
            if (
                t + pd.Timedelta(minutes=5)
                == pd.Timestamp(bucket) + pd.Timedelta(minutes=minutes)
                and active["count"] == minutes // 5
            ):
                he, completed = ht["indicators"], ht["completed"]
                hc = completed[-1]["Close"] if completed else c
                ha = _ewm(
                    he,
                    "atr",
                    max(
                        active["High"] - active["Low"],
                        abs(active["High"] - hc),
                        abs(active["Low"] - hc),
                    ),
                    1 / 14,
                )
                e20, e50 = _ewm(he, "e20", c, 2 / 21), _ewm(he, "e50", c, 2 / 51)
                ht["projection"] = dict(
                    e20=e20,
                    e50=e50,
                    atr=ha,
                    Close=c,
                    up=e20 > e50 and c > e20,
                    dn=e20 < e50 and c < e20,
                )
                completed.append(dict(active))
                del completed[:-12]
            f[name] = ht["projection"]
        # Values used by the active V1.6/V1.9/V2.1/V2.3/V2.5 filters.
        f["early"] = dict(
            atr_relative=atrrel,
            stochastic=f["k"],
            bb_zscore=(c - np.mean(closes)) / max(np.std(closes), 1e-9)
            if closes
            else np.nan,
            close_gap_atr=abs(o - pc) / max(a, 1e-9),
            day_range_atr=(day["hi"] - day["lo"]) / max(a, 1e-9),
            rsi=100 * gain / max(gain + loss, 1e-9),
        )
        f["context"] = dict(
            adx=adx,
            atr_rel=f["ar"],
            rsi_raw=f["early"]["rsi"],
            stoch_raw=f["k"],
            rv=f["rv"],
            volume_slope=np.mean(volumes[-12:]) / max(np.mean(volumes[-60:-12]), 1)
            if len(volumes) >= 60
            else np.nan,
            bar_range_atr=(h - l) / max(a, 1e-9),
            bbwidth=4 * f["bs"] / max(a, 1e-9),
            volume_z=(v - np.mean(volumes[-48:])) / max(np.std(volumes[-48:]), 1)
            if volumes
            else np.nan,
            lower_wick=(min(o, c) - l) / span,
            upper_wick=(h - max(o, c)) / span,
            channel24_pos=(c - f["lo24"]) / max(f["hi24"] - f["lo24"], 1e-9),
            range24_atr=(f["hi24"] - f["lo24"]) / max(a, 1e-9),
            range96_atr=(f["hi96"] - f["lo96"]) / max(a, 1e-9),
        )
        f["previous"] = dict(
            hi48=max(x["High"] for x in bars[-49:-1]) if len(bars) >= 49 else np.nan,
            lo48=min(x["Low"] for x in bars[-49:-1]) if len(bars) >= 49 else np.nan,
        )
        f["trail"] = trail
        f["bars"] = bars
        f["day"] = day
        f["index"] = s["count"]
        f["span"] = span
        return f

    def finish(self, b, f, output):
        s = self.s
        s["bars"].append(b)
        del s["bars"][:-289]
        s["trail"].append({k: float(f[k]) for k in ("atr", "e20", "e50", "k")})
        del s["trail"][:-288]
        s["count"] += 1
        s["last_output"] = output


def _evaluate(stream, f, ref, params):
    o, h, l, c, a = (f[k] for k in ("o", "h", "l", "c", "atr"))  # noqa: E741
    # Live runner replays the *latest rolling 80,000 rows* on every closed
    # candle. The source's row index is therefore always 0..79,999 and its
    # research-only overlays guarded by (index >= 80,000) cannot fire on
    # this last row. The streaming state count is cumulative and MUST NOT
    # be substituted for the rolling DataFrame's local positional index.
    rolling_row_index = min(f["index"], 79999)
    pos, stop, target, reason = 0, None, None, ""
    hi, lo, pc = f["hi48"], f["lo48"], f["pc"]
    up = (
        c > o and c - o >= params["body_atr"] * a and (c - l) / max(h - l, 1e-10) >= 0.7
    )
    dn = (
        c < o and o - c >= params["body_atr"] * a and (h - c) / max(h - l, 1e-10) >= 0.7
    )
    up &= (
        pc > f["previous"]["hi48"] + 0.06 * a
        and l <= hi + 0.15 * a
        and c > hi + 0.08 * a
    )
    dn &= (
        pc < f["previous"]["lo48"] - 0.06 * a
        and h >= lo - 0.15 * a
        and c < lo - 0.08 * a
    )
    sl, ss = min(l, hi - 0.75 * a) - 0.15 * a, max(h, lo + 0.75 * a) + 0.15 * a
    up &= 0.2 * a <= c - sl <= params["stop_atr_max"] * a
    dn &= 0.2 * a <= ss - c <= params["stop_atr_max"] * a
    if 570 <= f["minute"] < 960 and (
        not params["volume_min"] or f["rv"] >= params["volume_min"]
    ):
        pos = 1 if up and not dn else -1 if dn and not up else 0
    if pos and params["cooldown"] > 0:
        if f["index"] - stream.s["last_base"] < params["cooldown"]:
            pos = 0
        else:
            stream.s["last_base"] = f["index"]
    if pos:
        stop = sl if pos > 0 else ss
        target = c + pos * 3.0 * abs(c - stop)
        reason = ref["_v11core_VERSION"] + "|retest|rolling48"
        if not (570 <= f["minute"] < 870 and f["dow"] != 0):
            pos, stop, target, reason = 0, None, None, ref["_v12_VERSION"] + "|FILTERED"
    day = f["day"]
    if (
        not pos
        and rolling_row_index >= 80000
        and 600 <= f["minute"] < 690
        and f["dow"] < 5
        and day["orb_n"] >= 6
    ):
        low = day["orb_lo"]
        st = min(l, low) - 0.14 * a
        if (
            pc < low + 0.18 * a
            and l <= low + 0.12 * a
            and c > low + 0.24 * a
            and c > o
            and 0.2 * a <= c - st <= 5 * a
            and f["body"] >= 0.3
            and f["q"] >= 0.6
            and f["rv"] >= 1.25
            and f["early"]["atr_relative"] >= 0.9
            and abs(c - st) / max(a, 1e-9) <= 2
        ):
            pos, stop, target, reason = (
                1,
                st,
                c + 3.0 * abs(c - st),
                ref["_v14_VERSION"] + "|NEW_ENTRY|reclaim_ny_orb",
            )

    def early():
        v = dict(f["early"])
        v.update(
            stop_atr=abs(c - stop) / max(a, 1e-9),
            ema_spread=pos * (f["e20"] - f["e50"]) / max(a, 1e-9),
            macd_atr=pos * f["macdh"] / max(a, 1e-9),
            momentum_6=pos * (c - f["bars"][-6]["Close"]) / max(a, 1e-9),
            momentum_24=pos * (c - f["bars"][-24]["Close"]) / max(a, 1e-9),
            opp_wick=(h - max(o, c) if pos > 0 else min(o, c) - l) / f["span"],
        )
        for ht in ("h1", "h4"):
            p = f[ht]
            v[ht + "_ema_dist"] = pos * (c - p["e20"]) / max(a, 1e-9)
            v[ht + "_slope"] = pos * (p["e20"] - p["e50"]) / max(p["atr"], 1e-9)
        return v

    if pos and len(f["bars"]) >= 48 and f["h1"] and f["h4"]:
        v = early()
        if (
            v["stop_atr"] <= 1.66201
            and v["bb_zscore"] <= -2.35055
            and v["h1_ema_dist"] >= 3.33802
        ):
            pos, stop, target, reason = (
                0,
                None,
                None,
                "V1.6|FILTER_ONLY|STOP_ATR_BB_EXTREME_H1_EMA_DIST",
            )
        for version in (19, 21, 23, 25):
            if pos and _hit(ref[f"V{version}_FILTER_RULES"], early()):
                pos, stop, target, reason = (
                    0,
                    None,
                    None,
                    ref[f"V{version}_VERSION"]
                    + ("|VETO" if version == 19 else "|FILTERED"),
                )

    def context():
        v = dict(f["context"])
        aa = max(a, 1e-9)
        v.update(
            body_atr=abs(c - o) / aa,
            stop_atr=abs(c - stop) / aa,
            wick_against=(min(o, c) - l if pos > 0 else h - max(o, c)) / f["span"],
            stoch_direction=f["k"] if pos > 0 else 100 - f["k"],
            macd_dir=pos * f["macdh"] / aa,
            ema20_gap_dir=pos * (c - f["e20"]) / aa,
            ema50_100_dir=pos * (f["e50"] - f["e100"]) / aa,
            ema_spread_abs=abs(np.float32(pos * (f["e20"] - f["e50"]) / aa)),
            vwap_gap_dir=pos * (c - day["pv"] / max(day["vol"], 1e-9)) / aa,
        )
        for n in (12, 48):
            v[f"atr_slope_{n}"] = a / max(f["trail"][-n]["atr"], 1e-9)
        v["ema20_slope_12"] = pos * (f["e20"] - f["trail"][-12]["e20"]) / aa
        v["ema50_slope_48"] = pos * (f["e50"] - f["trail"][-48]["e50"]) / aa
        for n in (12, 96):
            v[f"momentum_{n}"] = pos * (c - f["bars"][-n]["Close"]) / aa
        return v

    for version in (28, 30, 32, 33, 34):
        key = "V28_REJECTION_RULES" if version == 28 else f"V{version}_REJECTION_GROUPS"
        if pos and rolling_row_index >= 80000 and _hit(ref[key], context(), True):
            pos, stop, target, reason = 0, None, None, ""
    # V3.5 is research-only and not active at the right edge of 80K replay.
    if not pos and rolling_row_index >= 80000 and f["dow"] < 5:
        # Selected families: BBWIDTH_REVERSAL, DAY_HI_AFTER_BREAK_FAIL,
        # BBWIDTH_TREND_BREAK. Keep their original priority and float32 casts.
        candidates = (
            4 * f["bs"] / max(a, 1e-8) > 9
            and h > f["hi24"] + 0.20 * max(a, 1e-8)
            and c < f["hi24"] - 0.21 * max(a, 1e-8),
            f["bars"][-2]["Close"] > f["dh"] + 0.14 * max(a, 1e-8)
            and h > f["dh"] + 0.22 * max(a, 1e-8)
            and c < f["dh"] - 0.26 * max(a, 1e-8),
            4 * f["bs"] / max(a, 1e-8) < 3
            and c < f["lo24"] - 0.25 * max(a, 1e-8)
            and f["h1"]["dn"],
        )
        st = max(h, f["hi8"]) + 0.15 * max(a, 1e-8)
        for active, (fi, cfg) in zip(candidates, ref["V35_SELECTED_GROUPS"]):
            B, Q, RV, AR, ADX, RSI, trend, choice, session = cfg
            good = active and c < o and 0.2 * max(a, 1e-8) < st - c < 6 * max(a, 1e-8)
            good &= all(
                np.float32(x) >= np.float32(y)
                for x, y in (
                    (f["body"], B),
                    (f["bearq"], Q),
                    (f["rv"], RV),
                    (f["ar"], AR),
                    (f["adx"], ADX),
                    (100 - f["rsi"], RSI),
                )
            )
            if int(trend):
                good &= f["h1" if int(trend) == 1 else "h4"]["dn"]
            if choice != -1 or session != 0:
                raise ValueError("Frozen V3.5 configuration changed")
            if good:
                pos, stop, target, reason = (
                    -1,
                    float(np.float32(st)),
                    float(np.float32(c - 3 * abs(c - st))),
                    "V3.5_" + ref["V35_FAMILIES"][fi],
                )
                break
    for key in ("V36_REJECTION_GROUPS", "V38_REJECTION_GROUPS", "V39_FILTER_GROUPS"):
        if pos and rolling_row_index >= 80000 and _hit(ref[key], context(), True):
            pos, stop, target, reason = 0, None, None, ""
    return dict(
        Position=pos,
        strategy_stop_loss=stop,
        strategy_target=target,
        signal_reason=reason,
    )


@lru_cache(maxsize=4)
def make_strategy(source):
    if not source_matches_frozen(source):
        raise ValueError("NAS100 V4.8 frozen source mismatch")
    # Always execute the byte-audited frozen source, not the experimental
    # extra DB candidate implementation. Its generate() simply delegates to
    # the frozen V4.8 parent; the adapter supplies its independently tested
    # state machine, making a single source of truth for trading decisions.
    frozen = _frozen_source() if source_match_kind(source) == "pinned_append_only_db_variant" else source
    ref = {"__name__": "nas100_v48_frozen_reference"}
    exec(compile(frozen, "<frozen NAS100 V4.8>", "exec"), ref)
    base = ref["Strategy"]

    class Native(base):
        LIVE_INCREMENTAL_STATE_SCHEMA_VERSION = 1
        LIVE_INCREMENTAL_CAPITAL_INDEPENDENT = True

        def initialize(self, history, config):
            self._stream = None
            if len(history) < 80000:
                raise ValueError("Original 80000-bar warmup required")
            if self.params["family"] != "retest" or self.params["level"] != "rolling48":
                raise ValueError("Frozen parameters required")
            candidate = _Stream()
            for record in history.to_dict("records"):
                b = _bar(record)
                if candidate.s["bars"] and b["Date"] <= candidate.s["bars"][-1]["Date"]:
                    raise ValueError("Warmup must be sorted and unique")
                f = candidate.advance(b)
                output = {**b, **_evaluate(candidate, f, ref, self.params)}
                candidate.finish(b, f, output)
            generated = config.get("generated")
            if generated is None:
                generated = base(history, **self.params).generate()
            assert_exact_signal(candidate.s["last_output"], generated.iloc[-1])
            self._stream = candidate
            # The streaming state is bounded; do not retain the 80K DataFrame.
            self.df = history.iloc[-1:].copy()
            return True

        def on_closed_bar(self, bar):
            if self._stream is None:
                raise ValueError("NAS100 state requires initialization")
            b = _bar(bar)
            s = self._stream.s
            last = s["bars"][-1]
            if b["Date"] == last["Date"] and b == last:
                return deepcopy(s["last_output"])
            if pd.Timestamp(b["Date"]) - pd.Timestamp(last["Date"]) != pd.Timedelta(
                minutes=5
            ):
                raise ValueError(
                    "Duplicate revision, out-of-order candle or gap; backfill/reinitialize required"
                )
            try:
                f = self._stream.advance(b)
                output = {**b, **_evaluate(self._stream, f, ref, self.params)}
                self._stream.finish(b, f, output)
            except Exception:
                # Never retry partially advanced indicator state.
                self._stream = None
                raise
            return deepcopy(output)

        def snapshot(self):
            payload = deepcopy(
                dict(
                    schema=1,
                    source_sha256=SOURCE_SHA256,
                    params=self.params,
                    state=self._stream.s,
                )
            )
            payload["checksum"] = sha256(
                json.dumps(payload, sort_keys=True, allow_nan=False).encode()
            ).hexdigest()
            return payload

        def restore(self, state, config):
            payload = {k: v for k, v in state.items() if k != "checksum"}
            if (
                state.get("checksum")
                != sha256(
                    json.dumps(payload, sort_keys=True, allow_nan=False).encode()
                ).hexdigest()
            ):
                raise ValueError("NAS100 checkpoint checksum mismatch")
            if (
                state.get("schema") != 1
                or state.get("source_sha256") != SOURCE_SHA256
                or state.get("params") != self.params
            ):
                raise ValueError("Incompatible NAS100 checkpoint")
            s = deepcopy(state["state"])
            if s["count"] < 80000 or len(s["bars"]) != 289 or len(s["trail"]) != 288:
                raise ValueError("Incomplete NAS100 checkpoint")
            for b in s["bars"]:
                if _bar(b) != b:
                    raise ValueError("Noncanonical checkpoint")
            if any(
                left["Date"] >= right["Date"]
                for left, right in zip(s["bars"], s["bars"][1:])
            ):
                raise ValueError("Checkpoint bars not sorted/unique")
            if (
                not isinstance(s["count"], int)
                or not -100000 <= s["last_base"] < s["count"]
            ):
                raise ValueError("Checkpoint count/cooldown mismatch")
            if set(s["htf"]) != {"m15", "m30", "h1", "h4"}:
                raise ValueError("Incomplete HTF checkpoint")
            required = {
                "atr",
                "e12",
                "e20",
                "e26",
                "e50",
                "e100",
                "macds",
                "gain",
                "loss",
                "plus",
                "minus",
                "minus27",
                "adx",
                "adx27",
            }
            if set(s["indicators"]) != required or not all(
                math.isfinite(x) for x in s["indicators"].values()
            ):
                raise ValueError("Incomplete indicator checkpoint")
            if s["last_output"]["Date"] != s["bars"][-1]["Date"]:
                raise ValueError("Checkpoint cursor mismatch")
            json.dumps(state, allow_nan=False)
            self._stream = _Stream()
            self._stream.s = s

    return make_incremental_strategy_class(Native)


def assert_exact_signal(actual, expected):
    for key in ("Position", "strategy_stop_loss", "strategy_target", "signal_reason"):
        if key not in actual or key not in expected:
            raise ValueError("Missing parity field: " + key)
        a, b = actual[key], expected[key]
        if pd.isna(a) and pd.isna(b):
            continue
        if pd.isna(a) != pd.isna(b) or a != b:
            raise ValueError(
                f"NAS100 right-edge parity mismatch: {key}: {a!r} != {b!r}"
            )


def verify_right_edge(source, candles, *, warmup=80000, params=None):
    """Offline acceptance check; no tolerance, skipped bars or order approval.

    Each reference is a fresh full-history prefix, not a future-informed row.
    BUY, SELL and HOLD coverage is mandatory, including reasons and restart.
    """
    if warmup < 80000 or len(candles) <= warmup:
        raise ValueError("Original warmup plus validation candles required")
    cls = make_strategy(source)
    params = params or {}
    strategy = cls(candles.iloc[:warmup].copy(), **params)
    generated = strategy.generate()
    strategy.start_live_incremental(generated)
    directions = set()
    for i in range(warmup, len(candles)):
        bar = candles.iloc[i].to_dict()
        checkpoint = json.loads(json.dumps(strategy.snapshot(), allow_nan=False))
        copy = cls(candles.iloc[i - 1 : i].copy(), **params)
        copy.restore(checkpoint, {"interface_version": 1})
        actual = strategy.on_closed_candle(bar).iloc[-1]
        assert_exact_signal(actual, copy.on_closed_candle(bar).iloc[-1])
        reference = cls(candles.iloc[: i + 1].copy(), **params).generate().iloc[-1]
        assert_exact_signal(actual, reference)
        directions.add(int(actual["Position"]))
    if directions != {-1, 0, 1}:
        raise ValueError(
            "Incomplete BUY/SELL/HOLD parity coverage; compatibility rejected"
        )
    return {
        "compatible": True,
        "source_sha256": SOURCE_SHA256,
        "bars": len(candles) - warmup,
        "restore_checked": True,
        "orders_approved": False,
    }
