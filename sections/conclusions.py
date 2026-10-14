"""Section 5 — So what? Implications, limitations, next steps; then the data-quality appendix."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import prep as A
from utils import viz
from utils.io import COLORS, SEEDS
from utils.viz import cached, chart, section


def render(d: A.Data, f: A.Filters) -> None:
    section("so-what", "5 · So what?", "Three implications for clubs and policymakers")
    k = cached("kpis", d, f)
    g = cached("growth_by_age", d, f)
    t = g[g["group"] == A.TENNIS].set_index("age_group")
    ya = "Young adults (20–34)"
    per_fed, bench = cached("qpv_shares", d, f, SEEDS["min_federation_size_for_comparison"])
    tq = per_fed[(per_fed["name"] == d.fed_name(d.tennis_key)) & (per_fed["year"] == f.end)]["share"]
    bq = bench.loc[bench["year"] == f.end, "share"]
    qtxt = (f"{tq.iloc[0]:.1f}% vs {bq.iloc[0]:.1f}%" if len(tq) and len(bq) else "see section 4")

    c = st.columns(3)
    with c[0]:
        st.markdown("##### 1 · Plan capacity for adults, not just juniors")
        st.markdown(
            f"Young adults grew **{t.loc[ya, 'growth']:+.0f}%** ({t.loc[ya, 'added']:+,.0f} licences) over "
            f"{f.span}. These players want evening and weekend slots, short formats and (probably) padel. "
            "Court-hour availability at peak times, not total court count, is the likely bottleneck.")
    with c[1]:
        st.markdown("##### 2 · The growth is real but uneven")
        st.markdown(
            f"Tennis grew **{k['tennis_growth']:+.1f}%** against **{k['bench_growth']:+.1f}%** for other "
            "single-sport federations, but some départements shrank. Investment should follow per-capita "
            "demand and growth (section 2), not historical club size.")
    with c[2]:
        st.markdown("##### 3 · The boom skipped two groups")
        st.markdown(
            f"Women's share stayed at **{k['women_end']:.0f}%**, and priority neighbourhoods remain "
            f"under-represented ({qtxt}). Targeted offers (women-only sessions, free school-to-club "
            "pathways, courts in QPV) are where the next growth could come from.")

    st.markdown("#### Limitations — read before quoting a number")
    st.markdown(
        "- **Licences ≠ players.** Casual players without a licence are invisible; a licence is counted once "
        "per season even if the holder barely plays.\n"
        "- **Padel is inside tennis.** The FFT governs padel; the census does not split the two, so part of the "
        "young-adult growth may be padel. This is a hypothesis the data cannot test.\n"
        "- **Residence, not practice.** Licences are geocoded at the holder's address. Commune values are "
        "INSEE *estimates*.\n"
        "- **Seasons.** Licence year N = FFT season N-1/N (September–August). COVID closures hit parts of the "
        "2020 and 2021 seasons.\n"
        "- **Breaks in series.** Federations re-coded between years are matched by name; the QPV map changed in "
        "2023; earlier years (pre-2019) use a different format and are excluded. INJEP warns that later "
        "revisions are not back-propagated into the detailed files.\n"
        "- **No causality.** The charts show co-movement and differences; they do not identify why tennis grew.")

    st.markdown("#### Next steps")
    st.markdown(
        "1. Add the **2024 census** when INJEP publishes it, to test for a Paris-2024 Olympic effect.\n"
        "2. Join the **Data ES sports-facilities census** (courts per département) to compare demand with supply.\n"
        "3. Ask the FFT for a **tennis/padel split** of licences to test the padel hypothesis.\n"
        "4. Replace the QPV proxy with **commune median income** (INSEE Filosofi) to measure the social gradient "
        "directly.")


def render_data_quality(d: A.Data, f: A.Filters, q: dict) -> None:
    section("data-quality", "Appendix", "Data quality, validation & methods",
            "Can these numbers be trusted, and what was done to them?")
    yrs = pd.DataFrame(q["years"]).set_index("year")
    all_ok = (yrs["non_numeric_cells"].sum() == 0 and yrs["negative_cells"].sum() == 0
              and yrs["rows_where_sex_age_sum_differs_from_total"].sum() == 0 and yrs["duplicate_keys"].sum() == 0
              and all(c["consistent"] for c in q["cross_checks"]))
    (st.success if all_ok else st.error)(
        "All automated checks pass: counts are numeric and non-negative, sex × age columns add up to the total on "
        "every row, keys are unique, and tennis totals are identical across the four derived tables."
        if all_ok else "At least one automated check failed — see the table below.")

    c = st.columns(4)
    c[0].metric("Raw rows read (5 years)", f"{yrs['rows'].sum():,}")
    c[1].metric("Tennis rows", f"{yrs['tennis_rows'].sum():,}")
    c[2].metric("Outside geocoded scope (all sports)", f"{yrs['share_out_of_scope_pct'].mean():.1f}%",
                help="Mayotte, overseas collectivities, Monaco and abroad. Excluded from all maps and rates.")
    c[3].metric("Processed data shipped", f"{sum(q['processed_bytes'].values()) / 1e6:.1f} MB",
                help="vs ~1.2 GB of raw CSV, which the build script downloads and caches.")

    st.markdown("##### Validation checks, by file")
    checks = pd.DataFrame({
        "Rows": yrs["rows"],
        "Columns": yrs["columns"],
        "Non-numeric counts": yrs["non_numeric_cells"],
        "Negative counts": yrs["negative_cells"],
        "Rows: sex×age ≠ total": yrs["rows_where_sex_age_sum_differs_from_total"],
        "Duplicate keys": yrs["duplicate_keys"],
        "Naive duplicates*": yrs["naive_duplicates_commune_qpv_only"],
        "Unknown sex (all sports)": yrs["licences_unknown_sex"],
        "Unknown age (all sports)": yrs["licences_unknown_age"],
        "Out-of-scope %": yrs["share_out_of_scope_pct"],
        "Tennis licences": yrs["tennis_licences"],
    })
    st.dataframe(checks, width="stretch")
    st.caption("*Keying rows on commune + QPV + federation alone suggests ~600–800 duplicates per year; they are "
               "the out-of-scope 'non réparti' rows, one per overseas territory. With the département in the key "
               "(the correct key) there are **0** duplicates. Column counts differ because 2019–2021 carry extra "
               "'unknown sex' columns, harmonised into a single *Unknown* category.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### Missing values in identifier columns")
        miss = pd.DataFrame({y["year"]: y["missing_values"] for y in q["years"]})
        miss = miss[miss.sum(axis=1) > 0]
        st.dataframe(miss, width="stretch")
        st.caption("`Commune` is empty only on 'non réparti' rows (licences not allocated to a commune); "
                   "`Nom QPV` is empty by design outside priority neighbourhoods. No count is missing.")
    with c2:
        sc = d.scope.copy()
        sc = sc[sc["fed_key"].astype(str) == d.tennis_key]
        sc = sc.pivot_table(index="year", columns="status", values="licences", observed=True)
        fig = go.Figure()
        for col, colr, name in [(sc.columns[0], COLORS["tennis"], "Geocoded (in scope)"),
                                (sc.columns[-1], COLORS["all_sports"], "Out of scope")]:
            fig.add_trace(go.Bar(x=sc.index, y=sc[col], name=name, marker_color=colr,
                                 hovertemplate=f"{name}<br>%{{x}}: %{{y:,.0f}}<extra></extra>"))
        viz.base(fig, "Tennis licences by geocoding status", height=300, legend=True)
        fig.update_layout(barmode="stack", bargap=0.35)
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(title="Licences")
        chart(fig, alt="Stacked bars per year: almost all tennis licences are geocoded; about 1% are out of scope.",
              table=sc.reset_index(), key="scope")

    st.markdown("##### Cross-table consistency (tennis, in scope)")
    st.dataframe(pd.DataFrame(q["cross_checks"]).set_index("year"), width="stretch")

    with st.expander("Pipeline & decisions (feature engineering)"):
        st.markdown(f"""
