"""Section 5 — So what? Implications, limitations, next steps; then the data-quality appendix."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils import prep as A
from utils import viz
from utils.io import COLORS, SEEDS
from utils.viz import cached, chart, section, tr


def render(d: A.Data, f: A.Filters) -> None:
    section("so-what", tr("5 · So what?", "5 · Et alors ?"),
            tr("Three implications for clubs and policymakers", "Trois enseignements pour les clubs et les décideurs"))
    k = cached("kpis", d, f)
    g = cached("growth_by_age", d, f)
    t = g[g["group"] == A.TENNIS].set_index("age_group")
    ya = "Young adults (20–34)"
    per_fed, bench = cached("qpv_shares", d, f, SEEDS["min_federation_size_for_comparison"])
    tq = per_fed[(per_fed["name"] == d.fed_name(d.tennis_key)) & (per_fed["year"] == f.end)]["share"]
    bq = bench.loc[bench["year"] == f.end, "share"]
    qtxt = (f"{tq.iloc[0]:.1f}% vs {bq.iloc[0]:.1f}%" if len(tq) and len(bq) else tr("see section 4", "voir section 4"))

    c = st.columns(3)
    with c[0]:
        st.markdown(tr("##### 1 · Plan capacity for adults, not just juniors",
                       "##### 1 · Prévoir des créneaux pour les adultes, pas seulement les jeunes"))
        st.markdown(tr(
            f"Young adults grew **{t.loc[ya, 'growth']:+.0f}%** ({t.loc[ya, 'added']:+,.0f} licences) over "
            f"{f.span}. These players want evening and weekend slots, short formats and (probably) padel. "
            "Court-hour availability at peak times, not total court count, is the likely bottleneck.",
            f"Les jeunes adultes ont progressé de **{t.loc[ya, 'growth']:+.0f} %** ({t.loc[ya, 'added']:+,.0f} licences) "
            f"sur {f.span}. Ces joueurs veulent des créneaux le soir et le week-end, des formats courts et (sans doute) "
            "du padel. Le goulot d'étranglement probable est le nombre d'heures de court aux heures de pointe, pas le "
            "nombre total de courts."))
    with c[1]:
        st.markdown(tr("##### 2 · The growth is real but uneven", "##### 2 · Une croissance réelle mais inégale"))
        st.markdown(tr(
            f"Tennis grew **{k['tennis_growth']:+.1f}%** against **{k['bench_growth']:+.1f}%** for other "
            "single-sport federations, but some départements shrank. Investment should follow per-capita "
            "demand and growth (section 2), not historical club size.",
            f"Le tennis a progressé de **{k['tennis_growth']:+.1f} %** contre **{k['bench_growth']:+.1f} %** pour les "
            "autres fédérations unisport, mais certains départements ont reculé. L'investissement devrait suivre la "
            "demande par habitant et sa progression (section 2), pas la taille historique des clubs."))
    with c[2]:
        st.markdown(tr("##### 3 · The boom skipped two groups", "##### 3 · L'essor a oublié deux publics"))
        st.markdown(tr(
            f"Women's share stayed at **{k['women_end']:.0f}%**, and priority neighbourhoods remain "
            f"under-represented ({qtxt}). Targeted offers (women-only sessions, free school-to-club "
            "pathways, courts in QPV) are where the next growth could come from.",
            f"La part des femmes est restée à **{k['women_end']:.0f} %**, et les quartiers prioritaires restent "
            f"sous-représentés ({qtxt}). Des offres ciblées (séances réservées aux femmes, passerelles gratuites "
            "école-club, courts en QPV) sont les prochains relais de croissance possibles."))

    st.markdown(tr("#### Limitations — read before quoting a number", "#### Limites — à lire avant de citer un chiffre"))
    st.markdown(tr(
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
        "- **No causality.** The charts show co-movement and differences; they do not identify why tennis grew.",
        "- **Licences ≠ joueurs.** Les joueurs occasionnels sans licence sont invisibles ; une licence compte une fois "
        "par saison même si son titulaire joue peu.\n"
        "- **Le padel est inclus dans le tennis.** La FFT gère le padel ; le recensement ne sépare pas les deux, donc "
        "une partie de la hausse chez les jeunes adultes peut venir du padel. Hypothèse que les données ne peuvent pas tester.\n"
        "- **Résidence, pas pratique.** Les licences sont géocodées à l'adresse du titulaire. Les valeurs communales "
        "sont des *estimations* INSEE.\n"
        "- **Saisons.** Année de licence N = saison FFT N-1/N (septembre–août). Les fermetures COVID ont touché une "
        "partie des saisons 2020 et 2021.\n"
        "- **Ruptures de séries.** Les fédérations recodées d'une année à l'autre sont rapprochées par leur nom ; la "
        "carte des QPV a changé en 2023 ; les années avant 2019 ont un autre format et sont exclues. L'INJEP précise "
        "que les révisions ultérieures ne sont pas reportées dans les fichiers détaillés.\n"
        "- **Pas de causalité.** Les graphiques montrent des évolutions conjointes et des écarts ; ils n'expliquent "
        "pas pourquoi le tennis a progressé."))

    st.markdown(tr("#### Next steps", "#### Prochaines étapes"))
    st.markdown(tr(
        "1. Add the **2024 census** when INJEP publishes it, to test for a Paris-2024 Olympic effect.\n"
        "2. Join the **Data ES sports-facilities census** (courts per département) to compare demand with supply.\n"
        "3. Ask the FFT for a **tennis/padel split** of licences to test the padel hypothesis.\n"
        "4. Replace the QPV proxy with **commune median income** (INSEE Filosofi) to measure the social gradient "
        "directly.",
        "1. Ajouter le **recensement 2024** dès sa publication par l'INJEP, pour tester un effet des JO de Paris 2024.\n"
        "2. Croiser avec le **recensement des équipements sportifs Data ES** (courts par département) pour comparer "
        "l'offre et la demande.\n"
        "3. Demander à la FFT une **répartition tennis/padel** des licences pour tester l'hypothèse du padel.\n"
        "4. Remplacer l'indicateur QPV par le **revenu médian communal** (INSEE Filosofi) pour mesurer directement "
        "le gradient social."))


def render_data_quality(d: A.Data, f: A.Filters, q: dict) -> None:
    section("data-quality", tr("Appendix", "Annexe"),
            tr("Data quality, validation & methods", "Qualité des données, validation et méthodes"),
            tr("Can these numbers be trusted, and what was done to them?",
               "Peut-on se fier à ces chiffres, et quels traitements ont-ils subis ?"))
    yrs = pd.DataFrame(q["years"]).set_index("year")
    all_ok = (yrs["non_numeric_cells"].sum() == 0 and yrs["negative_cells"].sum() == 0
              and yrs["rows_where_sex_age_sum_differs_from_total"].sum() == 0 and yrs["duplicate_keys"].sum() == 0
              and all(c["consistent"] for c in q["cross_checks"]))
    if all_ok:
        st.success(tr("All automated checks pass: counts are numeric and non-negative, sex × age columns add up to the "
                      "total on every row, keys are unique, and tennis totals are identical across the four derived tables.",
                      "Tous les contrôles automatiques sont validés : effectifs numériques et positifs, colonnes sexe × âge "
                      "égales au total sur chaque ligne, clés uniques, et totaux du tennis identiques dans les quatre "
                      "tables dérivées."))
    else:
        st.error(tr("At least one automated check failed — see the table below.",
                    "Au moins un contrôle automatique a échoué — voir le tableau ci-dessous."))

    c = st.columns(4)
    c[0].metric(tr("Raw rows read (5 years)", "Lignes brutes lues (5 ans)"), f"{yrs['rows'].sum():,}")
    c[1].metric(tr("Tennis rows", "Lignes tennis"), f"{yrs['tennis_rows'].sum():,}")
    c[2].metric(tr("Outside geocoded scope (all sports)", "Hors champ géocodé (tous sports)"),
                f"{yrs['share_out_of_scope_pct'].mean():.1f}%",
                help=tr("Mayotte, overseas collectivities, Monaco and abroad. Excluded from all maps and rates.",
                        "Mayotte, collectivités d'outre-mer, Monaco et étranger. Exclus des cartes et des taux."))
    c[3].metric(tr("Processed data shipped", "Données traitées livrées"),
                f"{sum(q['processed_bytes'].values()) / 1e6:.1f} MB",
                help=tr("vs ~1.2 GB of raw CSV, which the build script downloads and caches.",
                        "contre ~1,2 Go de CSV bruts, téléchargés et mis en cache par le script."))

    st.markdown(tr("##### Validation checks, by file", "##### Contrôles de validation, par fichier"))
    checks = pd.DataFrame({
        tr("Rows", "Lignes"): yrs["rows"],
        tr("Columns", "Colonnes"): yrs["columns"],
        tr("Non-numeric counts", "Effectifs non numériques"): yrs["non_numeric_cells"],
        tr("Negative counts", "Effectifs négatifs"): yrs["negative_cells"],
        tr("Rows: sex×age ≠ total", "Lignes : sexe×âge ≠ total"): yrs["rows_where_sex_age_sum_differs_from_total"],
        tr("Duplicate keys", "Clés en double"): yrs["duplicate_keys"],
        tr("Naive duplicates*", "Doublons naïfs*"): yrs["naive_duplicates_commune_qpv_only"],
        tr("Unknown sex (all sports)", "Sexe inconnu (tous sports)"): yrs["licences_unknown_sex"],
        tr("Unknown age (all sports)", "Âge inconnu (tous sports)"): yrs["licences_unknown_age"],
        tr("Out-of-scope %", "Hors champ %"): yrs["share_out_of_scope_pct"],
        tr("Tennis licences", "Licences tennis"): yrs["tennis_licences"],
    })
    st.dataframe(checks, width="stretch")
    st.caption(tr("*Keying rows on commune + QPV + federation alone suggests ~600–800 duplicates per year; they are "
                  "the out-of-scope 'non réparti' rows, one per overseas territory. With the département in the key "
                  "(the correct key) there are **0** duplicates. Column counts differ because 2019–2021 carry extra "
                  "'unknown sex' columns, harmonised into a single *Unknown* category.",
                  "*Une clé commune + QPV + fédération seule fait apparaître ~600–800 doublons par an : ce sont les lignes "
                  "« non réparti » hors champ, une par territoire d'outre-mer. Avec le département dans la clé (la bonne "
                  "clé), il y a **0** doublon. Le nombre de colonnes varie car 2019–2021 ont des colonnes « sexe inconnu » "
                  "supplémentaires, regroupées en une seule catégorie *Inconnu*."))

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(tr("##### Missing values in identifier columns", "##### Valeurs manquantes dans les identifiants"))
        miss = pd.DataFrame({y["year"]: y["missing_values"] for y in q["years"]})
        miss = miss[miss.sum(axis=1) > 0]
        st.dataframe(miss, width="stretch")
        st.caption(tr("`Commune` is empty only on 'non réparti' rows (licences not allocated to a commune); "
                      "`Nom QPV` is empty by design outside priority neighbourhoods. No count is missing.",
                      "`Commune` n'est vide que sur les lignes « non réparti » (licences non rattachées à une commune) ; "
                      "`Nom QPV` est vide par construction hors des quartiers prioritaires. Aucun effectif ne manque."))
    with c2:
        sc = d.scope.copy()
        sc = sc[sc["fed_key"].astype(str) == d.tennis_key]
        sc = sc.pivot_table(index="year", columns="status", values="licences", observed=True)
        fig = go.Figure()
        for col, colr, name in [(sc.columns[0], COLORS["tennis"], tr("Geocoded (in scope)", "Géocodées (dans le champ)")),
                                (sc.columns[-1], COLORS["all_sports"], tr("Out of scope", "Hors champ"))]:
            fig.add_trace(go.Bar(x=sc.index, y=sc[col], name=name, marker_color=colr,
                                 hovertemplate=f"{name}<br>%{{x}}: %{{y:,.0f}}<extra></extra>"))
        viz.base(fig, tr("Tennis licences by geocoding status", "Licences de tennis selon le géocodage"),
                 height=300, legend=True)
        fig.update_layout(barmode="stack", bargap=0.35)
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(title="Licences")
        chart(fig, alt=tr("Stacked bars per year: almost all tennis licences are geocoded; about 1% are out of scope.",
                          "Barres empilées par année : presque toutes les licences de tennis sont géocodées ; environ 1 % "
                          "sont hors champ."),
              table=sc.reset_index(), key="scope")

    st.markdown(tr("##### Cross-table consistency (tennis, in scope)",
                   "##### Cohérence entre tables (tennis, dans le champ)"))
    st.dataframe(pd.DataFrame(q["cross_checks"]).set_index("year"), width="stretch")

    recoded = ", ".join(q["federations_recoded_between_years"])
    n_recoded = len(q["federations_recoded_between_years"])
    with st.expander(tr("Pipeline & decisions (feature engineering)", "Chaîne de traitement et choix (feature engineering)")):
        st.markdown(tr(f"""
