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
from utils.io import AGE_GROUPS, SEEDS, YEARS  # noqa: E402
from utils.viz import inject_css, kpi_header, label, sidebar_credits, tr  # noqa: E402

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
    st.error("Processed data not found. Run `python download_data.py` first — see README. / Données traitées introuvables : lancez `python download_data.py` (voir README).")
    st.stop()

D = A.Data(**load_tables())
GEO = load_geo()
QUALITY = load_quality()


# ------------------------------------------------------------------ sidebar
# Widget labels change with the language, and Streamlit treats a relabelled widget as a new one.
# Each choice is therefore remembered in session state and passed back as the widget's default,
# so switching English <-> Français keeps every filter as it was.
def mem(name: str, default):
    return st.session_state.get(f"_mem_{name}", default)


def keep(name: str, value):
    st.session_state[f"_mem_{name}"] = value
    return value


with st.sidebar:
    sidebar_credits()
    st.radio("Language / Langue", ["en", "fr"], key="lang", horizontal=True,
             format_func={"en": "🇬🇧 English", "fr": "🇫🇷 Français"}.get)
    st.divider()
    st.markdown("### 🎾 The Resilient Racket")
    st.caption(tr("French tennis licences, 2019–2023 · INJEP open data",
                  "Licences de tennis en France, 2019–2023 · open data INJEP"))

    start, end = keep("period", st.select_slider(
        tr("Period (licence year)", "Période (année de licence)"), options=YEARS,
        value=mem("period", (YEARS[0], YEARS[-1])),
        help=tr("Licence year N = season N-1/N for the FFT (e.g. 2021 = 2020/21 season). "
                "Growth and indices compare the last year with the first.",
                "Année de licence N = saison N-1/N pour la FFT (ex. 2021 = saison 2020/21). "
                "Évolutions et indices comparent la dernière année à la première.")))
    if start == end:
        st.warning(tr("Pick at least two years — showing the previous year as start.",
                      "Choisissez au moins deux années — l'année précédente sert de départ."))
        start = YEARS[max(0, YEARS.index(end) - 1)]
        if start == end:
            end = YEARS[1]

    deps = D.departments.sort_values("dep")
    regions = sorted(deps["region"].unique())
    sel_regions = keep("regions", st.multiselect(
        tr("Region", "Région"), regions, default=[r for r in mem("regions", []) if r in regions],
        placeholder=tr("All of France", "Toute la France"),
        help=tr("Leave empty for all of France (mainland + 4 overseas départements; "
                "Mayotte is outside the geocoded scope).",
                "Laisser vide pour toute la France (métropole + 4 départements d'outre-mer ; "
                "Mayotte est hors du champ géocodé).")))
    pool = deps[deps["region"].isin(sel_regions)] if sel_regions else deps
    dep_labels = {r.dep: f"{r.dep_name} ({r.dep})" for r in pool.itertuples()}
    sel_deps = keep("deps", st.multiselect(
        "Département", list(dep_labels), format_func=dep_labels.get,
        default=[x for x in mem("deps", []) if x in dep_labels],
        placeholder=tr("All in selected region(s)", "Tous ceux des régions choisies")))
    dep_codes = tuple(sel_deps) if sel_deps else tuple(pool["dep"])
    scope_label = ("France" if not sel_regions and not sel_deps else
                   ", ".join(dep_labels[d] for d in sel_deps) if 0 < len(sel_deps) <= 2 else
                   f"{len(sel_deps)} départements" if sel_deps else
                   ", ".join(sel_regions) if len(sel_regions) <= 2 else
                   tr(f"{len(sel_regions)} regions", f"{len(sel_regions)} régions"))

    sex_options = ["All", "F", "H"]
    sex = keep("sex", st.radio(tr("Sex", "Sexe"), sex_options, index=sex_options.index(mem("sex", "All")),
                   format_func=label, horizontal=True,
                   help=tr("Applies to counts, growth and per-capita rates. Women's-share views always use both sexes.",
                           "S'applique aux effectifs, évolutions et taux par habitant. Les vues « part des femmes » "
                           "utilisent toujours les deux sexes.")))
    ages = keep("ages", st.multiselect(tr("Age groups", "Tranches d'âge"), list(AGE_GROUPS),
                          default=mem("ages", list(AGE_GROUPS)), format_func=label,
                          help=tr("Age at licence date, grouped from INJEP's 5-year bands.",
                                  "Âge à la date de la licence, regroupé à partir des tranches de 5 ans de l'INJEP.")))
    if not ages:
        st.warning(tr("No age group selected — showing all ages.", "Aucune tranche choisie — tous les âges affichés."))
        ages = list(AGE_GROUPS)

    feds = D.federations
    min_size = SEEDS["min_federation_size_for_comparison"]
    choices = feds[feds["single_sport"] & (feds["code"] != SEEDS["tennis_code"]) & (feds["2019"] >= min_size)]
    choices = choices.sort_values("2019", ascending=False)
    comp_keys = list(choices["fed_key"])
    default_comp = feds.loc[feds["code"] == SEEDS["default_comparison_code"], "fed_key"].iloc[0]
    comparison = keep("comparison", st.selectbox(
        tr("Compare tennis with…", "Comparer le tennis avec…"), comp_keys,
        index=comp_keys.index(mem("comparison", default_comp)), format_func=D.fed_name,
                              help=tr(f"Single-sport federations with ≥{min_size:,} licences in 2019.",
                                      f"Fédérations unisport avec ≥{min_size:,} licences en 2019.")))

    metric = keep("metric", st.radio(
        tr("Map variable", "Variable de la carte"), list(overview.METRIC_KEYS),
        index=list(overview.METRIC_KEYS).index(mem("metric", "per1000")), format_func=overview.metric_option,
                      help=tr("Variable shown on the map and in the ranking (section 2).",
                              "Variable affichée sur la carte et dans le classement (section 2).")))

    st.divider()
    st.markdown(tr("**Story**  \n[1 · Hook](#hook) · [2 · Where](#where) · [3 · Who](#who)  \n"
                   "[4 · Who is missing](#missing) · [5 · So what?](#so-what) · [Data quality](#data-quality)",
                   "**Récit**  \n[1 · Accroche](#hook) · [2 · Où](#where) · [3 · Qui](#who)  \n"
                   "[4 · Les absents](#missing) · [5 · Et alors ?](#so-what) · [Qualité des données](#data-quality)"))
    st.caption(tr("Source: INJEP–MEDES licence census, geocoded by INSEE · Licence Ouverte 2.0. "
                  "Population: INSEE populations légales.",
                  "Source : recensement des licences INJEP–MEDES, géocodé par l'INSEE · Licence Ouverte 2.0. "
                  "Population : populations légales INSEE."))

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
