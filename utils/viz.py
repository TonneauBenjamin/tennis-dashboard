"""Chart functions and page building blocks that enforce one consistent, accessible style.

Colour roles (validated for colour-vision deficiency, see README):
tennis = clay orange, comparison sport = blue, benchmark = neutral grey (context only),
women = violet, men = aqua. Every multi-series chart is direct-labelled, so identity
never relies on colour alone.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import prep
from utils.io import AGE_BAND_LABELS, AGE_BANDS, COLORS
from utils.prep import BENCH, TENNIS

FONT = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
          "toImageButtonOptions": {"format": "png", "scale": 2}}


def color_for(group: str) -> str:
    return {TENNIS: COLORS["tennis"], BENCH: COLORS["all_sports"]}.get(group, COLORS["comparison"])


def base(fig: go.Figure, title: str, height: int = 420, legend: bool = False) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=16, color=COLORS["ink"])),
        font=dict(family=FONT, size=13, color=COLORS["ink_secondary"]),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=COLORS["surface"],
        margin=dict(l=10, r=30, t=60, b=10), height=height, showlegend=legend,
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, size=13)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor=COLORS["grid"], ticks="outside", tickcolor=COLORS["grid"],
                     title_font=dict(size=12))
    fig.update_yaxes(gridcolor=COLORS["grid"], zeroline=False, title_font=dict(size=12))
    return fig


def covid_band(fig: go.Figure, years: list[int]) -> None:
    lo, hi = max(min(years), 2020), min(max(years), 2021)
    if lo > hi:
        return
    fig.add_vrect(x0=lo - 0.5, x1=hi + 0.5, fillcolor=COLORS["covid_band"], line_width=0, layer="below")
    fig.add_annotation(x=(lo + hi) / 2, y=1.0, yref="paper", yanchor="bottom", showarrow=False,
                       text="COVID-19 club closures", font=dict(size=11, color=COLORS["muted"]))


# ------------------------------------------------------------------ section 1
def index_chart(idx: pd.DataFrame, raw: pd.DataFrame, start: int) -> go.Figure:
    fig = go.Figure()
    years = list(idx.index)
    order = [c for c in idx.columns if c not in (TENNIS, BENCH)] + [BENCH, TENNIS]  # tennis on top
    for g in order:
        width = 3 if g == TENNIS else 2
        fig.add_trace(go.Scatter(
            x=years, y=idx[g], name=g, mode="lines+markers",
            line=dict(color=color_for(g), width=width), marker=dict(size=8 if g == TENNIS else 6),
            customdata=raw[g].values,
            hovertemplate=f"<b>{g}</b><br>%{{x}} season: %{{y:.1f}} (index)<br>%{{customdata:,.0f}} licences<extra></extra>"))
        fig.add_annotation(x=years[-1], y=idx[g].iloc[-1], text=f"<b>{g}</b> {idx[g].iloc[-1]:.0f}",
                           xanchor="left", xshift=8, showarrow=False, font=dict(color=color_for(g), size=12))
    fig.add_hline(y=100, line=dict(color=COLORS["muted"], width=1), annotation_text=f"{start} level = 100",
                  annotation_position="bottom left", annotation_font=dict(size=11, color=COLORS["muted"]))
    covid_band(fig, years)
    base(fig, f"Licences indexed to {start} (= 100)")
    fig.update_xaxes(tickvals=years, title="Licence year (season ending)", range=[years[0] - 0.3, years[-1] + 1.1])
    fig.update_yaxes(title="Index (start year = 100)")
    return fig


def peers_chart(p: pd.DataFrame, tennis_name: str, comparison_name: str | None) -> go.Figure:
    fig = go.Figure()
    sizeref = 2.0 * p["start"].max() / (46 ** 2)  # largest bubble ≈ 46 px
    bubble = dict(sizemode="area", sizeref=sizeref, sizemin=4)
    other = p[~p["name"].isin([tennis_name, comparison_name])]
    fig.add_trace(go.Scatter(
        x=other["worst"], y=other["growth"], mode="markers", name="Other single-sport federations",
        marker=dict(size=other["start"], color=COLORS["all_sports"], opacity=0.55,
                    line=dict(color="white", width=1), **bubble),
        text=other["name"], customdata=other["start"],
        hovertemplate="<b>%{text}</b><br>Worst year vs start: %{x:.1f}%<br>End vs start: %{y:.1f}%"
                      "<br>%{customdata:,.0f} licences at start<extra></extra>"))
    for name, col in [(comparison_name, COLORS["comparison"]), (tennis_name, COLORS["tennis"])]:
        r = p[p["name"] == name]
        if r.empty or name is None:
            continue
        fig.add_trace(go.Scatter(
            x=r["worst"], y=r["growth"], mode="markers+text", name=name, text=[f"<b>{name}</b>"],
            textposition="top center", textfont=dict(color=col),
            marker=dict(size=r["start"], color=col, line=dict(color="white", width=2), **bubble),
            customdata=r["start"],
            hovertemplate=f"<b>{name}</b><br>Worst year vs start: %{{x:.1f}}%<br>End vs start: %{{y:.1f}}%"
                          "<br>%{customdata:,.0f} licences at start<extra></extra>"))
    # label peers that were more resilient than tennis, plus the hardest-hit federation
    t_worst = p.loc[p["name"] == tennis_name, "worst"]
    t_worst = t_worst.iloc[0] if len(t_worst) else 0
    labelled = pd.concat([other[other["worst"] > t_worst], other.nsmallest(1, "worst")]).drop_duplicates("name")
    for i, (_, r) in enumerate(labelled.iterrows()):
        fig.add_annotation(x=r["worst"], y=r["growth"], text=r["name"], showarrow=True, arrowhead=0,
                           arrowcolor=COLORS["grid"], ax=40 if i % 2 else -40, ay=-22 if i % 2 else 22,
                           font=dict(size=10, color=COLORS["ink_secondary"]))
    fig.add_hline(y=0, line=dict(color=COLORS["grid"], width=1))
    fig.add_vline(x=0, line=dict(color=COLORS["grid"], width=1))
    fig.add_annotation(x=0, y=1, xref="x", yref="paper", text="Never fell below start →", showarrow=False,
                       xanchor="left", xshift=4, font=dict(size=11, color=COLORS["muted"]))
    base(fig, "Resilience vs recovery: single-sport federations (bubble = size)", height=460)
    fig.update_xaxes(title="Worst year vs start year (%)", ticksuffix="%", zeroline=False)
    fig.update_yaxes(title="End year vs start year (%)", ticksuffix="%")
    return fig


# ------------------------------------------------------------------ section 2
METRICS = {
    "per1000": ("Licences per 1,000 residents", "{:.1f}", "sequential"),
    "growth": ("Growth over the period (%)", "{:+.1f}%", "diverging"),
    "women_share": ("Women's share of licences (%)", "{:.1f}%", "sequential"),
}


def choropleth(dep: pd.DataFrame, geo: dict, metric: str, national: float) -> go.Figure:
    label, fmt, kind = METRICS[metric]
    sel = dep[dep["selected"]]
    rest = dep[~dep["selected"]]
    if kind == "diverging":
        lim = float(np.nanpercentile(np.abs(sel[metric]), 95)) or 1
        scale, zmin, zmax = COLORS["diverging"], -lim, lim
    else:
        scale = COLORS["sequential"]
        zmin, zmax = (float(np.nanpercentile(sel[metric], 3)), float(np.nanpercentile(sel[metric], 97)))
    fig = go.Figure()
    if not rest.empty:
        fig.add_trace(go.Choroplethmap(
            geojson=geo, featureidkey="properties.code", locations=rest["dep"], z=[0] * len(rest),
            colorscale=[[0, "#ecebe6"], [1, "#ecebe6"]], showscale=False,
            marker=dict(line=dict(color="white", width=0.6)),
            text=rest["dep_name"], hovertemplate="%{text}<br>(outside selection)<extra></extra>"))
    custom = np.stack([sel["dep"], sel["licences_end"], sel["per1000"], sel["growth"], sel["women_share"]], axis=-1)
    fig.add_trace(go.Choroplethmap(
        geojson=geo, featureidkey="properties.code", locations=sel["dep"], z=sel[metric],
        colorscale=scale, zmin=zmin, zmax=zmax, marker=dict(line=dict(color="white", width=0.6)),
        text=sel["dep_name"], customdata=custom,
        colorbar=dict(title=dict(text=label, side="right"), thickness=12, len=0.75,
                      ticksuffix="%" if metric != "per1000" else ""),
        hovertemplate="<b>%{text}</b> (%{customdata[0]})<br>%{customdata[1]:,.0f} licences"
                      "<br>%{customdata[2]:.1f} per 1,000 residents<br>Growth: %{customdata[3]:+.1f}%"
                      "<br>Women: %{customdata[4]:.1f}%<extra></extra>"))
    # "white-bg" needs no tiles, fonts or CDN: the map works offline and loads instantly.
    fig.update_layout(map=dict(style="white-bg", center=dict(lon=0.9, lat=45.5), zoom=4.0))
    base(fig, f"{label} by département", height=600)
    fig.update_layout(margin=dict(l=0, r=0, t=50, b=0))
    fig.add_annotation(x=0.01, y=0.01, xref="paper", yref="paper", showarrow=False, align="left",
                       text="Insets (west, not to scale): Guadeloupe · Martinique · Guyane · La Réunion",
                       font=dict(size=10, color=COLORS["muted"]), bgcolor="rgba(255,255,255,0.8)")
    return fig


def ranking_chart(dep: pd.DataFrame, metric: str, national: float, n: int = 10) -> go.Figure:
    label, fmt, _ = METRICS[metric]
    d = dep[dep["selected"]].dropna(subset=[metric]).sort_values(metric)
    if len(d) > 2 * n:
        d = pd.concat([d.head(n), d.tail(n)])
    top_names = set(d.tail(n)["dep_name"])
    colors = [COLORS["tennis"] if nm in top_names else COLORS["all_sports"] for nm in d["dep_name"]]
    fig = go.Figure(go.Bar(
        x=d[metric], y=d["dep_name"] + " (" + d["dep"] + ")", orientation="h", marker_color=colors,
        text=[fmt.format(v) for v in d[metric]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>" + label + ": %{x:.1f}<extra></extra>"))
    fig.add_vline(x=national, line=dict(color=COLORS["ink_secondary"], width=1.5),
                  annotation_text=f"Selection average {fmt.format(national)}", annotation_position="top",
                  annotation_font=dict(size=11))
    base(fig, f"Top and bottom {n} départements", height=max(380, 22 * len(d) + 80))
    fig.update_layout(bargap=0.25)
    fig.update_xaxes(title=label, showgrid=True, gridcolor=COLORS["grid"])
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
    return fig


# ------------------------------------------------------------------ section 3
def pyramid_chart(p: pd.DataFrame, start: int, end: int, highlight: set[str]) -> go.Figure:
    labels = [AGE_BAND_LABELS[b] for b in AGE_BANDS]
    fig = go.Figure()
    for sex, sign, col, name in [("H", -1, COLORS["men"], "Men"), ("F", 1, COLORS["women"], "Women")]:
        e = p[(p["year"] == end) & (p["sex"] == sex)].set_index("age_band")["licences"].reindex(AGE_BANDS).fillna(0)
        s = p[(p["year"] == start) & (p["sex"] == sex)].set_index("age_band")["licences"].reindex(AGE_BANDS).fillna(0)
        op = [1.0 if b in highlight else 0.35 for b in AGE_BANDS]
        fig.add_trace(go.Bar(
            y=labels, x=sign * e.values, orientation="h", name=f"{name} {end}", marker=dict(color=col, opacity=op),
            customdata=np.stack([e.values, s.values, (e.values / np.where(s.values == 0, np.nan, s.values) - 1) * 100], -1),
            hovertemplate=f"<b>{name}, %{{y}} yrs</b><br>{end}: %{{customdata[0]:,.0f}}<br>{start}: %{{customdata[1]:,.0f}}"
                          "<br>Change: %{customdata[2]:+.1f}%<extra></extra>"))
        fig.add_trace(go.Scatter(
            y=labels, x=sign * s.values, mode="markers", name=f"{start} level",
            marker=dict(symbol="line-ns", size=14, line=dict(width=2.5, color=COLORS["ink"])),
            showlegend=(sex == "F"), hoverinfo="skip"))
    m = float(p.groupby(["year", "sex"], observed=True)["licences"].max().max()) * 1.1
    ticks = np.linspace(0, m, 4)
    fig.update_layout(barmode="overlay", bargap=0.15)
    base(fig, f"Tennis licences by age and sex — {end} bars, {start} level as black ticks", height=520, legend=True)
    fig.update_xaxes(range=[-m, m], tickvals=list(-ticks[::-1]) + list(ticks[1:]),
                     ticktext=[f"{abs(v)/1000:.0f}k" for v in list(-ticks[::-1]) + list(ticks[1:])],
                     title="← Men · Women → (licences)", showgrid=True, gridcolor=COLORS["grid"])
    fig.update_yaxes(title="Age band (years)", showgrid=False)
    fig.add_vline(x=0, line=dict(color=COLORS["ink"], width=1))
    return fig


def age_growth_chart(g: pd.DataFrame, comparison_name: str | None) -> go.Figure:
    order = ["Children (1–14)", "Teens (15–19)", "Young adults (20–34)", "Adults (35–54)", "Seniors (55+)"]
    ticks = [o.replace(" (", "<br>(") for o in order]
    fig = go.Figure()
    for grp in [BENCH, TENNIS]:
        r = g[g["group"] == grp].set_index("age_group").reindex(order)
        fig.add_trace(go.Bar(
            x=ticks, y=r["growth"], name=grp, marker_color=color_for(grp),
            text=[f"{v:+.0f}%" for v in r["growth"]], textposition="outside", cliponaxis=False,
            customdata=np.stack([r["added"].fillna(0)], -1),
            hovertemplate=f"<b>{grp}</b><br>%{{x}}: %{{y:+.1f}}%<br>%{{customdata[0]:+,.0f}} licences<extra></extra>"))
    fig.add_hline(y=0, line=dict(color=COLORS["ink_secondary"], width=1))
    base(fig, "Growth by age group: tennis vs other single-sport federations", height=420, legend=True)
    fig.update_layout(barmode="group", bargap=0.3, bargroupgap=0.08)
    fig.update_yaxes(title="Change over the period (%)", ticksuffix="%")
    return fig


def women_chart(ws: dict[str, pd.Series]) -> go.Figure:
    fig = go.Figure()
    for g, s in ws.items():
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=g, mode="lines+markers",
                                 line=dict(color=color_for(g), width=3 if g == TENNIS else 2),
                                 hovertemplate=f"<b>{g}</b><br>%{{x}}: %{{y:.1f}}% women<extra></extra>"))
        fig.add_annotation(x=s.index[-1], y=s.values[-1], text=f"<b>{g}</b> {s.values[-1]:.1f}%", xanchor="left",
                           xshift=8, showarrow=False, font=dict(color=color_for(g), size=12))
    fig.add_hline(y=50, line=dict(color=COLORS["muted"], width=1), annotation_text="Parity (50%)",
                  annotation_position="bottom left", annotation_font=dict(size=11, color=COLORS["muted"]))
    years = list(next(iter(ws.values())).index)
    base(fig, "Women's share of licences", height=380)
    fig.update_xaxes(tickvals=years, range=[years[0] - 0.3, years[-1] + 1.4], title="Licence year")
    fig.update_yaxes(title="Women / (women + men)", ticksuffix="%", rangemode="tozero")
    return fig


# ------------------------------------------------------------------ section 4
def qpv_chart(per_fed: pd.DataFrame, bench_share: float, end: int, tennis_name: str,
              comparison_name: str | None) -> go.Figure:
    d = per_fed[per_fed["year"] == end].sort_values("share")
    cols = [COLORS["tennis"] if n == tennis_name else COLORS["comparison"] if n == comparison_name
            else COLORS["all_sports"] for n in d["name"]]
    fig = go.Figure(go.Bar(
        x=d["share"], y=d["name"], orientation="h", marker_color=cols,
        text=[f"{v:.1f}%" for v in d["share"]], textposition="outside", cliponaxis=False,
        customdata=np.stack([d["In QPV"], d["total"]], -1),
        hovertemplate="<b>%{y}</b><br>%{x:.2f}% of licences held by QPV residents"
                      "<br>%{customdata[0]:,.0f} of %{customdata[1]:,.0f}<extra></extra>"))
    fig.add_vline(x=bench_share, line=dict(color=COLORS["ink_secondary"], width=1.5),
                  annotation_text=f"All other single-sport federations: {bench_share:.1f}%",
                  annotation_position="bottom right", annotation_font=dict(size=11),
                  annotation_bgcolor="rgba(255,255,255,0.85)")
    base(fig, f"Share of licences held by residents of priority neighbourhoods (QPV), {end}",
         height=max(380, 24 * len(d) + 90))
    fig.update_xaxes(title="Share of licences (%)", ticksuffix="%", showgrid=True, gridcolor=COLORS["grid"])
    fig.update_yaxes(showgrid=False, tickfont=dict(size=11))
    return fig


def qpv_trend_chart(tennis: pd.Series, bench: pd.Series) -> go.Figure:
    fig = go.Figure()
    for g, s in [(BENCH, bench), (TENNIS, tennis)]:
        short = "Others" if g == BENCH else g
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=g, mode="lines+markers",
                                 line=dict(color=color_for(g), width=3 if g == TENNIS else 2),
                                 hovertemplate=f"<b>{g}</b><br>%{{x}}: %{{y:.2f}}%<extra></extra>"))
        fig.add_annotation(x=s.index[-1], y=s.values[-1], text=f"<b>{short}</b> {s.values[-1]:.1f}%", xanchor="left",
                           xshift=8, showarrow=False, font=dict(color=color_for(g), size=12))
    if 2023 in tennis.index and len(tennis) > 1:
        fig.add_vrect(x0=2022.5, x1=2023.5, fillcolor=COLORS["covid_band"], line_width=0, layer="below")
        fig.add_annotation(x=2023, y=1, yref="paper", yanchor="bottom", showarrow=False,
                           text="New QPV map (2024 list)", font=dict(size=11, color=COLORS["muted"]))
    base(fig, "QPV share over time", height=360)
    fig.update_xaxes(tickvals=list(tennis.index), range=[tennis.index[0] - 0.3, tennis.index[-1] + 1.2], title="Licence year")
    fig.update_yaxes(title="Share held by QPV residents", ticksuffix="%", rangemode="tozero")
    return fig


# ==================================================================
# Page building blocks: cached calls, section headers, insight boxes, accessible charts, KPI header
# ==================================================================
# Fingerprint of the calculation code: when prep.py changes (e.g. after a git push on Streamlit Cloud,
# where the process keeps running), cached results from the old code are no longer reused.
PREP_VERSION = hashlib.md5(Path(prep.__file__).read_bytes()).hexdigest()


@st.cache_data(show_spinner=False, max_entries=256)
def _cached(fn_name: str, version: str, _d: prep.Data, f: prep.Filters, *args):
    return getattr(prep, fn_name)(_d, f, *args)


def cached(fn_name: str, _d: prep.Data, f: prep.Filters, *args):
    """Memoise any analysis function on (code version, filters, args). `_d` is skipped from hashing:
    the processed data is immutable for the life of the process."""
    return _cached(fn_name, PREP_VERSION, _d, f, *args)


def inject_css() -> None:
    st.markdown(f"""
