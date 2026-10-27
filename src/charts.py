"""
Plotly chart builders. Pure functions of the results table; no Streamlit here.

Charting rules
  * Observed (historical) values are solid lines with markers.
  * Forecasts are dashed and labelled "forecast".
  * Where a reporting period is missing, a gap is inserted so that the line is
    NOT drawn across it as if the in-between value had been observed.
  * Undefined indices are NaN placeholders and are therefore not plotted.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from .forecasting import METHODS

INK, PAPER, GREY = "#1F2A33", "#F6F7F5", "#8A9299"
PV_C, EV_C, AC_C = "#4C6A92", "#2E7D4F", "#A8323E"
AMBER, CRIT = "#E3A008", "#B3261E"
METHOD_C = {"A_CPI": "#4C6A92", "B_CPI_SPI": "#A8323E", "C_BUDGET_RATE": "#2E7D4F", "D_INDEPENDENT": "#7A5C99"}
FONT = "Barlow, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

UNIT_DIV = {"units": 1.0, "lakh": 1e5, "crore": 1e7, "million": 1e6}


def unit_label(currency: str, unit: str) -> str:
    return {"units": currency, "lakh": f"{currency} lakh", "crore": f"{currency} crore",
            "million": f"{currency} million"}[unit]


def _layout(fig: go.Figure, title: str, ytitle: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=17, color=INK)),
        font=dict(family=FONT, color=INK, size=13), height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        margin=dict(l=10, r=10, t=56, b=90), hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0),
    )
    fig.update_xaxes(title_text="Reporting date", showgrid=False, linecolor=GREY, tickformat="%d %b %Y")
    fig.update_yaxes(title_text=ytitle, gridcolor="#E4E7EA", zeroline=False, linecolor=GREY)
    return fig


def with_gap_breaks(df: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """Insert NaN rows inside missing reporting periods so lines break instead of bridging."""
    if frequency not in ("Monthly", "Weekly") or len(df) < 2:
        return df
    rows = []
    d = df.sort_values("reporting_date").reset_index(drop=True)
    for i in range(len(d)):
        rows.append(d.iloc[i].to_dict())
        if i < len(d) - 1:
            a, b = pd.Timestamp(d.loc[i, "reporting_date"]), pd.Timestamp(d.loc[i + 1, "reporting_date"])
            gap = ((b.year - a.year) * 12 + b.month - a.month) > 1 if frequency == "Monthly" else (b - a).days > 8
            if gap:
                rows.append({"reporting_date": a + (b - a) / 2})
    return pd.DataFrame(rows)


def cumulative_chart(res: pd.DataFrame, bac: float, method: str, currency: str, unit: str,
                     frequency: str, selected_date=None, baseline_finish=None) -> go.Figure:
    k = UNIT_DIV[unit]
    d = with_gap_breaks(res, frequency)
    fig = go.Figure()
    for col, name, c in (("pv", "PV — planned value", PV_C), ("ev", "EV — earned value", EV_C),
                         ("ac", "AC — actual cost", AC_C)):
        fig.add_trace(go.Scatter(x=d["reporting_date"], y=d[col] / k, name=name, mode="lines+markers",
                                 line=dict(color=c, width=2.5), marker=dict(size=6), connectgaps=False,
                                 hovertemplate="%{y:,.2f}"))
    fig.add_hline(y=bac / k, line=dict(color=INK, width=1), annotation_text="BAC",
                  annotation_position="bottom right")
    last = res.iloc[-1] if selected_date is None else res[res["reporting_date"] == selected_date].iloc[0]
    eac = last.get(f"eac_{method}")
    if pd.notna(eac):
        fig.add_hline(y=eac / k, line=dict(color=METHODS_COLOR(method), width=1.5, dash="dash"),
                      annotation_text=f"EAC forecast (method {method[0]})", annotation_position="top right")
    if baseline_finish is not None:
        fig.add_vline(x=pd.Timestamp(baseline_finish).timestamp() * 1000, line=dict(color=GREY, dash="dot"),
                      annotation_text="Baseline finish", annotation_position="bottom left")
    if selected_date is not None:
        fig.add_vline(x=pd.Timestamp(selected_date).timestamp() * 1000, line=dict(color=GREY, width=1))
    return _layout(fig, "Cumulative PV, EV and AC", unit_label(currency, unit), 420)


def METHODS_COLOR(method: str) -> str:  # noqa: N802
    return METHOD_C.get(method, INK)


def index_chart(res: pd.DataFrame, col: str, label: str, color: str, frequency: str,
                warn: float, crit: float) -> go.Figure:
    d = with_gap_breaks(res, frequency)
    fig = go.Figure()
    fig.add_hrect(y0=crit, y1=warn, fillcolor=AMBER, opacity=0.08, line_width=0)
    fig.add_hline(y=1.0, line=dict(color=INK, width=1), annotation_text="1.00 = on plan",
                  annotation_position="top left")
    fig.add_hline(y=crit, line=dict(color=CRIT, width=1, dash="dot"),
                  annotation_text=f"critical < {crit:.2f}", annotation_position="bottom left")
    fig.add_trace(go.Scatter(x=d["reporting_date"], y=d[col], name=label, mode="lines+markers",
                             line=dict(color=color, width=2.5), marker=dict(size=7), connectgaps=False,
                             hovertemplate="%{y:.3f}"))
    undefined = res[res[f"{col}__status"] != "ok"]
    if len(undefined):
        fig.add_trace(go.Scatter(x=undefined["reporting_date"], y=[1.0] * len(undefined), mode="markers",
                                 name=f"{label} undefined", marker=dict(symbol="x-open", size=10, color=GREY),
                                 hovertext=undefined[f"{col}__note"], hoverinfo="text"))
    fig = _layout(fig, f"{label} trend", label, 340)
    vals = res[col].dropna()
    lo = min([crit] + list(vals)) - 0.03
    hi = max([1.0] + list(vals)) + 0.04
    fig.update_yaxes(range=[lo, hi])
    fig.update_layout(showlegend=len(undefined) > 0)
    return fig


def combined_index_chart(res: pd.DataFrame, frequency: str, warn: float, crit: float) -> go.Figure:
    """CPI and SPI on one chart, with the 1.00 line and the warning/critical band."""
    d = with_gap_breaks(res, frequency)
    fig = go.Figure()
    fig.add_hrect(y0=crit, y1=warn, fillcolor=AMBER, opacity=0.08, line_width=0)
    fig.add_hline(y=1.0, line=dict(color=INK, width=1), annotation_text="1.00 = on plan",
                  annotation_position="top left")
    fig.add_hline(y=crit, line=dict(color=CRIT, width=1, dash="dot"),
                  annotation_text=f"critical < {crit:.2f}", annotation_position="bottom left")
    for col, label, color in (("cpi", "CPI", AC_C), ("spi", "SPI", PV_C)):
        fig.add_trace(go.Scatter(x=d["reporting_date"], y=d[col], name=label, mode="lines+markers",
                                 line=dict(color=color, width=2.5), marker=dict(size=7), connectgaps=False,
                                 hovertemplate="%{y:.3f}"))
        undefined = res[res[f"{col}__status"] != "ok"]
        if len(undefined):
            fig.add_trace(go.Scatter(x=undefined["reporting_date"], y=[1.0] * len(undefined), mode="markers",
                                     name=f"{label} undefined", marker=dict(symbol="x-open", size=10, color=GREY),
                                     hovertext=undefined[f"{col}__note"], hoverinfo="text"))
    fig = _layout(fig, "CPI and SPI trend", "Index (1.00 = on plan)", 420)
    vals = pd.concat([res["cpi"], res["spi"]]).dropna()
    fig.update_yaxes(range=[min([crit] + list(vals)) - 0.03, max([1.0] + list(vals)) + 0.04])
    return fig


def progress_chart(periods: pd.DataFrame, frequency: str) -> go.Figure:
    d = with_gap_breaks(periods, frequency)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["reporting_date"], y=d["planned_pct"], name="Planned progress",
                             mode="lines+markers", line=dict(color=PV_C, width=2.5), connectgaps=False,
                             hovertemplate="%{y:.2f}%"))
    fig.add_trace(go.Scatter(x=d["reporting_date"], y=d["actual_pct"], name="Actual physical progress",
                             mode="lines+markers", line=dict(color=EV_C, width=2.5), connectgaps=False,
                             hovertemplate="%{y:.2f}%"))
    fig = _layout(fig, "Planned vs actual progress (cumulative, % of BAC)", "% of budgeted scope", 340)
    fig.update_yaxes(range=[0, 105], ticksuffix="%")
    return fig


def budget_vs_forecast_chart(row, bac: float, currency: str, unit: str) -> go.Figure:
    k = UNIT_DIV[unit]
    names, vals, cols, texts = ["BAC"], [bac / k], [INK], [f"{bac / k:,.2f}"]
    for m, meta in METHODS.items():
        v = row.get(f"eac_{m}")
        names.append(f"EAC {m[0]}")
        if pd.notna(v):
            vals.append(v / k)
            texts.append(f"{v / k:,.2f}")
        else:
            vals.append(0)
            texts.append("not available")
        cols.append(METHOD_C[m])
    fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker_color=cols, text=texts,
                           textposition="outside", cliponaxis=False, hovertemplate="%{x:,.2f}<extra></extra>"))
    fig = _layout(fig, "Budget vs forecast final cost (EAC by method)", "", 320)
    fig.update_xaxes(title_text=unit_label(currency, unit), tickformat=",.0f", showgrid=True, gridcolor="#E4E7EA")
    fig.update_yaxes(title_text="", autorange="reversed")
    fig.update_layout(hovermode="closest", margin=dict(l=10, r=90, t=56, b=40))
    return fig


def eac_trend_chart(res: pd.DataFrame, bac: float, currency: str, unit: str, frequency: str) -> go.Figure:
    k = UNIT_DIV[unit]
    d = with_gap_breaks(res, frequency)
    fig = go.Figure()
    fig.add_hline(y=bac / k, line=dict(color=INK, width=1), annotation_text="BAC", annotation_position="bottom right")
    for m, meta in METHODS.items():
        col = f"eac_{m}"
        if col in d and d[col].notna().any():
            fig.add_trace(go.Scatter(x=d["reporting_date"], y=d[col] / k, name=f"EAC {m[0]} ({meta['short']})",
                                     mode="lines+markers", line=dict(color=METHOD_C[m], dash="dash", width=2),
                                     connectgaps=False, hovertemplate="%{y:,.2f}"))
    return _layout(fig, "EAC over time (forecast made at each date)", unit_label(currency, unit), 380)


def wp_variance_chart(wp: pd.DataFrame, date, currency: str, unit: str) -> Optional[go.Figure]:
    if wp is None or not len(wp):
        return None
    k = UNIT_DIV[unit]
    d = wp[wp["reporting_date"] == date].copy()
    d["label"] = d["activity_id"].astype(str) + " " + d.get("activity_name", "").fillna("").astype(str)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d["label"], x=d["cv_i"] / k, name="CV (EV − AC)", orientation="h", marker_color=AC_C,
                         hovertemplate="%{x:,.2f}"))
    fig.add_trace(go.Bar(y=d["label"], x=d["sv_i"] / k, name="SV (EV − PV)", orientation="h", marker_color=PV_C,
                         hovertemplate="%{x:,.2f}"))
    fig = _layout(fig, "Variance by work package at the selected date", "", 60 + 42 * len(d) + 80)
    fig.update_layout(barmode="group", hovermode="y unified")
    fig.update_xaxes(title_text=f"{unit_label(currency, unit)} (negative = unfavourable)", zeroline=True,
                     zerolinecolor=INK)
    fig.update_yaxes(title_text="", autorange="reversed")
    return fig
