"""
Plotly chart builders. Pure functions of the results table; no Streamlit here.

Charting rules
  * Observed (historical) values are solid lines with markers; forecasts are dashed and labelled.
  * Where a reporting period is missing, a gap is inserted so the line is NOT drawn across it as if
    the in-between value had been observed.
  * Undefined indices are NaN placeholders and are therefore not plotted.
  * Each reporting date is labelled once on the x-axis (short series); with a single reporting date
    the chart says so instead of showing an empty "trend".
  * Hover labels carry the money unit.
"""
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from .forecasting import METHODS

INK, MUTED, GREY, GRID, LINE = "#1F2A33", "#5B6670", "#8A9299", "#EDF0F3", "#C9D0D6"
PV_C, EV_C, AC_C = "#4C6A92", "#2E7D4F", "#B3261E"
AMBER, CRIT, GOOD = "#E3A008", "#B3261E", "#2E7D4F"
METHOD_C = {"A_CPI": "#4C6A92", "B_CPI_SPI": "#A8323E", "C_BUDGET_RATE": "#2E7D4F", "D_INDEPENDENT": "#7A5C99"}
FONT = "Barlow, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
MAX_LABELLED_DATES = 16
ONE_DATE_NOTE = "Only one reporting date in this data.<br>Add more reporting periods to see a trend."

UNIT_DIV = {"units": 1.0, "lakh": 1e5, "crore": 1e7, "million": 1e6}


def unit_label(currency: str, unit: str) -> str:
    return {"units": currency, "lakh": f"{currency} lakh", "crore": f"{currency} crore",
            "million": f"{currency} million"}[unit]


def METHODS_COLOR(method: str) -> str:  # noqa: N802
    return METHOD_C.get(method, INK)


def _layout(fig: go.Figure, title: str, ytitle: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", y=0.98, font=dict(size=16, color=INK, family=FONT)),
        font=dict(family=FONT, color=INK, size=12.5), height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
        margin=dict(l=8, r=16, t=70, b=40), hovermode="x unified",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor="#D5DAE0", font=dict(family=FONT, size=12, color=INK)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, font=dict(size=12),
                    bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(title_text="", showgrid=False, linecolor=LINE, ticks="outside", tickcolor=LINE,
                     tickfont=dict(color=MUTED))
    fig.update_yaxes(title_text=ytitle, title_font=dict(color=MUTED, size=12), gridcolor=GRID, zeroline=False,
                     linecolor=LINE, tickfont=dict(color=MUTED))
    return fig


def _date_axis(fig: go.Figure, dates) -> None:
    """Label every reporting date once (short series); pad the range when there is a single date."""
    ds = sorted(pd.Timestamp(d) for d in pd.Series(dates).dropna().unique())
    if not ds:
        return
    if len(ds) <= MAX_LABELLED_DATES:
        fig.update_xaxes(tickvals=ds, ticktext=[d.strftime("%d %b %y") for d in ds])
    else:
        fig.update_xaxes(tickformat="%b %Y")
    if len(ds) == 1:
        fig.update_xaxes(range=[ds[0] - pd.Timedelta(days=20), ds[0] + pd.Timedelta(days=20)])
        # Shown under the axis, where it cannot cover the BAC / EAC / status-date labels inside the plot.
        fig.update_xaxes(title_text=ONE_DATE_NOTE, title_font=dict(size=12, color=MUTED), title_standoff=10)
        fig.update_layout(margin_b=78)


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


def _ms(d) -> float:
    return pd.Timestamp(d).timestamp() * 1000


def cumulative_chart(res: pd.DataFrame, bac: float, method: str, currency: str, unit: str,
                     frequency: str, selected_date=None, baseline_finish=None) -> go.Figure:
    k = UNIT_DIV[unit]
    ul = unit_label(currency, unit)
    d = with_gap_breaks(res, frequency)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["reporting_date"], y=d["pv"] / k, name="PV planned", mode="lines+markers",
                             line=dict(color=PV_C, width=2.5, shape="linear"), marker=dict(size=7),
                             fill="tozeroy", fillcolor="rgba(76,106,146,0.07)", connectgaps=False,
                             hovertemplate=f"%{{y:,.2f}} {ul}"))
    fig.add_trace(go.Scatter(x=d["reporting_date"], y=d["ev"] / k, name="EV earned", mode="lines+markers",
                             line=dict(color=EV_C, width=3), marker=dict(size=8, line=dict(width=1.5, color="#fff")),
                             connectgaps=False, hovertemplate=f"%{{y:,.2f}} {ul}"))
    fig.add_trace(go.Scatter(x=d["reporting_date"], y=d["ac"] / k, name="AC actual cost", mode="lines+markers",
                             line=dict(color=AC_C, width=3), marker=dict(size=8, line=dict(width=1.5, color="#fff")),
                             connectgaps=False, hovertemplate=f"%{{y:,.2f}} {ul}"))
    fig.add_hline(y=bac / k, line=dict(color=INK, width=1.2),
                  annotation_text=f"BAC {bac / k:,.2f}", annotation_position="top left",
                  annotation_font=dict(color=INK, size=11))
    last = res.iloc[-1] if selected_date is None else res[res["reporting_date"] == selected_date].iloc[0]
    eac = last.get(f"eac_{method}")
    if pd.notna(eac):
        fig.add_hline(y=eac / k, line=dict(color=METHODS_COLOR(method), width=1.6, dash="dash"),
                      annotation_text=f"EAC forecast ({method[0]}) {eac / k:,.2f}", annotation_position="top right",
                      annotation_font=dict(color=METHODS_COLOR(method), size=11))
    if baseline_finish is not None:
        fig.add_vline(x=_ms(baseline_finish), line=dict(color=GREY, dash="dot", width=1),
                      annotation_text="Baseline finish", annotation_position="bottom left",
                      annotation_font=dict(color=MUTED, size=11))
    if selected_date is not None:
        fig.add_vline(x=_ms(selected_date), line=dict(color="#9AA5B1", width=1),
                      annotation_text="Status date", annotation_position="top left",
                      annotation_font=dict(color=MUTED, size=11))
    fig = _layout(fig, "Cumulative PV, EV and AC (S-curve)", ul, 430)
    _date_axis(fig, res["reporting_date"])
    return fig


