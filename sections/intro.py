"""Section 1 — Hook & context: tennis came through COVID almost untouched, then grew."""
from __future__ import annotations

import streamlit as st

from utils import prep as A
from utils import viz
from utils.io import SEEDS
from utils.viz import cached, chart, insight, label, section, tr


def render_header(f: A.Filters) -> None:
    st.markdown(f'<p class="kicker">{tr("French open data · sports licences", "Open data français · licences sportives")}</p>',
                unsafe_allow_html=True)
    st.title("The Resilient Racket", anchor=False)
    st.markdown(tr(
        "#### COVID-19 emptied French sports clubs. Tennis barely noticed — and came out bigger. "
        "Who joined, where, and who is still missing?",
        "#### Le COVID-19 a vidé les clubs sportifs français. Le tennis l'a à peine senti — et en est sorti grandi. "
        "Qui l'a rejoint, où, et qui manque encore ?"))
    st.markdown(tr(
        "**Audience:** the French Tennis Federation (FFT), its regional leagues, and the local authorities "
        "that fund courts.  \n"
        "**Data:** every annual licence of every approved sports federation, by commune of residence, "
        "sex and age (INJEP census, 2019–2023, ~1 million rows per year).  \n"
        "Use the sidebar to change the period, the area, the sex and age groups, and the sport tennis "
        "is compared with. Every number and headline below updates.",
        "**Public :** la Fédération française de tennis (FFT), ses ligues régionales et les collectivités "
        "qui financent les courts.  \n"
        "**Données :** toutes les licences annuelles de toutes les fédérations agréées, par commune de résidence, "
        "sexe et âge (recensement INJEP, 2019–2023, ~1 million de lignes par an).  \n"
        "Utilisez la barre latérale pour changer la période, la zone, le sexe, les tranches d'âge et le sport "
        "comparé au tennis. Tous les chiffres et titres ci-dessous se mettent à jour."))


