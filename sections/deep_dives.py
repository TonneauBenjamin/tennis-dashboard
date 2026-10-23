"""Sections 3 & 4 — Who plays (age, sex) and who is missing (priority neighbourhoods)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from utils import prep as A
from utils import viz
from utils.io import AGE_GROUPS, SEEDS
from utils.viz import cached, chart, insight, label, section, tr


def render_who(d: A.Data, f: A.Filters) -> None:
    section("who", tr("3 · Who", "3 · Qui"),
            tr("The new players are young adults", "Les nouveaux joueurs sont de jeunes adultes"),
            tr("Which age groups drove the growth, and did the gender gap close?",
               "Quelles tranches d'âge ont porté la croissance, et l'écart femmes-hommes s'est-il réduit ?"))
    g = cached("growth_by_age", d, f)
    t = g[g["group"] == A.TENNIS].set_index("age_group")
    b = g[g["group"] == A.BENCH].set_index("age_group")
    top = t["growth"].idxmax()
    share_added = t.loc[top, "added"] / t["added"].sum() * 100 if t["added"].sum() > 0 else float("nan")
    base_share = t.loc[top, f.start] / t[f.start].sum() * 100
    has_growth = share_added == share_added
    insight(tr(
        f"<b>{label(top)}</b> grew <b>{t.loc[top, 'growth']:+.0f}%</b> in tennis over {f.span}, against "
        f"{b.loc[top, 'growth']:+.0f}% in other single-sport federations. They were {base_share:.0f}% of "
        f"tennis licences in {f.start} but brought "
        + (f"<b>{share_added:.0f}%</b> of the net new licences." if has_growth else "no net growth.")
        + " Children remain the base of the sport, but no longer its engine.",
        f"Les <b>{label(top).lower()}</b> ont progressé de <b>{t.loc[top, 'growth']:+.0f} %</b> au tennis sur {f.span}, "
        f"contre {b.loc[top, 'growth']:+.0f} % dans les autres fédérations unisport. Ils représentaient {base_share:.0f} % "
        f"des licences de tennis en {f.start} mais ont apporté "
        + (f"<b>{share_added:.0f} %</b> des nouvelles licences nettes." if has_growth else "aucune croissance nette.")
        + " Les enfants restent la base du sport, mais n'en sont plus le moteur."))

    c1, c2 = st.columns([1.1, 1])
    highlight = {band for grp in f.ages for band in AGE_GROUPS[grp]}
    with c1:
        p = cached("pyramid", d, f)
        chart(viz.pyramid_chart(p, f.start, f.end, highlight),
              alt=tr(f"Population pyramid of tennis licences by 5-year age band, men on the left, women on the "
                     f"right, {f.end} as bars and {f.start} as black ticks. The largest bands are ages 5–14; "
                     f"the 20–34 bands extend furthest beyond their {f.start} ticks. Age groups not selected in "
                     f"the sidebar are faded.",
                     f"Pyramide des licences de tennis par tranche de 5 ans, hommes à gauche, femmes à droite, "
                     f"{f.end} en barres et {f.start} en traits noirs. Les tranches les plus fournies sont les 5–14 ans ; "
                     f"les 20–34 ans dépassent le plus leurs traits de {f.start}. Les tranches non sélectionnées dans "
                     f"la barre latérale sont estompées."),
              table=p.pivot_table(index="age_band", columns=["sex", "year"], values="licences", observed=True)
                     .reindex(SEEDS["age_bands"]).reset_index(), key="pyramid")
    with c2:
        chart(viz.age_growth_chart(g, None),
              alt=tr("Grouped bar chart of growth by age group, tennis (orange) versus other single-sport "
                     f"federations (grey). Tennis grows most among {label(top).lower()} ({t.loc[top, 'growth']:+.0f}%).",
                     "Barres groupées de l'évolution par tranche d'âge, tennis (orange) contre autres fédérations "
                     f"unisport (gris). Le tennis progresse le plus chez les {label(top).lower()} "
                     f"({t.loc[top, 'growth']:+.0f} %)."),
              table=g.round(1), key="agegrowth")

    st.subheader(tr("The gender gap did not move", "L'écart femmes-hommes n'a pas bougé"), anchor=False)
    comp = d.fed_name(f.comparison)
    ws = {A.BENCH: cached("women_share", d, f, "bench"),
          comp: cached("women_share", d, f, f.comparison),
          A.TENNIS: cached("women_share", d, f, "tennis")}
    wt, wb = ws[A.TENNIS], ws[A.BENCH]
    ratio = (100 - wt.iloc[-1]) / wt.iloc[-1]
    insight(tr(
        f"Women held <b>{wt.iloc[-1]:.1f}%</b> of tennis licences in {f.end} "
        f"({wt.iloc[-1] - wt.iloc[0]:+.1f} points since {f.start}), against {wb.iloc[-1]:.1f}% in other "
        f"single-sport federations. Growth brought in more women in absolute terms but did not change "
        f"the balance: roughly <b>{ratio:.1f} men for every woman</b>.",
        f"Les femmes détenaient <b>{wt.iloc[-1]:.1f} %</b> des licences de tennis en {f.end} "
        f"({wt.iloc[-1] - wt.iloc[0]:+.1f} points depuis {f.start}), contre {wb.iloc[-1]:.1f} % dans les autres "
        f"fédérations unisport. La croissance a attiré plus de femmes en nombre, sans changer l'équilibre : "
        f"environ <b>{ratio:.1f} hommes pour une femme</b>."))
    ya = "Young adults (20–34)"
    if ya in f.ages:
        wya = cached("women_share", d, A.Filters(f.start, f.end, f.deps, "All", (ya,), f.comparison,
                                                 f.scope_label), "tennis")
        if wya.notna().all():
            down = wya.iloc[-1] < wya.iloc[0]
            st.markdown(tr(
                f"Among **young adults**, the fastest-growing group, women's share went from "
                f"**{wya.iloc[0]:.1f}%** to **{wya.iloc[-1]:.1f}%**: the boom was "
                f"{'male-skewed' if down else 'not male-skewed'}. "
                "This fits the padel hypothesis, but the data cannot confirm it.",
                f"Chez les **jeunes adultes**, le groupe qui progresse le plus, la part des femmes est passée de "
                f"**{wya.iloc[0]:.1f} %** à **{wya.iloc[-1]:.1f} %** : l'essor a été "
                f"{'surtout masculin' if down else 'équilibré'}. "
                "C'est cohérent avec l'hypothèse du padel, mais les données ne permettent pas de le confirmer."))
    chart(viz.women_chart(ws),
          alt=tr(f"Line chart of women's share of licences, {f.span}: tennis about {wt.iloc[-1]:.0f}%, other "
                 f"single-sport federations about {wb.iloc[-1]:.0f}%, {comp} {ws[comp].iloc[-1]:.0f}%; "
                 "a reference line marks parity at 50%.",
                 f"Courbes de la part des femmes, {f.span} : tennis environ {wt.iloc[-1]:.0f} %, autres fédérations "
                 f"unisport environ {wb.iloc[-1]:.0f} %, {comp} {ws[comp].iloc[-1]:.0f} % ; une ligne de référence "
                 "marque la parité à 50 %."),
          table=pd.DataFrame({label(k): v for k, v in ws.items()}).round(2).reset_index()
                .rename(columns={"index": tr("year", "année")}), key="women")
    st.caption(tr("Women's share = women ÷ (women + men); licences with unknown sex (0.02% for tennis, 2.8% for "
                  "all sports in 2019 only) are excluded. The age filter applies; the sex filter does not.",
                  "Part des femmes = femmes ÷ (femmes + hommes) ; les licences de sexe inconnu (0,02 % pour le tennis, "
                  "2,8 % pour tous les sports en 2019 uniquement) sont exclues. Le filtre d'âge s'applique, pas celui "
                  "du sexe."))


def render_missing(d: A.Data, f: A.Filters) -> None:
    section("missing", tr("4 · Who is missing", "4 · Les absents"),
            tr("Priority neighbourhoods are left behind", "Les quartiers prioritaires restent à l'écart"),
            tr("Do residents of deprived urban areas (QPV) take part in tennis as much as in other sports?",
               "Les habitants des quartiers prioritaires (QPV) pratiquent-ils le tennis autant que les autres sports ?"))
    per_fed, bench = cached("qpv_shares", d, f, SEEDS["min_federation_size_for_comparison"])
    tennis_name, comp = d.fed_name(d.tennis_key), d.fed_name(f.comparison)
    tq = per_fed[per_fed["name"] == tennis_name].set_index("year")["share"]
    bq = bench.set_index("year")["share"]
    if tq.empty or f.end not in tq.index or tq.loc[f.end] == 0 or bq.get(f.end, 0) == 0:
        insight(tr("No QPV residents hold tennis licences in this selection (many rural départements have no QPV).",
                   "Aucun habitant de QPV n'a de licence de tennis dans cette sélection (beaucoup de départements "
                   "ruraux n'ont pas de QPV)."))
        return
    end_rank = per_fed[per_fed["year"] == f.end].sort_values("share")
    pos = list(end_rank["name"]).index(tennis_name) + 1
    insight(tr(
        f"Residents of priority neighbourhoods hold <b>{tq.iloc[-1]:.1f}%</b> of tennis licences, "
        f"<b>{bq.iloc[-1] / tq.iloc[-1]:.1f}× less</b> than their {bq.iloc[-1]:.1f}% share in other "
        f"single-sport federations. Tennis ranks <b>{pos} of {len(end_rank)}</b> large federations on this "
        "measure (1 = least inclusive): the post-COVID boom did not reach these areas proportionally.",
        f"Les habitants des quartiers prioritaires détiennent <b>{tq.iloc[-1]:.1f} %</b> des licences de tennis, "
        f"<b>{bq.iloc[-1] / tq.iloc[-1]:.1f} fois moins</b> que leur part de {bq.iloc[-1]:.1f} % dans les autres "
        f"fédérations unisport. Le tennis est <b>{pos}ᵉ sur {len(end_rank)}</b> grandes fédérations sur cet indicateur "
        "(1 = la moins inclusive) : l'essor post-COVID n'a pas touché ces quartiers à proportion."))
    c1, c2 = st.columns([1.2, 1])
    with c1:
        n_min = f"{SEEDS['min_federation_size_for_comparison']:,}"
        chart(viz.qpv_chart(per_fed, bq.iloc[-1], f.end, tennis_name, comp),
              alt=tr(f"Horizontal bar chart of the share of licences held by QPV residents in {f.end}, for each "
                     f"single-sport federation with at least {n_min} licences nationally. Tennis (orange) is at "
                     f"{tq.iloc[-1]:.1f}%; the benchmark line is at {bq.iloc[-1]:.1f}%.",
                     f"Barres horizontales de la part des licences détenues par des habitants de QPV en {f.end}, pour "
                     f"chaque fédération unisport d'au moins {n_min} licences en France. Le tennis (orange) est à "
                     f"{tq.iloc[-1]:.1f} % ; la ligne de référence est à {bq.iloc[-1]:.1f} %."),
              table=end_rank[["name", "In QPV", "total", "share"]].round(2).sort_values("share")
                    .rename(columns={"name": tr("Federation", "Fédération"),
                                     "In QPV": tr("QPV licences", "Licences en QPV"),
                                     "total": tr("All allocated", "Total localisé"),
                                     "share": tr("QPV share %", "Part QPV %")}), key="qpv")
    with c2:
        chart(viz.qpv_trend_chart(tq, bq),
              alt=tr(f"Line chart of the QPV share of licences over {f.span}: tennis from {tq.iloc[0]:.1f}% to "
                     f"{tq.iloc[-1]:.1f}%, other single-sport federations from {bq.iloc[0]:.1f}% to "
                     f"{bq.iloc[-1]:.1f}%. The 2023 point uses the new QPV map.",
                     f"Courbes de la part QPV sur {f.span} : tennis de {tq.iloc[0]:.1f} % à {tq.iloc[-1]:.1f} %, "
                     f"autres fédérations unisport de {bq.iloc[0]:.1f} % à {bq.iloc[-1]:.1f} %. Le point 2023 utilise "
                     "la nouvelle carte des QPV."), key="qpvtrend")
    with st.expander(tr("What is a QPV, and why the 2023 break?", "Qu'est-ce qu'un QPV, et pourquoi la rupture de 2023 ?")):
        st.markdown(tr(
            "A *quartier prioritaire de la politique de la ville* (QPV) is an officially designated low-income "
            "urban neighbourhood. INSEE flags each geocoded licence as inside or outside a QPV. "
            "Licences that could not be placed at that level ('non réparti') are excluded from both numerator "
            "and denominator. **The 2023 file uses the new QPV list (codes `QN…`), which covers more areas** — "
            "part of the 2023 rise for every sport is a definitional change, so compare sports *within* a year "
            "rather than reading the 2022→2023 step as progress. The data has no income variable: this is a "
            "neighbourhood-level proxy for social background, not an individual one.",
            "Un *quartier prioritaire de la politique de la ville* (QPV) est un quartier urbain à bas revenus désigné "
            "officiellement. L'INSEE indique pour chaque licence géocodée si elle est dans un QPV ou non. "
            "Les licences non localisables à ce niveau (« non réparti ») sont exclues du numérateur et du dénominateur. "
            "**Le fichier 2023 utilise la nouvelle liste des QPV (codes `QN…`), qui couvre plus de quartiers** — "
            "une partie de la hausse de 2023, pour tous les sports, vient de ce changement de définition : comparez "
            "les sports *au sein* d'une même année plutôt que de lire le passage 2022→2023 comme un progrès. Les données "
            "ne contiennent pas de revenu : c'est un indicateur social au niveau du quartier, pas de l'individu."))