1. **Download & cache** the five yearly files (`download_data.py`, sizes verified against data.gouv metadata).
2. **Type & validate**: identifiers kept as text (leading zeros, `2A/2B`), counts coerced to integers with
   non-numeric and negative cells counted, row sums checked, keys tested for uniqueness.
3. **Scope**: keep `Statut géo = 1.Champ geoc` (mainland + Guadeloupe, Martinique, Guyane, La Réunion).
4. **Harmonise** sex × age columns across years: 17 five-year bands × {{women, men, unknown}}, grouped into
   5 age groups for filtering.
5. **Stable federation key** from the normalised name, because INJEP re-coded
   {len(q['federations_recoded_between_years'])} federations between years
   ({', '.join(q['federations_recoded_between_years'])}).
6. **Benchmark** = all single-sport federations (codes 1xx and 2xx) except tennis.
7. **QPV flag** from `Code QPV` (`QP…`/`QN…` = inside; `CSZ`/`HZ` = outside; `NR` = unallocated, excluded).
8. **Join population** (INSEE legal population, département sum of communes; 2022–23 → 2021).
9. **Pre-aggregate** to département × federation × sex × age group (~400k rows) so every filter runs in
   milliseconds; tennis keeps 5-year bands and commune detail.
10. **Geometry**: IGN département shapes simplified (tolerance 0.01°), overseas départements moved into
    insets west of the mainland.
""")
    with st.expander("Sources & licences"):
        s = SEEDS["sources"]
        st.markdown("\n".join(
            f"- **{v['producer']}** — [{v['dataset_page']}]({v['dataset_page']}) — {v['license']}"
            for v in s.values()))
        st.markdown("Reuse under Licence Ouverte 2.0 requires attribution of the source and the date of last "
                    "update: *INJEP–MEDES, Recensement des licences et clubs sportifs, données géocodées "
                    "2019–2023 (mise à jour 29/12/2025)*. This dashboard aggregates counts; no individual-level "
                    "data exists in the source or is shown here.")
