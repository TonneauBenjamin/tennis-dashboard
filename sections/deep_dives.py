"""Sections 3 & 4 — Who plays (age, sex) and who is missing (priority neighbourhoods)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils import prep as A
from utils import viz
from utils.io import AGE_GROUPS, SEEDS
from utils.viz import cached, chart, insight, section


def render_who(d: A.Data, f: A.Filters) -> None:
    section("who", "3 · Who", "The new players are young adults",
            "Which age groups drove the growth, and did the gender gap close?")
    g = cached("growth_by_age", d, f)
    t = g[g["group"] == A.TENNIS].set_index("age_group")
    b = g[g["group"] == A.BENCH].set_index("age_group")
    top = t["growth"].idxmax()
    share_added = t.loc[top, "added"] / t["added"].sum() * 100 if t["added"].sum() > 0 else float("nan")
    base_share = t.loc[top, f.start] / t[f.start].sum() * 100
    insight(f"<b>{top}</b> grew <b>{t.loc[top, 'growth']:+.0f}%</b> in tennis over {f.span}, against "
            f"{b.loc[top, 'growth']:+.0f}% in other single-sport federations. They were {base_share:.0f}% of "
            f"tennis licences in {f.start} but brought "
            + (f"<b>{share_added:.0f}%</b> of the net new licences." if share_added == share_added else
               "no net growth.")
            + " Children remain the base of the sport, but no longer its engine.")

    c1, c2 = st.columns([1.1, 1])
    highlight = {band for grp in f.ages for band in AGE_GROUPS[grp]}
    with c1:
        p = cached("pyramid", d, f)
        chart(viz.pyramid_chart(p, f.start, f.end, highlight),
              alt=(f"Population pyramid of tennis licences by 5-year age band, men on the left, women on the "
                   f"right, {f.end} as bars and {f.start} as black ticks. The largest bands are ages 5–14; "
                   f"the 20–34 bands extend furthest beyond their {f.start} ticks. Age groups not selected in "
                   f"the sidebar are faded."),
              table=p.pivot_table(index="age_band", columns=["sex", "year"], values="licences", observed=True)
                     .reindex(SEEDS["age_bands"]).reset_index(), key="pyramid")
    with c2:
        chart(viz.age_growth_chart(g, None),
              alt=("Grouped bar chart of growth by age group, tennis (orange) versus other single-sport "
                   f"federations (grey). Tennis grows most among {top.lower()} ({t.loc[top, 'growth']:+.0f}%)."),
              table=g.round(1), key="agegrowth")

    st.subheader("The gender gap did not move", anchor=False)
    comp = d.fed_name(f.comparison)
    ws = {A.BENCH: cached("women_share", d, f, "bench"),
          comp: cached("women_share", d, f, f.comparison),
          A.TENNIS: cached("women_share", d, f, "tennis")}
    wt, wb = ws[A.TENNIS], ws[A.BENCH]
    insight(f"Women held <b>{wt.iloc[-1]:.1f}%</b> of tennis licences in {f.end} "
            f"({wt.iloc[-1] - wt.iloc[0]:+.1f} points since {f.start}), against {wb.iloc[-1]:.1f}% in other "
            f"single-sport federations. Growth brought in more women in absolute terms but did not change "
            f"the balance: roughly <b>{(100 - wt.iloc[-1]) / wt.iloc[-1]:.1f} men for every woman</b>.")
    ya = "Young adults (20–34)"
    if ya in f.ages:
        wya = cached("women_share", d, A.Filters(f.start, f.end, f.deps, "All", (ya,), f.comparison,
                                                 f.scope_label), "tennis")
        if wya.notna().all():
            st.markdown(f"Among **young adults**, the fastest-growing group, women's share went from "
                        f"**{wya.iloc[0]:.1f}%** to **{wya.iloc[-1]:.1f}%**: the boom was "
                        f"{'male-skewed' if wya.iloc[-1] < wya.iloc[0] else 'not male-skewed'}. "
                        "This fits the padel hypothesis, but the data cannot confirm it.")
    chart(viz.women_chart(ws),
          alt=(f"Line chart of women's share of licences, {f.span}: tennis about {wt.iloc[-1]:.0f}%, other "
               f"single-sport federations about {wb.iloc[-1]:.0f}%, {comp} {ws[comp].iloc[-1]:.0f}%; "
               "a reference line marks parity at 50%."),
          table=pd.DataFrame(ws).round(2).reset_index().rename(columns={"index": "year"}), key="women")
    st.caption("Women's share = women ÷ (women + men); licences with unknown sex (0.02% for tennis, 2.8% for "
               "all sports in 2019 only) are excluded. The age filter applies; the sex filter does not.")


def render_missing(d: A.Data, f: A.Filters) -> None:
    section("missing", "4 · Who is missing", "Priority neighbourhoods are left behind",
            "Do residents of deprived urban areas (QPV) take part in tennis as much as in other sports?")
    per_fed, bench = cached("qpv_shares", d, f, SEEDS["min_federation_size_for_comparison"])
    tennis_name, comp = d.fed_name(d.tennis_key), d.fed_name(f.comparison)
    tq = per_fed[per_fed["name"] == tennis_name].set_index("year")["share"]
    bq = bench.set_index("year")["share"]
    if tq.empty or f.end not in tq.index or tq.loc[f.end] == 0 or bq.get(f.end, 0) == 0:
        insight("No QPV residents hold tennis licences in this selection (many rural départements have no QPV).")
        return
    end_rank = per_fed[per_fed["year"] == f.end].sort_values("share")
    pos = list(end_rank["name"]).index(tennis_name) + 1
    insight(f"Residents of priority neighbourhoods hold <b>{tq.iloc[-1]:.1f}%</b> of tennis licences, "
            f"<b>{bq.iloc[-1] / tq.iloc[-1]:.1f}× less</b> than their {bq.iloc[-1]:.1f}% share in other "
            f"single-sport federations. Tennis ranks <b>{pos} of {len(end_rank)}</b> large federations on this "
            "measure (1 = least inclusive): the post-COVID boom did not reach these areas proportionally.")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        chart(viz.qpv_chart(per_fed, bq.iloc[-1], f.end, tennis_name, comp),
              alt=(f"Horizontal bar chart of the share of licences held by QPV residents in {f.end}, for each "
                   f"single-sport federation with at least {SEEDS['min_federation_size_for_comparison']:,} "
                   f"licences nationally. Tennis (orange) is at {tq.iloc[-1]:.1f}%; the benchmark line is at "
                   f"{bq.iloc[-1]:.1f}%."),
              table=end_rank[["name", "In QPV", "total", "share"]].round(2).sort_values("share")
                    .rename(columns={"name": "Federation", "In QPV": "QPV licences", "total": "All allocated",
                                     "share": "QPV share %"}), key="qpv")
    with c2:
        chart(viz.qpv_trend_chart(tq, bq),
              alt=(f"Line chart of the QPV share of licences over {f.span}: tennis from {tq.iloc[0]:.1f}% to "
                   f"{tq.iloc[-1]:.1f}%, other single-sport federations from {bq.iloc[0]:.1f}% to "
                   f"{bq.iloc[-1]:.1f}%. The 2023 point uses the new QPV map."), key="qpvtrend")
    with st.expander("What is a QPV, and why the 2023 break?"):
        st.markdown(
            "A *quartier prioritaire de la politique de la ville* (QPV) is an officially designated low-income "
            "urban neighbourhood. INSEE flags each geocoded licence as inside or outside a QPV. "
            "Licences that could not be placed at that level ('non réparti') are excluded from both numerator "
            "and denominator. **The 2023 file uses the new QPV list (codes `QN…`), which covers more areas** — "
            "part of the 2023 rise for every sport is a definitional change, so compare sports *within* a year "
            "rather than reading the 2022→2023 step as progress. The data has no income variable: this is a "
            "neighbourhood-level proxy for social background, not an individual one.")
