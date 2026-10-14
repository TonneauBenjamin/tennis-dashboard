"""The Resilient Racket — a data story on French tennis licences, 2019–2023.

Run:  streamlit run app.py
Data: INJEP geocoded licence census (data.gouv.fr), see README.md.
"""
from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="The Resilient Racket · French tennis 2019–2023", page_icon="🎾",
                   layout="wide", initial_sidebar_state="expanded")

from sections import conclusions, deep_dives, intro, overview  # noqa: E402
from utils import prep as A  # noqa: E402
from utils import io  # noqa: E402
from utils.io import AGE_GROUPS, SEEDS, SEX_LABELS, YEARS  # noqa: E402
from utils.viz import kpi_header, inject_css  # noqa: E402

inject_css()


# ------------------------------------------------------------------ data (cached once per process)
@st.cache_data(show_spinner="Loading processed data…")
def load_tables() -> dict:
    return {name: io.read_processed(name) for name in
            ["fed_long", "fed_qpv", "tennis_age", "tennis_commune", "scope", "federations",
             "departments", "population"]}


@st.cache_data
def load_geo() -> dict:
    return io.read_geojson()


@st.cache_data
def load_quality() -> dict:
    return io.read_quality()


if not io.processed_ready():
    st.error("Processed data not found. Run `python download_data.py` first — see README.")
    st.stop()

D = A.Data(**load_tables())
GEO = load_geo()
QUALITY = load_quality()


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown("### 🎾 The Resilient Racket")
    st.caption("French tennis licences, 2019–2023 · INJEP open data")

    start, end = st.select_slider("Period (licence year)", options=YEARS, value=(YEARS[0], YEARS[-1]),
                                  help="Licence year N = season N-1/N for the FFT (e.g. 2021 = 2020/21 season). "
                                       "Growth and indices compare the last year with the first.")
    if start == end:
        st.warning("Pick at least two years — showing the previous year as start.")
        start = YEARS[max(0, YEARS.index(end) - 1)]
        if start == end:
            end = YEARS[1]

    deps = D.departments.sort_values("dep")
    regions = sorted(deps["region"].unique())
    sel_regions = st.multiselect("Region", regions, placeholder="All of France",
                                 help="Leave empty for all of France (mainland + 4 overseas départements; "
                                      "Mayotte is outside the geocoded scope).")
    pool = deps[deps["region"].isin(sel_regions)] if sel_regions else deps
    dep_labels = {r.dep: f"{r.dep_name} ({r.dep})" for r in pool.itertuples()}
    sel_deps = st.multiselect("Département", list(dep_labels), format_func=dep_labels.get,
                              placeholder="All in selected region(s)")
    dep_codes = tuple(sel_deps) if sel_deps else tuple(pool["dep"])
    scope_label = ("France" if not sel_regions and not sel_deps else
                   ", ".join(dep_labels[d] for d in sel_deps) if 0 < len(sel_deps) <= 2 else
                   f"{len(sel_deps)} départements" if sel_deps else
                   ", ".join(sel_regions) if len(sel_regions) <= 2 else f"{len(sel_regions)} regions")

    sex = st.radio("Sex", ["All", "F", "H"], format_func=lambda s: {"All": "All", **SEX_LABELS}[s],
                   horizontal=True, help="Applies to counts, growth and per-capita rates. "
                                         "Women's-share views always use both sexes.")
    ages = st.multiselect("Age groups", list(AGE_GROUPS), default=list(AGE_GROUPS),
                          help="Age at licence date, grouped from INJEP's 5-year bands.")
    if not ages:
        st.warning("No age group selected — showing all ages.")
        ages = list(AGE_GROUPS)

    feds = D.federations
    min_size = SEEDS["min_federation_size_for_comparison"]
    choices = feds[feds["single_sport"] & (feds["code"] != SEEDS["tennis_code"]) & (feds["2019"] >= min_size)]
    choices = choices.sort_values("2019", ascending=False)
    comp_keys = list(choices["fed_key"])
    default_comp = feds.loc[feds["code"] == SEEDS["default_comparison_code"], "fed_key"].iloc[0]
    comparison = st.selectbox("Compare tennis with…", comp_keys, index=comp_keys.index(default_comp),
                              format_func=D.fed_name,
                              help=f"Single-sport federations with ≥{min_size:,} licences in 2019.")

    metric = st.radio("Map variable", list(overview.METRIC_OPTIONS), format_func=overview.METRIC_OPTIONS.get,
                      help="Variable shown on the map and in the ranking (section 2).")

    st.divider()
    st.markdown("**Story**  \n[1 · Hook](#hook) · [2 · Where](#where) · [3 · Who](#who)  \n"
                "[4 · Who is missing](#missing) · [5 · So what?](#so-what) · [Data quality](#data-quality)")
    st.caption("Source: INJEP–MEDES licence census, geocoded by INSEE · Licence Ouverte 2.0. "
               "Population: INSEE populations légales.")

F = A.Filters(start=start, end=end, deps=dep_codes, sex=sex, ages=tuple(ages),
              comparison=comparison, scope_label=scope_label)

# ------------------------------------------------------------------ story
intro.render_header(F)
kpi_header(D, F)
intro.render(D, F)
overview.render(D, F, GEO, metric)
deep_dives.render_who(D, F)
deep_dives.render_missing(D, F)
conclusions.render(D, F)
conclusions.render_data_quality(D, F, QUALITY)
