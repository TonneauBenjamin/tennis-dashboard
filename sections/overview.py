"""Section 2 — Where: geography of tennis density, growth and gender balance."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils import prep as A
from utils import viz
from utils.viz import cached, chart, insight, section

METRIC_OPTIONS = {"per1000": "Licences per 1,000 residents", "growth": "Growth over the period",
                  "women_share": "Women's share"}


def _average(dep: pd.DataFrame, metric: str) -> float:
    s = dep[dep["selected"]]
    if metric == "per1000":
        return s["licences_end"].sum() / s["population"].sum() * 1000
    if metric == "growth":
        return (s["licences_end"].sum() / s["licences_start"].sum() - 1) * 100
    return float((s["women_share"] * s["licences_end"]).sum() / s["licences_end"].sum())


def render(d: A.Data, f: A.Filters, geo: dict, metric: str) -> None:
    section("where", "2 · Where", "Where tennis is played, and where it grew",
            "Where is tennis played most, and where did it grow?")
    dep = cached("by_department", d, f)
    sel = dep[dep["selected"]].dropna(subset=["per1000"])
    avg = _average(dep, metric)

    top_d = sel.nlargest(3, "per1000")
    low_d = sel.nsmallest(3, "per1000")
    grow = sel.nlargest(3, "growth")
    shrink = sel.nsmallest(1, "growth").iloc[0]
    if len(sel) >= 6:
        ratio = top_d["per1000"].iloc[0] / low_d["per1000"].iloc[0]
        insight(
            f"Density varies <b>{ratio:.1f}×</b> across départements: from "
            f"{', '.join(f'{r.dep_name} ({r.per1000:.1f})' for r in top_d.itertuples())} licences per 1,000 "
            f"residents down to {', '.join(f'{r.dep_name} ({r.per1000:.1f})' for r in low_d.itertuples())}. "
            f"The fastest growth over {f.span} was in "
            f"{', '.join(f'{r.dep_name} ({r.growth:+.0f}%)' for r in grow.itertuples())}; "
            f"{shrink.dep_name} declined most ({shrink.growth:+.0f}%).")
    else:
        insight("Select at least six départements (or a whole region) to compare geography meaningfully.")

    c1, c2 = st.columns([1.25, 1])
    with c1:
        chart(viz.choropleth(dep, geo, metric, avg),
              alt=(f"Map of France by département showing {METRIC_OPTIONS[metric].lower()} for tennis, "
                   f"{f.end}. Darker = higher"
                   + (" (blue = growth, red = decline, grey = stable)" if metric == "growth" else "")
                   + f". Selection average: {avg:.1f}. Départements outside the selection are light grey."),
              key="map")
    with c2:
        chart(viz.ranking_chart(dep, metric, avg),
              alt=(f"Horizontal bar chart of the top and bottom 10 selected départements by "
                   f"{METRIC_OPTIONS[metric].lower()}, with the selection average as a vertical line."),
              table=sel[["dep", "dep_name", "region", "licences_start", "licences_end", "population",
                         "per1000", "growth", "women_share"]].round(1).sort_values(metric, ascending=False)
                       .rename(columns={"dep": "Code", "dep_name": "Département", "region": "Region",
                                        "licences_start": f"Licences {f.start}", "licences_end": f"Licences {f.end}",
                                        "population": "Population", "per1000": "Per 1,000",
                                        "growth": "Growth %", "women_share": "Women %"}),
              key="rank")

    with st.expander("Method: how density and growth are computed"):
        st.markdown(
            "- **Licences per 1,000 residents** = tennis licences of residents of the département ÷ legal "
            "municipal population × 1,000. Licences are counted where the player *lives*, not where they play.\n"
            "- Population: INSEE *populations légales* of the same year up to 2021; 2022–2023 use 2021 "
            "(population grows ~0.3%/year, so rates for those two years are overstated by under 1%).\n"
            "- With a sex or age filter, the numerator is restricted but the denominator stays the whole "
            "population; read the rate as *licences of that group per 1,000 residents*.\n"
            "- A licence is not a player: some people hold none (casual play), a few hold two.")

    st.subheader("Drill down: the leading communes of a département", anchor=False)
    options = sel.sort_values("licences_end", ascending=False)
    if options.empty:
        return
    labels = {r.dep: f"{r.dep_name} ({r.dep})" for r in options.itertuples()}
    pick = st.selectbox("Département", list(labels), format_func=labels.get, key="commune_dep",
                        help="Ordered by number of tennis licences.")
    com = cached("communes", d, f, pick, 15)
    st.dataframe(
        com.rename(columns={"commune_code": "Code", "commune": "Commune", f.start: f"Licences {f.start}",
                            f.end: f"Licences {f.end}", "growth": "Growth %", "women_share": "Women %"}),
        hide_index=True, width="stretch",
        column_config={
            f"Licences {f.end}": st.column_config.ProgressColumn(
                f"Licences {f.end}", format="%d", min_value=0, max_value=int(com[f.end].max() or 1)),
            "Growth %": st.column_config.NumberColumn(format="%+.1f%%"),
            "Women %": st.column_config.NumberColumn(format="%.1f%%"),
            f"Licences {f.start}": st.column_config.NumberColumn(format="%d")})
    st.caption("Commune figures are INSEE estimates allocated from geocoded addresses; all ages and sexes. "
               "Paris, Lyon and Marseille appear by arrondissement.")