1. **Download & cache** the five yearly files (`download_data.py`, sizes verified against data.gouv metadata).
2. **Type & validate**: identifiers kept as text (leading zeros, `2A/2B`), counts coerced to integers with
   non-numeric and negative cells counted, row sums checked, keys tested for uniqueness.
3. **Scope**: keep `Statut géo = 1.Champ geoc` (mainland + Guadeloupe, Martinique, Guyane, La Réunion).
4. **Harmonise** sex × age columns across years: 17 five-year bands × {{women, men, unknown}}, grouped into
   5 age groups for filtering.
5. **Stable federation key** from the normalised name, because INJEP re-coded {n_recoded} federations between
   years ({recoded}).
6. **Benchmark** = single-sport federations (codes 1xx and 2xx) except tennis, **only the 79 present in all five
   years**: fixed membership, so federations entering the census late or missing a year (kick-boxing 2021,
   squash and twirling 2020) cannot pass for growth or for an extra COVID drop.
7. **QPV flag** from `Code QPV` (`QP…`/`QN…` = inside; `CSZ`/`HZ` = outside; `NR` = unallocated, excluded).
8. **Join population** (INSEE legal population, département sum of communes; 2022–23 → 2021).
9. **Pre-aggregate** to département × federation × sex × age group (~400k rows) so every filter runs in
   milliseconds; tennis keeps 5-year bands and commune detail.