<style>
  .block-container {{ padding-top: 1.6rem; max-width: 1280px; }}
  .kicker {{ color: {COLORS['tennis']}; font-weight: 700; letter-spacing: .08em; text-transform: uppercase;
            font-size: .78rem; margin-bottom: -.4rem; }}
  .insight {{ border-left: 4px solid {COLORS['tennis']}; background: #fff7f2; padding: .8rem 1rem;
             border-radius: 0 6px 6px 0; margin: .4rem 0 1rem 0; font-size: 1.05rem; color: {COLORS['ink']}; }}
  .insight b {{ color: {COLORS['ink']}; }}
  .alt {{ color: {COLORS['ink_secondary']}; font-size: .82rem; margin-top: -.6rem; }}
  [data-testid="stMetricValue"] {{ font-size: 1.7rem; }}
  [data-testid="stMetricLabel"] p {{ font-size: .85rem; }}
</style>""", unsafe_allow_html=True)


def section(anchor: str, kicker: str, title: str, question: str | None = None) -> None:
    st.markdown(f'<div id="{anchor}"></div>', unsafe_allow_html=True)
    st.divider()
    st.markdown(f'<p class="kicker">{kicker}</p>', unsafe_allow_html=True)
    st.header(title, anchor=False)
    if question:
        st.markdown(f"*Question: {question}*")


def insight(html: str) -> None:
    """One headline sentence per section, computed from the filtered data."""
    st.markdown(f'<div class="insight">💡 {html}</div>', unsafe_allow_html=True)


def chart(fig, alt: str, table: pd.DataFrame | None = None, key: str | None = None) -> None:
    """Render a Plotly chart with a text description (alt text) and an optional data-table view."""
    st.plotly_chart(fig, config=CONFIG, key=key)  # full width by default
    st.markdown(f'<p class="alt" role="note"><b>Chart description:</b> {alt}</p>', unsafe_allow_html=True)
    if table is not None:
        table = table.copy()
        table.columns = [" ".join(map(str, c)).strip() if isinstance(c, tuple) else str(c) for c in table.columns]
        with st.expander("Show the data behind this chart"):
            st.dataframe(table, width="stretch", hide_index=True)


def fmt_pct(v: float, signed: bool = True) -> str:
    return "n/a" if pd.isna(v) else (f"{v:+.1f}%" if signed else f"{v:.1f}%")


def kpi_header(d: prep.Data, f: prep.Filters) -> None:
    k = cached("kpis", d, f)
    sex = {"All": "", "F": " (women)", "H": " (men)"}[f.sex]
    c = st.columns(5)
    c[0].metric(f"Tennis licences {f.end}{sex}", f"{k['tennis_end']:,.0f}",
                f"{k['tennis_growth']:+.1f}% vs {f.start}",
                help="FFT licences held by residents of the selected area (place of residence, not of play).")
    c[1].metric("Gap vs other single-sport", f"{k['gap_pp']:+.1f} pp",
                f"others: {k['bench_growth']:+.1f}%", delta_color="off",
                help="Tennis growth minus the growth of all other single-sport federations combined, "
                     "same filters, same period. pp = percentage points.")
    c[2].metric(f"Worst year vs {f.start}", fmt_pct(k["trough_drop"]),
                f"others: {fmt_pct(k['bench_trough_drop'])}", delta_color="off",
                help="Largest drop below the start-year level within the period (the COVID trough if 2020–21 "
                     "is included).")
    c[3].metric(f"Per 1,000 residents{sex}", f"{k['per1000_end']:.1f}",
                f"{k['per1000_end'] - k['per1000_start']:+.1f} vs {f.start}",
                help="Licences ÷ legal population (all ages and sexes) × 1,000. Population for 2022–23 uses "
                     "the latest available year, 2021.")
    c[4].metric(f"Women's share {f.end}", fmt_pct(k["women_end"], signed=False),
                f"{k['women_delta']:+.1f} pp vs {f.start}",
                help="Women ÷ (women + men) among tennis licences, ignoring the sex filter.")
    st.caption(f"Scope: **{f.scope_label}** · {f.span} · ages: "
               f"{'all' if set(f.ages) == set(prep.ALL_GROUPS) else ', '.join(f.ages)}")
