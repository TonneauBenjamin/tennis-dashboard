# 🎾 The Resilient Racket — French tennis licences, 2019–2023

**COVID-19 emptied French sports clubs. Tennis barely noticed, and came out bigger. Who joined, where, and who is still missing?**

An interactive Streamlit data story built on the official INJEP census of sports licences (data.gouv.fr).

- **Live app:** `<add Streamlit Community Cloud URL>`
- **Demo video (3 min):** `<add video link>`
- **Author:** Clément Tonneau · student ID 20230792 · group I2-DE_01 · EFREI Paris, Data Visualization 2026 (#EFREIDataStories2026)

---

## 1. The story

| | |
|---|---|
| **Audience** | French Tennis Federation (FFT) and its regional leagues; local authorities that fund courts |
| **Problem** | COVID-19 closures cut sports licences in France by a fifth. Did tennis suffer like other sports, and who drove what happened next? |
| **Narrative pattern** | Before/after change over time, plus group/region comparison, plus ranking & distribution |

**Key insights (France, 2019 → 2023, geocoded scope):**

1. **Resilience.** At the COVID low (2021) tennis was **−3.2%** below 2019, against **−17.1%** for all other single-sport federations combined. Among the 35 largest single-sport federations it ranks **#4 for resilience** (after equestrian, rugby and shooting) and **#6 for growth**.
2. **Growth.** By 2023 tennis reached **1,096,180** licences: **+13.2%**, against **+3.9%** for the benchmark.
3. **Who.** **Young adults (20–34) grew +34.9%** against +2.3% in other sports. They were 11% of tennis licences in 2019 but brought **29% of the net new licences**. Among them, women's share *fell* from 29.1% to 26.2%.
4. **Gender gap unchanged.** Women's share stayed at **29.8%** (+0.4 pt), below the 33.6% of other single-sport federations: about 2.4 men per woman.
5. **Where.** Density ranges **8×**, from 31.5 licences per 1,000 residents (Hauts-de-Seine) to 3.9 (Guyane). Growth was strongest in Pyrénées-Orientales (+64%); Territoire de Belfort fell 23%.
6. **Who is missing.** Residents of priority neighbourhoods (QPV) hold **2.2%** of tennis licences, against **4.7%** in other single-sport federations (2.2× less).

**Implications:** plan court capacity for adult peak-hour demand; target investment by per-capita demand and growth; the next growth pools are women and QPV residents. The dashboard's *Limitations* section lists what these numbers cannot say (padel is inside tennis licences, licences ≠ players, no causality).

### Storyboard

| # | Section | Question | Visuals & interactions |
|---|---|---|---|
| — | KPI header | What is the state of tennis in the selection? | 5 KPIs (licences, gap vs benchmark, worst year, per 1,000, women's share), all filter-aware |
| 1 | **Hook** | How did tennis fare through COVID compared with other sports? | Indexed line chart (2019 = 100) with COVID band and comparison sport; resilience vs recovery bubble chart of 35 federations |
| 2 | **Where** | Where is tennis played most, and where did it grow? | Choropleth (per 1,000 / growth / women's share, chosen in the sidebar) + top/bottom-10 ranking + commune drill-down table |
| 3 | **Who** | Which age groups drove growth; did the gender gap close? | Age–sex pyramid (end-year bars, start-year ticks); growth by age group vs benchmark; women's share over time |
| 4 | **Who is missing** | Do QPV residents take part as much as in other sports? | Ranked bar chart of QPV share for 23 federations; QPV trend with 2023 definition break |
| 5 | **So what?** | What should clubs and policymakers do? | 3 data-driven implications, limitations, next steps |
| A | **Data quality** | Can the numbers be trusted? | Validation table per file, missingness, scope chart, cross-table checks, pipeline, sources & licences |

Every section opens with **one headline insight sentence computed from the filtered data**, so the story stays true when the reader changes filters.

**Sidebar controls:** period (licence years), region, département, sex, age groups, comparison sport, map variable.

---

## 2. Data

| Source | Producer | Use | Licence |
|---|---|---|---|
| [Données géocodées issues du recensement des licences et clubs auprès des fédérations sportives agréées](https://www.data.gouv.fr/datasets/donnees-geocodees-issues-du-recensement-des-licences-et-clubs-aupres-des-federations-sportives-agreees-par-le-ministere-charge-des-sports) — files `lic-data-2019` … `lic-data-2023` | INJEP–MEDES (Ministry of Sports), geocoded by INSEE; last update 29/12/2025 | Main dataset: licences by commune × QPV × federation × sex × age | Licence Ouverte 2.0 |
| [Populations légales communales 2017–2021](https://www.data.gouv.fr/datasets/populations-legales-communales-2017-2021) | INSEE, republished by icem7 | Denominator for licences per 1,000 residents | Licence Ouverte 2.0 |
| [france-geojson](https://github.com/gregoiredavid/france-geojson) (`departements-avec-outre-mer`) | IGN Admin Express 2018 | Département shapes for the map | Licence Ouverte |

Exact URLs and byte sizes are in `seeds.json`. See `DATASET.md` for the variable dictionary.

**Scope.** Licence year *N* = FFT season *N-1/N*. 2019–2023 only: the file format changed in 2019 (commune-QPV level, new age bands), so earlier years are not comparable. "Geocoded scope" = mainland France + Guadeloupe, Martinique, Guyane and La Réunion. Mayotte, overseas collectivities, Monaco and abroad (≈1.7% of all licences, ≈1% of tennis) are excluded from maps and rates.

### Pipeline (`download_data.py` → `utils/prep.py`)

1. **Download & cache** five ~250 MB CSVs and two auxiliary files; sizes checked against data.gouv metadata; atomic writes; skipped if already present.
2. **Type & validate**: identifiers read as text (keeps `01`, `2A`), counts coerced to integers. Recorded per file: non-numeric cells, negative cells, rows where sex × age ≠ total, duplicate keys, missing identifiers, unknown sex/age, out-of-scope share.
3. **Harmonise** sex × age columns (2019–2021 carry extra "unknown sex" columns): 17 five-year bands × {women, men, unknown} → 5 age groups.
4. **Stable federation key** from the normalised name: INJEP re-coded 6 federations between years (squash, karate, dance, American football, baseball, alpine clubs).
5. **Features**: QPV flag (`QP…`/`QN…` inside, `CSZ`/`HZ` outside, `NR` unallocated); benchmark = all single-sport federations (codes 1xx/2xx) except tennis; population join (2022–23 use 2021).
6. **Pre-aggregate** to département × federation × sex × age group (~400k rows), plus tennis detail (5-year bands, communes).
7. **Geometry**: simplify shapes (0.01°) and move the overseas départements into insets.
8. **Cross-checks**: tennis totals are identical across the four derived tables and equal to the raw in-scope total, every year.

**Validation results (all files):** 0 non-numeric or negative counts, 0 rows where sex × age ≠ total, 0 duplicate keys. A naive commune+QPV key would suggest ~700 duplicates per year: they are out-of-scope rows, one per overseas territory, and disappear once the département is in the key. Full report: `data/processed/quality_report.json`, displayed in the app's *Data quality* section.

---

## 3. Run it

Requires **Python 3.10–3.13**. The processed data (2.5 MB) ships with the project, so the app runs from a clean checkout without downloading 1.2 GB.

macOS / Linux:

```bash
cd tennis-dashboard
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py          # opens http://localhost:8501
```

Windows: replace `.venv/bin/` with `.venv\Scripts\`.

Rebuild all processed data from the official raw files (~2–3 min, ~3 GB RAM):

```bash
.venv/bin/python download_data.py                       # downloads to data/raw/ (cached), rewrites data/processed/ and assets/
.venv/bin/python download_data.py --raw-dir /my/folder  # same, from CSVs already on disk (no download)
```

**Deploy (Streamlit Community Cloud):** push the folder to GitHub → share.streamlit.io → *Create app* → main file `app.py`, Python 3.12 (Advanced settings) → Deploy.

---

## 4. Project structure (follows the recommended structure of the brief)

```
app.py                page config, cached loading, sidebar filters, KPI header, section order
sections/
  intro.py            context, audience, 1 · Hook (COVID resilience vs other sports)
  overview.py         2 · Where (map, top/bottom ranking, commune drill-down)
  deep_dives.py       3 · Who (age, sex) and 4 · Who is missing (priority neighbourhoods)
  conclusions.py      5 · So what? (implications, limitations, next steps) + data-quality appendix
utils/
  io.py               constants from seeds.json, cached downloads (fetch_raw), loaders, licence sources
  prep.py             cleaning, validation, feature engineering, quality report, filter-aware tables
  viz.py              chart functions with one consistent style + page building blocks
data/processed/       8 parquet tables + quality_report.json (2.5 MB)
data/raw/             raw downloads, created by download_data.py (not shipped)
assets/               simplified département GeoJSON for the map
download_data.py      data download script (with caching) → cleaning → validation → processed tables
seeds.json            constants: source URLs and sizes, age groups, colours, seed
requirements.txt      pinned dependencies
STORYBOARD.md         storyboard
DATASET.md            dataset links and variable dictionary
```

## 5. Engineering notes

- **Performance:** raw files are never read by the app. Parquet tables are loaded once (`st.cache_data`) and every aggregation is memoised on the (hashable, frozen) filter object; a full render of all sections takes ~2–3 s on a cold cache and well under 1 s once cached.
- **Separation of concerns:** the aggregations in `prep.py` have no Streamlit dependency, so every number in the app can be reproduced in a notebook.
- **No external runtime calls:** the map uses Plotly's MapLibre trace with a blank style, so it needs no tile server, token or CDN.
- **Reproducibility:** exact pins, constants in `seeds.json`, deterministic pipeline (no sampling; the seed is recorded for completeness). Tested from a clean environment on Python 3.10 and 3.13; processed outputs verified identical under pandas 2.2 and 3.0.

## 6. Design & accessibility

- Colour roles: tennis = clay orange `#eb6834`, comparison sport = blue `#2a78d6`, benchmark = neutral grey (context). Women/men = violet/aqua. Validated for colour-vision deficiency (ΔE ≥ 9.8 across all pairs). Every line is **direct-labelled**, so identity never relies on colour alone.
- Sequential blue ramp for magnitudes; diverging red–grey–blue for growth (grey = 0).
- Every chart has a **text description** (alt text) and a **"Show the data" table view**; axes carry titles and units; COVID and the QPV definition change are annotated on the charts.

## 7. Ethics & limitations

- Aggregated counts only; the source contains no individual-level data.
- Licences ≠ players; padel is counted inside tennis (FFT); place of residence, not of play; commune values are INSEE estimates; QPV is a neighbourhood proxy, not individual income; the 2023 QPV map change breaks the series; population for 2022–23 is the 2021 figure (rates overstated by <1%).
- The dashboard shows **co-movement, not causation**. Explanations such as outdoor play during lockdown or the rise of padel are flagged as hypotheses.

*Attribution (Licence Ouverte 2.0): INJEP–MEDES, Recensement des licences et clubs sportifs — données géocodées 2019–2023 (mise à jour 29/12/2025); INSEE, Populations légales; IGN, Admin Express.*