10. **Geometry**: IGN département shapes simplified (tolerance 0.01°), overseas départements moved into
    insets west of the mainland.
""", f"""
1. **Téléchargement et cache** des cinq fichiers annuels (`download_data.py`, tailles vérifiées avec les
   métadonnées de data.gouv).
2. **Typage et validation** : identifiants gardés en texte (zéros initiaux, `2A/2B`), effectifs convertis en entiers
   avec comptage des cellules non numériques et négatives, sommes de lignes vérifiées, unicité des clés testée.
3. **Champ** : on garde `Statut géo = 1.Champ geoc` (métropole + Guadeloupe, Martinique, Guyane, La Réunion).
4. **Harmonisation** des colonnes sexe × âge entre années : 17 tranches de 5 ans × {{femmes, hommes, inconnu}},
   regroupées en 5 tranches d'âge pour les filtres.
5. **Clé fédération stable** à partir du nom normalisé, car l'INJEP a recodé {n_recoded} fédérations d'une année
   à l'autre ({recoded}).
6. **Référence** = fédérations unisport (codes 1xx et 2xx) hors tennis, **uniquement les 79 présentes les cinq
   années** : composition fixe, pour que les fédérations entrées tard ou absentes une année (kick-boxing 2021,
   squash et twirling 2020) ne passent ni pour de la croissance ni pour une chute COVID supplémentaire.