def combined_index_chart(res: pd.DataFrame, frequency: str, warn: float, crit: float) -> go.Figure:
    """CPI and SPI on one chart over red / amber / green screening zones."""
    d = with_gap_breaks(res, frequency)
    fig = go.Figure()
    vals = pd.concat([res["cpi"], res["spi"]]).dropna()
    lo = min([crit] + list(vals)) - 0.05
    hi = max([warn, 1.0] + list(vals)) + 0.06
    fig.add_hrect(y0=0, y1=crit, fillcolor=CRIT, opacity=0.07, line_width=0, layer="below")
    fig.add_hrect(y0=crit, y1=warn, fillcolor=AMBER, opacity=0.10, line_width=0, layer="below")
    fig.add_hrect(y0=warn, y1=max(hi, warn) + 10, fillcolor=GOOD, opacity=0.06, line_width=0, layer="below")
    fig.add_hline(y=1.0, line=dict(color=INK, width=1), annotation_text="1.00 = on plan",
                  annotation_position="top left", annotation_font=dict(size=11, color=INK))
    fig.add_hline(y=crit, line=dict(color=CRIT, width=1, dash="dot"),
                  annotation_text=f"critical < {crit:.2f}", annotation_position="bottom left",
                  annotation_font=dict(size=11, color=CRIT))
    for col, label, color in (("cpi", "CPI", AC_C), ("spi", "SPI", PV_C)):
        ys = d[col]
        last_i = ys.last_valid_index()
        text = [f"{v:.2f}" if i == last_i else "" for i, v in ys.items()]
        fig.add_trace(go.Scatter(x=d["reporting_date"], y=ys, name=label, mode="lines+markers+text",
                                 text=text, textposition="middle right", textfont=dict(color=color, size=12),
                                 cliponaxis=False,
                                 line=dict(color=color, width=3), marker=dict(size=8, line=dict(width=1.5, color="#fff")),
                                 connectgaps=False, hovertemplate="%{y:.3f}"))
        undefined = res[res[f"{col}__status"] != "ok"]
        if len(undefined):
            fig.add_trace(go.Scatter(x=undefined["reporting_date"], y=[1.0] * len(undefined), mode="markers",
                                     name=f"{label} undefined", marker=dict(symbol="x-open", size=10, color=GREY),
                                     hovertext=undefined[f"{col}__note"], hoverinfo="text"))
    fig = _layout(fig, "CPI and SPI trend", "Index (1.00 = on plan)", 430)
    fig.update_yaxes(range=[lo, hi])
    fig.update_layout(margin=dict(l=8, r=46, t=70, b=40))      # room for the end-of-line values
    _date_axis(fig, res["reporting_date"])
    return fig


def index_chart(res: pd.DataFrame, col: str, label: str, color: str, frequency: str,
                warn: float, crit: float) -> go.Figure:
    """Single-index trend (kept for reuse; the dashboard shows the combined chart)."""
    d = with_gap_breaks(res, frequency)
    fig = go.Figure()
    fig.add_hrect(y0=crit, y1=warn, fillcolor=AMBER, opacity=0.10, line_width=0)
    fig.add_hline(y=1.0, line=dict(color=INK, width=1), annotation_text="1.00 = on plan",
                  annotation_position="top left")
    fig.add_hline(y=crit, line=dict(color=CRIT, width=1, dash="dot"),
                  annotation_text=f"critical < {crit:.2f}", annotation_position="bottom left")
    fig.add_trace(go.Scatter(x=d["reporting_date"], y=d[col], name=label, mode="lines+markers",
                             line=dict(color=color, width=2.5), marker=dict(size=7), connectgaps=False,
                             hovertemplate="%{y:.3f}"))
    fig = _layout(fig, f"{label} trend", label, 340)
    vals = res[col].dropna()
    fig.update_yaxes(range=[min([crit] + list(vals)) - 0.03, max([1.0] + list(vals)) + 0.04])
    _date_axis(fig, res["reporting_date"])
    return fig


