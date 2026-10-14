# Dataset used

**Main dataset:** INJEP – *Données géocodées issues du recensement des licences et clubs auprès des fédérations sportives agréées par le ministère chargé des sports*
https://www.data.gouv.fr/datasets/donnees-geocodees-issues-du-recensement-des-licences-et-clubs-aupres-des-federations-sportives-agreees-par-le-ministere-charge-des-sports
Licence Ouverte / Open Licence 2.0 · producer INJEP–MEDES, geocoded by INSEE · last update 29/12/2025

Files used (downloaded and cached by `download_data.py`; not included in the zip because of their size, ~1.2 GB):

| Year | File | Bytes |
|---|---|---|
| 2019 | lic-data-2019.csv | 266,754,279 |
| 2020 | lic-data-2020.csv | 240,546,787 |
| 2021 | lic-data-2021.csv | 225,825,478 |
| 2022 | lic-data-2022.csv | 247,714,299 |
| 2023 | lic-data-2023.csv | 256,370,260 |

Direct URLs are in `seeds.json`. Data dictionary: `licences-dictionnaire-des-variables.xlsx` and `liste-federations.xlsx` on the same page.

**Auxiliary (join):** INSEE legal population by commune 2017–2021 — https://www.data.gouv.fr/datasets/populations-legales-communales-2017-2021
**Geometry:** IGN Admin Express via https://github.com/gregoiredavid/france-geojson

## Raw variables (2019–2023 format)

| Column | Meaning |
|---|---|
| Code Commune / Commune | INSEE commune code / name of the licence holder's residence (`NR - Non réparti` = not allocated) |
| Code QPV / Nom QPV | Priority-neighbourhood code (`QP…` 2015 list, `QN…` 2024 list), `CSZ` commune without QPV, `HZ` outside QPV in a commune with QPV, `NR` not allocated |
| Département / Région | Département code and region name |
| Statut géo | `1.Champ geoc` geocoded (in scope) / `2.Hors Champ geoc` Mayotte, COM, Monaco, abroad |
| Code / Fédération | Federation code (tennis = 123) and name |
| `F - 10 à 14 ans`, `H - …`, `NR - …` | Licences by sex (F women, H men, NR unknown) and 5-year age band |
| Total | Total annual licences |

## Processed tables shipped in `data/processed/`

| Table | Grain | Rows |
|---|---|---|
| fed_long | year × département × federation × sex × age group | 398,109 |
| fed_qpv | year × département × federation × QPV status | 81,953 |
| tennis_age | year × département × sex × 5-year age band (tennis) | 17,168 |
| tennis_commune | year × commune (tennis), licences and women | 137,583 |
| scope | year × federation × geocoding status (national) | 1,078 |
| federations | federation reference (stable key, latest code/name, size by year, family) | 119 |
| departments | code, name, region, overseas flag | 100 |
| population | year × département legal population | 500 |
| quality_report.json | every validation check, per file and across tables | — |