7. **Indicateur QPV** issu de `Code QPV` (`QP…`/`QN…` = dedans ; `CSZ`/`HZ` = dehors ; `NR` = non réparti, exclu).
8. **Jointure population** (population légale INSEE, somme des communes par département ; 2022–23 → 2021).
9. **Pré-agrégation** en département × fédération × sexe × tranche d'âge (~400 000 lignes) pour que chaque filtre
   réponde en quelques millisecondes ; le tennis garde les tranches de 5 ans et le détail communal.
10. **Géométrie** : contours IGN des départements simplifiés (tolérance 0,01°), départements d'outre-mer déplacés
    en encarts à l'ouest de la métropole.
"""))
    with st.expander(tr("Sources & licences", "Sources et licences")):
        s = SEEDS["sources"]
        st.markdown("\n".join(
            f"- **{v['producer']}** — [{v['dataset_page']}]({v['dataset_page']}) — {v['license']}"
            for v in s.values()))
        st.markdown(tr("Reuse under Licence Ouverte 2.0 requires attribution of the source and the date of last "
                       "update: *INJEP–MEDES, Recensement des licences et clubs sportifs, données géocodées "
                       "2019–2023 (mise à jour 29/12/2025)*. This dashboard aggregates counts; no individual-level "
                       "data exists in the source or is shown here.",
                       "La réutilisation sous Licence Ouverte 2.0 impose de citer la source et la date de dernière mise "
                       "à jour : *INJEP–MEDES, Recensement des licences et clubs sportifs, données géocodées 2019–2023 "
                       "(mise à jour 29/12/2025)*. Ce tableau de bord agrège des effectifs ; aucune donnée individuelle "
                       "n'existe dans la source ni n'est affichée ici."))