def progress_chart(periods: pd.DataFrame, frequency: str) -> go.Figure:
    d = with_gap_breaks(periods, frequency)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["reporting_date"], y=d["planned_pct"], name="Planned progress",
                             mode="lines+markers", line=dict(color=PV_C, width=2.5), connectgaps=False,
                             fill="tozeroy", fillcolor="rgba(76,106,146,0.07)", hovertemplate="%{y:.2f}%"))
    fig.add_trace(go.Scatter(x=d["reporting_date"], y=d["actual_pct"], name="Actual physical progress",
                             mode="lines+markers", line=dict(color=EV_C, width=3), connectgaps=False,
                             hovertemplate="%{y:.2f}%"))
    fig = _layout(fig, "Planned vs actual progress (% of BAC)", "% of budgeted scope", 360)
    fig.update_yaxes(range=[0, 105], ticksuffix="%")
    _date_axis(fig, periods["reporting_date"])
    return fig


def budget_vs_forecast_chart(row, bac: float, currency: str, unit: str) -> go.Figure:
    k = UNIT_DIV[unit]
    names, vals, cols, texts = ["BAC (budget)"], [bac / k], [INK], [f"{bac / k:,.2f}"]
    for m, meta in METHODS.items():
        v = row.get(f"eac_{m}")
        names.append(f"EAC {m[0]}: {meta['short']}")
        if pd.notna(v):
            vals.append(v / k)
            texts.append(f"{v / k:,.2f}")
        else:
            vals.append(0)
            texts.append("not available")
        cols.append(METHOD_C[m])
    fig = go.Figure(go.Bar(x=vals, y=names, orientation="h", marker=dict(color=cols, line=dict(width=0)),
                           text=texts, textposition="outside", cliponaxis=False,
                           hovertemplate=f"%{{x:,.2f}} {unit_label(currency, unit)}<extra></extra>"))
    fig = _layout(fig, "Budget vs forecast final cost (EAC by method)", "", 330)
    fig.update_xaxes(title_text=unit_label(currency, unit), tickformat=",.0f", showgrid=True, gridcolor=GRID)
    fig.update_yaxes(title_text="", autorange="reversed", gridcolor="rgba(0,0,0,0)")
    fig.update_layout(hovermode="closest", margin=dict(l=10, r=90, t=60, b=40), bargap=0.35)
    return fig


def eac_trend_chart(res: pd.DataFrame, bac: float, currency: str, unit: str, frequency: str) -> go.Figure:
    k = UNIT_DIV[unit]
    d = with_gap_breaks(res, frequency)
    fig = go.Figure()
    fig.add_hline(y=bac / k, line=dict(color=INK, width=1.2), annotation_text=f"BAC {bac / k:,.2f}",
                  annotation_position="bottom right")
    for m, meta in METHODS.items():
        col = f"eac_{m}"
        if col in d and d[col].notna().any():
            fig.add_trace(go.Scatter(x=d["reporting_date"], y=d[col] / k, name=f"EAC {m[0]} ({meta['short']})",
                                     mode="lines+markers", line=dict(color=METHOD_C[m], dash="dash", width=2.2),
                                     connectgaps=False, hovertemplate=f"%{{y:,.2f}} {unit_label(currency, unit)}"))
    fig = _layout(fig, "EAC over time (forecast made at each date)", unit_label(currency, unit), 390)
    _date_axis(fig, res["reporting_date"])
    return fig


def wp_variance_chart(wp: pd.DataFrame, date, currency: str, unit: str) -> Optional[go.Figure]:
    if wp is None or not len(wp):
        return None
    k = UNIT_DIV[unit]
    d = wp[wp["reporting_date"] == date].copy()
    d["label"] = d["activity_id"].astype(str) + " " + d.get("activity_name", "").fillna("").astype(str)
    fig = go.Figure()
    fig.add_trace(go.Bar(y=d["label"], x=d["cv_i"] / k, name="CV (EV − AC)", orientation="h", marker_color=AC_C,
                         hovertemplate=f"%{{x:,.2f}} {unit_label(currency, unit)}"))
    fig.add_trace(go.Bar(y=d["label"], x=d["sv_i"] / k, name="SV (EV − PV)", orientation="h", marker_color=PV_C,
                         hovertemplate=f"%{{x:,.2f}} {unit_label(currency, unit)}"))
    fig = _layout(fig, "Variance by work package at the selected date", "", 60 + 42 * len(d) + 90)
    fig.update_layout(barmode="group", hovermode="y unified", bargap=0.3)
    fig.update_xaxes(title_text=f"{unit_label(currency, unit)} (negative = unfavourable)", zeroline=True,
                     zerolinecolor=INK, showgrid=True, gridcolor=GRID)
    fig.update_yaxes(title_text="", autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig
