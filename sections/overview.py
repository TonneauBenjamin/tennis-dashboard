"""Section 2 — Where: geography of tennis density, growth and gender balance."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils import prep as A
from utils import viz
from utils.viz import cached, chart, insight, section, tr

METRIC_KEYS = ("per1000", "growth", "women_share")


def metric_option(key: str) -> str:
    """Label of a map variable in the sidebar, in the current language."""
    return {"per1000": tr("Licences per 1,000 residents", "Licences pour 1 000 habitants"),
            "growth": tr("Growth over the period", "Évolution sur la période"),
            "women_share": tr("Women's share", "Part des femmes")}[key]


def _average(dep: pd.DataFrame, metric: str) -> float:
    s = dep[dep["selected"]]
    if metric == "per1000":
        return s["licences_end"].sum() / s["population"].sum() * 1000
    if metric == "growth":
        return (s["licences_end"].sum() / s["licences_start"].sum() - 1) * 100
    return float((s["women_share"] * s["licences_end"]).sum() / s["licences_end"].sum())


def render(d: A.Data, f: A.Filters, geo: dict, metric: str) -> None:
    section("where", tr("2 · Where", "2 · Où"),
            tr("Where tennis is played, and where it grew", "Où l'on joue au tennis, et où il a progressé"),
            tr("Where is tennis played most, and where did it grow?",
               "Où le tennis est-il le plus pratiqué, et où a-t-il progressé ?"))
    dep = cached("by_department", d, f)
    sel = dep[dep["selected"]].dropna(subset=["per1000"])
    avg = _average(dep, metric)

    top_d = sel.nlargest(3, "per1000")
    low_d = sel.nsmallest(3, "per1000")
    grow = sel.nlargest(3, "growth")
    if len(sel) >= 6:
        shrink = sel.nsmallest(1, "growth").iloc[0]
        ratio = top_d["per1000"].iloc[0] / low_d["per1000"].iloc[0]
        tops = ", ".join(f"{r.dep_name} ({r.per1000:.1f})" for r in top_d.itertuples())
        lows = ", ".join(f"{r.dep_name} ({r.per1000:.1f})" for r in low_d.itertuples())
        grows = ", ".join(f"{r.dep_name} ({r.growth:+.0f}%)" for r in grow.itertuples())
        insight(tr(
            f"Density varies <b>{ratio:.1f}×</b> across départements: from {tops} licences per 1,000 residents "
            f"down to {lows}. The fastest growth over {f.span} was in {grows}; "
            f"{shrink.dep_name} declined most ({shrink.growth:+.0f}%).",
            f"La densité varie de <b>1 à {ratio:.1f}</b> selon les départements : de {tops} licences pour 1 000 habitants "
            f"à {lows}. La plus forte progression sur {f.span} est en {grows} ; "
            f"{shrink.dep_name} recule le plus ({shrink.growth:+.0f} %)."))
    else:
        insight(tr("Select at least six départements (or a whole region) to compare geography meaningfully.",
                   "Sélectionnez au moins six départements (ou une région entière) pour comparer la géographie."))

    name = metric_option(metric).lower()
    c1, c2 = st.columns([1.25, 1])
    with c1:
        alt_growth = tr(" (blue = growth, red = decline, grey = stable)",
                        " (bleu = hausse, rouge = baisse, gris = stable)") if metric == "growth" else ""
        chart(viz.choropleth(dep, geo, metric, avg),
              alt=tr(f"Map of France by département showing {name} for tennis, {f.end}. Darker = higher{alt_growth}. "
                     f"Selection average: {avg:.1f}. Départements outside the selection are light grey.",
                     f"Carte de France par département : {name} pour le tennis, {f.end}. Plus foncé = plus élevé"
                     f"{alt_growth}. Moyenne de la sélection : {avg:.1f}. Les départements hors sélection sont en gris clair."),
              key="map")
    with c2:
        chart(viz.ranking_chart(dep, metric, avg),
              alt=tr(f"Horizontal bar chart of the top and bottom 10 selected départements by {name}, with the "
                     "selection average as a vertical line.",
                     f"Barres horizontales des 10 premiers et 10 derniers départements sélectionnés ({name}), avec la "
                     "moyenne de la sélection en trait vertical."),
              table=sel[["dep", "dep_name", "region", "licences_start", "licences_end", "population",
                         "per1000", "growth", "women_share"]].round(1).sort_values(metric, ascending=False)
                       .rename(columns={"dep": "Code", "dep_name": "Département", "region": tr("Region", "Région"),
                                        "licences_start": f"Licences {f.start}", "licences_end": f"Licences {f.end}",
                                        "population": "Population", "per1000": tr("Per 1,000", "Pour 1 000"),
                                        "growth": tr("Growth %", "Évolution %"), "women_share": tr("Women %", "Femmes %")}),
              key="rank")

    with st.expander(tr("Method: how density and growth are computed", "Méthode : calcul de la densité et de l'évolution")):
        st.markdown(tr(
            "- **Licences per 1,000 residents** = tennis licences of residents of the département ÷ legal "
            "municipal population × 1,000. Licences are counted where the player *lives*, not where they play.\n"
            "- Population: INSEE *populations légales* of the same year up to 2021; 2022–2023 use 2021 "
            "(population grows ~0.3%/year, so rates for those two years are overstated by under 1%).\n"
            "- With a sex or age filter, the numerator is restricted but the denominator stays the whole "
            "population; read the rate as *licences of that group per 1,000 residents*.\n"
            "- A licence is not a player: some people hold none (casual play), a few hold two.",
            "- **Licences pour 1 000 habitants** = licences de tennis des habitants du département ÷ population "
            "municipale légale × 1 000. Les licences sont comptées là où le joueur *habite*, pas là où il joue.\n"
            "- Population : *populations légales* INSEE de la même année jusqu'en 2021 ; 2022–2023 utilisent 2021 "
            "(la population croît d'environ 0,3 %/an, donc ces deux années sont surestimées de moins de 1 %).\n"
            "- Avec un filtre sexe ou âge, le numérateur est restreint mais le dénominateur reste toute la population ; "
            "lisez le taux comme *licences de ce groupe pour 1 000 habitants*.\n"
            "- Une licence n'est pas un joueur : certains n'en ont pas (pratique libre), quelques-uns en ont deux."))

    st.subheader(tr("Drill down: the leading communes of a département",
                    "Zoom : les principales communes d'un département"), anchor=False)
    options = sel.sort_values("licences_end", ascending=False)
    if options.empty:
        return
    labels = {r.dep: f"{r.dep_name} ({r.dep})" for r in options.itertuples()}
    keys = list(labels)
    prev = st.session_state.get("_mem_commune_dep")
    pick = st.selectbox("Département", keys, format_func=labels.get, index=keys.index(prev) if prev in keys else 0,
                        help=tr("Ordered by number of tennis licences.", "Classés par nombre de licences de tennis."))
    st.session_state["_mem_commune_dep"] = pick
    com = cached("communes", d, f, pick, 15)
    lic_s, lic_e = f"Licences {f.start}", f"Licences {f.end}"
    growth_c, women_c = tr("Growth %", "Évolution %"), tr("Women %", "Femmes %")
    st.dataframe(
        com.rename(columns={"commune_code": "Code", "commune": "Commune", f.start: lic_s, f.end: lic_e,
                            "growth": growth_c, "women_share": women_c}),
        hide_index=True, width="stretch",
        column_config={
            lic_e: st.column_config.ProgressColumn(lic_e, format="%d", min_value=0,
                                                   max_value=int(com[f.end].max() or 1)),
            growth_c: st.column_config.NumberColumn(format="%+.1f%%"),
            women_c: st.column_config.NumberColumn(format="%.1f%%"),
            lic_s: st.column_config.NumberColumn(format="%d")})
    st.caption(tr("Commune figures are INSEE estimates allocated from geocoded addresses; all ages and sexes. "
                  "Paris, Lyon and Marseille appear by arrondissement.",
                  "Les chiffres communaux sont des estimations INSEE issues des adresses géocodées ; tous âges et sexes. "
                  "Paris, Lyon et Marseille apparaissent par arrondissement."))
