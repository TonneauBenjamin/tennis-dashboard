"""Section 1 — Hook & context: tennis came through COVID almost untouched, then grew."""
from __future__ import annotations

import streamlit as st

from utils import prep as A
from utils import viz
from utils.io import SEEDS
from utils.viz import cached, chart, insight, section


def render_header(f: A.Filters) -> None:
    st.markdown('<p class="kicker">French open data · sports licences</p>', unsafe_allow_html=True)
    st.title("The Resilient Racket", anchor=False)
    st.markdown(
        "#### COVID-19 emptied French sports clubs. Tennis barely noticed — and came out bigger. "
        "Who joined, where, and who is still missing?")
    st.markdown(
        "**Audience:** the French Tennis Federation (FFT), its regional leagues, and the local authorities "
        "that fund courts.  \n"
        "**Data:** every annual licence of every approved sports federation, by commune of residence, "
        "sex and age (INJEP census, 2019–2023, ~1 million rows per year).  \n"
        "Use the sidebar to change the period, the area, the sex and age groups, and the sport tennis "
        "is compared with. Every number and headline below updates.")


def render(d: A.Data, f: A.Filters) -> None:
    section("hook", "1 · Hook", "Tennis held its ground while sport collapsed",
            "How did tennis fare through COVID compared with other sports?")

    s = cached("series", d, f)
    idx = A.indexed(s)
    k = cached("kpis", d, f)
    comp = d.fed_name(f.comparison)

    trough_txt = (f"At its worst point ({k['trough_year']}), tennis was <b>{k['trough_drop']:+.1f}%</b> below "
                  f"{f.start}, against <b>{k['bench_trough_drop']:+.1f}%</b> for other single-sport federations. "
                  if k["trough_drop"] < 0 else
                  f"Tennis never fell below its {f.start} level in this period. ")
    insight(f"{trough_txt}By {f.end}, tennis had grown <b>{k['tennis_growth']:+.1f}%</b>, "
            f"{abs(k['gap_pp']):.1f} points {'faster' if k['gap_pp'] >= 0 else 'slower'} than the "
            f"other single-sport federations ({k['bench_growth']:+.1f}%).")

    chart(viz.index_chart(idx, s, f.start),
          alt=(f"Line chart of licences indexed to {f.start} = 100 for tennis, {comp} and all other single-sport "
               f"federations, {f.span}, {f.scope_label}. A grey band marks the COVID-19 seasons (2020–2021). "
               f"Tennis ends at {idx[A.TENNIS].iloc[-1]:.0f}, others at {idx[A.BENCH].iloc[-1]:.0f}, "
               f"{comp} at {idx[comp].iloc[-1]:.0f}." if comp in idx else ""),
          table=s.reset_index().rename(columns={"year": "Licence year"}), key="index")

    with st.expander("Why compare with *other single-sport federations* rather than *all sports*?"):
        st.markdown(
            "The census also counts school sport (UNSS, USEP, UGSEL) and multi-sport federations. Their licences "
            "are often compulsory or bundled with school, and they fell 30–40% in 2021, which would make any "
            "club sport look resilient. The benchmark here is the **sum of all other single-sport federations** "
            "(Olympic and non-Olympic, tennis excluded), always with the same filters as tennis. "
            "The sport chosen in the sidebar is shown on its own line *and* stays inside that sum.")

    st.subheader("Was tennis special, or were other sports spared too?", anchor=False)
    p = cached("peers", d, f, SEEDS["min_federation_size_for_comparison"] // 2)
    tennis_name = d.fed_name(d.tennis_key)
    if tennis_name not in set(p["name"]) or len(p) < 5:
        insight("Too few licences in this selection to compare federations reliably — widen the area or period.")
        return
    rank_worst = int((p["worst"] > p.loc[p["name"] == tennis_name, "worst"].iloc[0]).sum()) + 1
    rank_growth = int((p["growth"] > p.loc[p["name"] == tennis_name, "growth"].iloc[0]).sum()) + 1
    better = p[p["worst"] > p.loc[p["name"] == tennis_name, "worst"].iloc[0]]["name"].tolist()
    insight(f"Among the {len(p)} largest single-sport federations (≥"
            f"{SEEDS['min_federation_size_for_comparison'] // 2:,} licences nationally in 2019), tennis ranks <b>#{rank_worst}</b> for "
            f"resilience and <b>#{rank_growth}</b> for growth. "
            + (f"Only {', '.join(better[:4])}{' and others' if len(better) > 4 else ''} held up better."
               if better else "No large federation held up better."))
    chart(viz.peers_chart(p, tennis_name, comp),
          alt=("Scatter plot: each bubble is a single-sport federation; x = worst year versus start year (%), "
               "y = end year versus start year (%), bubble size = licences at start. Tennis is orange, the "
               f"comparison sport blue. Tennis sits at x={p.loc[p['name'] == tennis_name, 'worst'].iloc[0]:.1f}%, "
               f"y={p.loc[p['name'] == tennis_name, 'growth'].iloc[0]:.1f}%."),
          table=p[["name", "start", "end", "worst", "growth"]].round(1).rename(columns={
              "name": "Federation", "start": f"Licences {f.start}", "end": f"Licences {f.end}",
              "worst": "Worst year vs start (%)", "growth": "End vs start (%)"}), key="peers")
    st.caption("Correlation is not causation: the data shows *when* licences moved, not *why*. Plausible drivers "
               "(outdoor play allowed earlier in lockdown, padel joining the FFT, post-COVID demand for individual "
               "sport) are hypotheses, not findings.")