def render(d: A.Data, f: A.Filters) -> None:
    section("hook", tr("1 · Hook", "1 · Accroche"),
            tr("Tennis held its ground while sport collapsed", "Le tennis a tenu bon quand le sport s'effondrait"),
            tr("How did tennis fare through COVID compared with other sports?",
               "Comment le tennis a-t-il traversé le COVID par rapport aux autres sports ?"))

    s = cached("series", d, f)
    idx = A.indexed(s)
    k = cached("kpis", d, f)
    comp = d.fed_name(f.comparison)

    if k["trough_drop"] < 0:
        trough_txt = tr(
            f"At its worst point ({k['trough_year']}), tennis was <b>{k['trough_drop']:+.1f}%</b> below "
            f"{f.start}, against <b>{k['bench_trough_drop']:+.1f}%</b> for other single-sport federations. ",
            f"Au plus bas ({k['trough_year']}), le tennis était à <b>{k['trough_drop']:+.1f} %</b> sous son niveau "
            f"de {f.start}, contre <b>{k['bench_trough_drop']:+.1f} %</b> pour les autres fédérations unisport. ")
    else:
        trough_txt = tr(f"Tennis never fell below its {f.start} level in this period. ",
                        f"Le tennis n'est jamais passé sous son niveau de {f.start} sur la période. ")
    faster = k["gap_pp"] >= 0
    insight(trough_txt + tr(
        f"By {f.end}, tennis had grown <b>{k['tennis_growth']:+.1f}%</b>, {abs(k['gap_pp']):.1f} points "
        f"{'faster' if faster else 'slower'} than the other single-sport federations ({k['bench_growth']:+.1f}%).",
        f"En {f.end}, le tennis avait progressé de <b>{k['tennis_growth']:+.1f} %</b>, soit {abs(k['gap_pp']):.1f} points "
        f"{'de plus' if faster else 'de moins'} que les autres fédérations unisport ({k['bench_growth']:+.1f} %)."))

    alt = ""
    if comp in idx:
        alt = tr(
            f"Line chart of licences indexed to {f.start} = 100 for tennis, {comp} and all other single-sport "
            f"federations, {f.span}, {f.scope_label}. A grey band marks the COVID-19 seasons (2020–2021). "
            f"Tennis ends at {idx[A.TENNIS].iloc[-1]:.0f}, others at {idx[A.BENCH].iloc[-1]:.0f}, "
            f"{comp} at {idx[comp].iloc[-1]:.0f}.",
            f"Courbes des licences en base 100 en {f.start} pour le tennis, {comp} et l'ensemble des autres "
            f"fédérations unisport, {f.span}, {f.scope_label}. Une bande grise marque les saisons COVID-19 (2020–2021). "
            f"Le tennis finit à {idx[A.TENNIS].iloc[-1]:.0f}, les autres à {idx[A.BENCH].iloc[-1]:.0f}, "
            f"{comp} à {idx[comp].iloc[-1]:.0f}.")
    table = s.reset_index().rename(columns={"year": tr("Licence year", "Année de licence"),
                                            A.TENNIS: label(A.TENNIS), A.BENCH: label(A.BENCH)})
    chart(viz.index_chart(idx, s, f.start), alt=alt, table=table, key="index")

    with st.expander(tr("Why compare with *other single-sport federations* rather than *all sports*?",
                        "Pourquoi comparer aux *autres fédérations unisport* plutôt qu'à *tous les sports* ?")):
        st.markdown(tr(
            "The census also counts school sport (UNSS, USEP, UGSEL) and multi-sport federations. Their licences "
            "are often compulsory or bundled with school, and they fell 30–40% in 2021, which would make any "
            "club sport look resilient. The benchmark here is the **sum of all other single-sport federations** "
            "(Olympic and non-Olympic, tennis excluded), restricted to the 79 federations with data in all five "
            "years so the group is identical every year, and always with the same filters as tennis. "
            "The sport chosen in the sidebar is shown on its own line *and* stays inside that sum.",
            "Le recensement compte aussi le sport scolaire (UNSS, USEP, UGSEL) et les fédérations multisports. Leurs "
            "licences sont souvent obligatoires ou liées à l'école, et elles ont chuté de 30 à 40 % en 2021, ce qui "
            "ferait paraître résilient n'importe quel sport de club. La référence est donc la **somme de toutes les "
            "autres fédérations unisport** (olympiques et non olympiques, hors tennis), limitée aux 79 fédérations "
            "présentes les cinq années pour que le groupe soit identique chaque année, toujours avec les mêmes filtres "
            "que le tennis. Le sport choisi dans la barre latérale a sa propre courbe *et* reste inclus dans cette somme."))

    st.subheader(tr("Was tennis special, or were other sports spared too?",
                    "Le tennis est-il un cas à part, ou d'autres sports ont-ils été épargnés ?"), anchor=False)
    p = cached("peers", d, f, SEEDS["min_federation_size_for_comparison"] // 2)
    tennis_name = d.fed_name(d.tennis_key)
    if tennis_name not in set(p["name"]) or len(p) < 5:
        insight(tr("Too few licences in this selection to compare federations reliably — widen the area or period.",
                   "Trop peu de licences dans cette sélection pour comparer les fédérations — élargissez la zone "
                   "ou la période."))
        return
    t_worst = p.loc[p["name"] == tennis_name, "worst"].iloc[0]
    t_growth = p.loc[p["name"] == tennis_name, "growth"].iloc[0]
    rank_worst = int((p["worst"] > t_worst).sum()) + 1
    rank_growth = int((p["growth"] > t_growth).sum()) + 1
    better = p[p["worst"] > t_worst]["name"].tolist()
    n_min = f"{SEEDS['min_federation_size_for_comparison'] // 2:,}"
    if better:
        tail = tr(f"Only {', '.join(better[:4])}{' and others' if len(better) > 4 else ''} held up better.",
                  f"Seules {', '.join(better[:4])}{' et d’autres' if len(better) > 4 else ''} ont mieux résisté.")
    else:
        tail = tr("No large federation held up better.", "Aucune grande fédération n'a mieux résisté.")
    insight(tr(f"Among the {len(p)} largest single-sport federations (≥{n_min} licences nationally in 2019), "
               f"tennis ranks <b>#{rank_worst}</b> for resilience and <b>#{rank_growth}</b> for growth. ",
               f"Parmi les {len(p)} plus grandes fédérations unisport (≥{n_min} licences en France en 2019), "
               f"le tennis est <b>{rank_worst}ᵉ</b> pour la résilience et <b>{rank_growth}ᵉ</b> pour la croissance. ")
            + tail)
    chart(viz.peers_chart(p, tennis_name, comp),
          alt=tr("Scatter plot: each bubble is a single-sport federation; x = worst year versus start year (%), "
                 "y = end year versus start year (%), bubble size = licences at start. Tennis is orange, the "
                 f"comparison sport blue. Tennis sits at x={t_worst:.1f}%, y={t_growth:.1f}%.",
                 "Nuage de points : chaque bulle est une fédération unisport ; x = pire année vs année de départ (%), "
                 "y = année de fin vs année de départ (%), taille = licences au départ. Le tennis est en orange, le "
                 f"sport comparé en bleu. Le tennis est à x={t_worst:.1f} %, y={t_growth:.1f} %."),
          table=p[["name", "start", "end", "worst", "growth"]].round(1).rename(columns={
              "name": tr("Federation", "Fédération"), "start": f"Licences {f.start}", "end": f"Licences {f.end}",
              "worst": tr("Worst year vs start (%)", "Pire année vs départ (%)"),
              "growth": tr("End vs start (%)", "Fin vs départ (%)")}), key="peers")
    st.caption(tr("Correlation is not causation: the data shows *when* licences moved, not *why*. Plausible drivers "
                  "(outdoor play allowed earlier in lockdown, padel joining the FFT, post-COVID demand for individual "
                  "sport) are hypotheses, not findings.",
                  "Corrélation n'est pas causalité : les données montrent *quand* les licences ont bougé, pas *pourquoi*. "
                  "Les explications plausibles (jeu en extérieur autorisé plus tôt pendant le confinement, arrivée du "
                  "padel à la FFT, envie de sport individuel après le COVID) sont des hypothèses, pas des résultats."))
