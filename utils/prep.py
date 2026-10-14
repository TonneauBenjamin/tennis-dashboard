"""Cleaning, validation, feature engineering, and the filter-aware tables used by the app.

Turns the five raw INJEP files (one row per commune × QPV × federation, 45–55 columns)
into small tidy tables the app can filter instantly, and records every validation
check in data/processed/quality_report.json.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from utils.io import (AGE_GROUPS, BAND_TO_GROUP, DATA_PROCESSED, GEOJSON_PATH, ID_COLS,
                      IN_SCOPE, POP_LAST_YEAR, QUALITY_PATH, SEEDS, TENNIS_CODE, YEARS)

SEXAGE_RE = re.compile(r"^(F|H|NR) - (.+?)(?: ans)?$")
KEY = ["Département", "Code Commune", "Code QPV", "Code"]


# ------------------------------------------------------------------ helpers
def parse_sexage(col: str) -> tuple[str, str]:
    """'F - 10 à 14 ans' -> ('F', '10 à 14'); 'H - NR' -> ('H', 'NR'); 'NR - NR' -> ('NR', 'NR')."""
    m = SEXAGE_RE.match(col)
    if not m:
        raise ValueError(f"Unexpected column: {col!r}")
    return m.group(1), m.group(2)


def fed_key(name: str) -> str:
    """Stable federation key. INJEP re-codes some federations between years
    (e.g. squash 252 -> 141 when it became Olympic), so names are the stable identifier."""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def fed_family(code: str) -> str:
    return {"1": "Single-sport (Olympic)", "2": "Single-sport (non-Olympic)", "4": "Multi-sport",
            "5": "Disability sport", "6": "School & university"}.get(str(code)[0], "Other")


def qpv_class(code: pd.Series) -> pd.Series:
    """QPV = 'quartier prioritaire de la politique de la ville' (deprived urban neighbourhood)."""
    c = code.fillna("").str[:2]
    return np.select([c.isin(["QP", "QN"]), c.isin(["CS", "HZ"])],
                     ["In QPV", "Outside QPV"], default="Unallocated")


# ------------------------------------------------------------------ one year
def read_year(path: Path, year: int) -> tuple[pd.DataFrame, list[str], dict]:
    """Read one raw file, coerce counts to integers and run row-level checks."""
    df = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig")
    value_cols = [c for c in df.columns if c not in ID_COLS]
    sexage_cols = [c for c in value_cols if c != "Total"]
    missing_id_cols = [c for c in ID_COLS if c not in df.columns]

    q: dict = {"year": year, "rows": int(len(df)), "columns": int(df.shape[1]),
               "sex_age_columns": len(sexage_cols), "missing_id_columns": missing_id_cols}
    q["missing_values"] = {c: int(df[c].isna().sum()) for c in ID_COLS if c in df.columns}

    non_numeric = 0
    for c in value_cols:
        num = pd.to_numeric(df[c], errors="coerce")
        non_numeric += int((num.isna() & df[c].notna()).sum())
        df[c] = num.fillna(0).astype("int64")
    q["non_numeric_cells"] = non_numeric
    q["negative_cells"] = int((df[value_cols] < 0).sum().sum())
    q["missing_count_cells"] = 0 if non_numeric == 0 else non_numeric

    rowsum = df[sexage_cols].sum(axis=1)
    q["rows_where_sex_age_sum_differs_from_total"] = int((rowsum != df["Total"]).sum())
    q["duplicate_keys"] = int(df.duplicated(KEY).sum())
    q["naive_duplicates_commune_qpv_only"] = int(df.duplicated(["Code Commune", "Code QPV", "Code"]).sum())

    q["licences_total"] = int(df["Total"].sum())
    scope = df.groupby("Statut géo")["Total"].sum()
    q["licences_out_of_scope"] = int(scope.drop(IN_SCOPE, errors="ignore").sum())
    q["share_out_of_scope_pct"] = round(100 * q["licences_out_of_scope"] / q["licences_total"], 2)
    unalloc = df["Code QPV"].fillna("").str.startswith("NR") & (df["Statut géo"] == IN_SCOPE)
    q["licences_in_scope_unallocated_to_commune"] = int(df.loc[unalloc, "Total"].sum())

    sex = pd.Series({c: parse_sexage(c)[0] for c in sexage_cols})
    age = pd.Series({c: parse_sexage(c)[1] for c in sexage_cols})
    q["licences_unknown_sex"] = int(df[sex[sex == "NR"].index].sum().sum())
    q["licences_unknown_age"] = int(df[age[age == "NR"].index].sum().sum())

    t = df[df["Code"] == TENNIS_CODE]
    q["tennis_licences"] = int(t["Total"].sum())
    q["tennis_rows"] = int(len(t))
    q["tennis_communes"] = int(t.loc[t["Statut géo"] == IN_SCOPE, "Code Commune"].nunique())
    q["tennis_federation_names"] = sorted(t["Fédération"].dropna().unique().tolist())
    q["federations"] = int(df["Code"].nunique())
    q["federations_with_duplicate_names"] = int(
        (df.groupby("Fédération")["Code"].nunique() > 1).sum())

    df["year"] = year
    return df, sexage_cols, q


def to_long(wide: pd.DataFrame, index: list[str], sexage_cols: list[str]) -> pd.DataFrame:
    """Melt sex × age columns into (sex, age_band, licences) rows, dropping zeros."""
    long = wide.melt(id_vars=index, value_vars=sexage_cols, var_name="col", value_name="licences")
    long = long[long["licences"] > 0]
    parsed = long["col"].map(parse_sexage)
    long["sex"] = parsed.str[0]
    long["age_band"] = parsed.str[1]
    return long.drop(columns="col")


def build_year(df: pd.DataFrame, sexage_cols: list[str], year: int) -> dict[str, pd.DataFrame]:
    ins = df[df["Statut géo"] == IN_SCOPE].copy()
    ins["fed_key"] = ins["Fédération"].map(fed_key)
    ins["female"] = ins[[c for c in sexage_cols if c.startswith("F - ")]].sum(axis=1)

    # all federations: département × federation × sex × age group (for benchmarks under any filter)
    by_dep = ins.groupby(["Département", "fed_key"], as_index=False)[sexage_cols].sum()
    fl = to_long(by_dep, ["Département", "fed_key"], sexage_cols)
    fl["age_group"] = fl["age_band"].map(BAND_TO_GROUP).fillna("Unknown")
    fed_long = fl.groupby(["Département", "fed_key", "sex", "age_group"], as_index=False)["licences"].sum()

    # QPV split (residence inside/outside deprived neighbourhoods)
    ins["qpv"] = qpv_class(ins["Code QPV"])
    fed_qpv = ins.groupby(["Département", "fed_key", "qpv"], as_index=False)["Total"].sum() \
                 .rename(columns={"Total": "licences"})

    # tennis detail: fine age bands, and commune totals
    ten = ins[ins["Code"] == TENNIS_CODE]
    tdep = ten.groupby("Département", as_index=False)[sexage_cols].sum()
    tennis_age = to_long(tdep, ["Département"], sexage_cols)
    tennis_age = tennis_age.groupby(["Département", "sex", "age_band"], as_index=False)["licences"].sum()
    tennis_commune = (ten[~ten["Code Commune"].str.startswith("NR")]
                      .groupby(["Département", "Code Commune", "Commune"], as_index=False)
                      .agg(licences=("Total", "sum"), women=("female", "sum")))

    # national scope check incl. out-of-scope rows (Mayotte, COM, abroad)
    df = df.assign(fed_key=df["Fédération"].map(fed_key))
    scope = df.groupby(["fed_key", "Statut géo"], as_index=False)["Total"].sum() \
              .rename(columns={"Total": "licences", "Statut géo": "status"})

    names = ins.drop_duplicates("fed_key")[["fed_key", "Code", "Fédération"]]
    regions = ins.dropna(subset=["Région"]).drop_duplicates("Département")[["Département", "Région"]]

    out = {"fed_long": fed_long, "fed_qpv": fed_qpv, "tennis_age": tennis_age,
           "tennis_commune": tennis_commune, "scope": scope, "names": names, "regions": regions}
    for k, v in out.items():
        out[k] = v.assign(year=year)
    return out


# ------------------------------------------------------------------ population & geometry
def build_population(path: Path) -> tuple[pd.DataFrame, dict]:
    pop = pd.read_parquet(path)
    pop["annee_rp"] = pop["annee_rp"].astype(int)
    dep = pop.groupby(["coddep", "annee_rp"], as_index=False)["pmun"].sum()
    rows = []
    for y in YEARS:
        py = min(y, POP_LAST_YEAR)
        d = dep[dep["annee_rp"] == py].rename(columns={"coddep": "dep", "pmun": "population"})
        rows.append(d.assign(year=y, population_year=py)[["year", "dep", "population", "population_year"]])
    out = pd.concat(rows, ignore_index=True)
    q = {"departments": int(out["dep"].nunique()), "population_years_used": sorted(set(out["population_year"])),
         "france_population_2021": int(dep.loc[dep["annee_rp"] == 2021, "pmun"].sum())}
    return out, q


def build_geometry(path: Path, keep_codes: set[str]) -> tuple[dict, pd.DataFrame]:
    """Simplify département shapes and move overseas départements into insets west of the mainland."""
    from shapely.affinity import scale, translate
    from shapely.geometry import mapping, shape

    with open(path, encoding="utf-8") as fh:
        gj = json.load(fh)
    insets = {k: v for k, v in SEEDS["overseas_insets"].items() if not k.startswith("_")}
    feats, names = [], []
    for f in gj["features"]:
        code, name = f["properties"]["code"], f["properties"]["nom"]
        if code not in keep_codes:
            continue
        geom = shape(f["geometry"])
        if code in insets:
            x0, y0, x1, y1 = geom.bounds
            bx0, by0, bx1, by1 = insets[code]
            k = min((bx1 - bx0) / (x1 - x0), (by1 - by0) / (y1 - y0))
            geom = scale(geom, xfact=k, yfact=k, origin=(x0, y0))
            geom = translate(geom, xoff=bx0 - x0, yoff=by0 - y0)
        geom = geom.simplify(0.01, preserve_topology=True)
        m = json.loads(json.dumps(mapping(geom)), parse_float=lambda s: round(float(s), 3))
        feats.append({"type": "Feature", "properties": {"code": code, "nom": name,
                                                         "overseas": code in insets}, "geometry": m})
        names.append({"dep": code, "dep_name": name})
    return {"type": "FeatureCollection", "features": feats}, pd.DataFrame(names)


# ------------------------------------------------------------------ pipeline
def run(raw: dict[str, Path], out_dir: Path = DATA_PROCESSED) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: dict[str, list[pd.DataFrame]] = {}
    quality: dict = {"years": []}
    for y in YEARS:
        print(f"  processing {y} …", flush=True)
        df, sexage_cols, q = read_year(raw[f"lic_{y}"], y)
        quality["years"].append(q)
        for k, v in build_year(df, sexage_cols, y).items():
            parts.setdefault(k, []).append(v)
        del df
    t = {k: pd.concat(v, ignore_index=True) for k, v in parts.items()}

    # federation reference table: latest code/name per stable key
    names = t["names"].sort_values("year").groupby("fed_key").last().reset_index()
    sizes = t["fed_long"].groupby(["fed_key", "year"])["licences"].sum().unstack(fill_value=0)
    feds = names.merge(sizes, left_on="fed_key", right_index=True, how="left")
    feds = feds.rename(columns={"Code": "code", "Fédération": "name"})
    feds["family"] = feds["code"].map(fed_family)
    feds["single_sport"] = feds["code"].str[0].isin(["1", "2"])
    feds["years_present"] = feds[YEARS].gt(0).sum(axis=1)
    code_changes = (t["names"].groupby("fed_key")["Code"].nunique() > 1)
    feds["code_changed"] = feds["fed_key"].map(code_changes).fillna(False)
    feds.columns = [str(c) for c in feds.columns]

    # départements: names from geometry, region from licence file
    pop, qpop = build_population(raw["population"])
    deps_in_data = set(t["fed_long"]["Département"])
    geo, depnames = build_geometry(raw["geometry"], deps_in_data)
    regions = t["regions"].sort_values("year").groupby("Département").last().reset_index()
    deps = depnames.merge(regions.rename(columns={"Département": "dep", "Région": "region"})[["dep", "region"]],
                          on="dep", how="outer")
    deps["overseas"] = deps["dep"].str.len() == 3

    rename = {"Département": "dep", "Code Commune": "commune_code", "Commune": "commune"}
    tables = {
        "fed_long": t["fed_long"].rename(columns=rename),
        "fed_qpv": t["fed_qpv"].rename(columns=rename),
        "tennis_age": t["tennis_age"].rename(columns=rename),
        "tennis_commune": t["tennis_commune"].rename(columns=rename),
        "scope": t["scope"],
        "federations": feds,
        "departments": deps,
        "population": pop,
    }
    cats = {"dep", "fed_key", "sex", "age_group", "qpv", "age_band", "status"}
    for name, df in tables.items():
        for c in df.columns:
            if c in cats:
                df[c] = df[c].astype("category")
            elif c in ("licences", "women", "population"):
                df[c] = df[c].astype("int32")
            elif c == "year":
                df[c] = df[c].astype("int16")
        df.to_parquet(out_dir / f"{name}.parquet", index=False)

    GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GEOJSON_PATH, "w", encoding="utf-8") as fh:
        json.dump(geo, fh, separators=(",", ":"))

    # ---------------------------------------------- cross-table validation checks
    tkey = feds.loc[feds["code"] == TENNIS_CODE, "fed_key"].iloc[0]
    checks = []
    for y in YEARS:
        qy = next(q for q in quality["years"] if q["year"] == y)
        a = int(tables["fed_long"].query("year == @y and fed_key == @tkey")["licences"].sum())
        b = int(tables["tennis_age"].query("year == @y")["licences"].sum())
        c = int(tables["fed_qpv"].query("year == @y and fed_key == @tkey")["licences"].sum())
        expected = qy["tennis_licences"] - int(tables["scope"].query(
            "year == @y and fed_key == @tkey and status != @IN_SCOPE")["licences"].sum())
        checks.append({"year": y, "tennis_in_scope_expected": expected,
                       "fed_long": a, "tennis_age": b, "fed_qpv": c, "consistent": a == b == c == expected})
    missing_pop = sorted(deps_in_data - set(pop["dep"]))
    missing_geo = sorted(deps_in_data - set(depnames["dep"]))
    quality["cross_checks"] = checks
    quality["population"] = qpop | {"departments_without_population": missing_pop}
    quality["geometry"] = {"departments_without_shape": missing_geo, "features": len(geo["features"])}
    quality["federations_recoded_between_years"] = feds.loc[feds["code_changed"], "name"].tolist()
    quality["processed_bytes"] = {f.name: f.stat().st_size for f in sorted(out_dir.glob("*.parquet"))}
    with open(QUALITY_PATH, "w", encoding="utf-8") as fh:
        json.dump(quality, fh, indent=2, ensure_ascii=False, default=str)
    return quality


# ==================================================================
# make_tables: filter-aware aggregations used by the sections.
# No Streamlit calls here, so every number can be reproduced in a notebook.
# ==================================================================
TENNIS = "Tennis"
BENCH = "Other single-sport federations"
ALL_GROUPS = list(AGE_GROUPS)


@dataclass(frozen=True)
class Filters:
    start: int
    end: int
    deps: tuple[str, ...]            # selected département codes (all by default)
    sex: str = "All"                 # "All" | "F" | "H"
    ages: tuple[str, ...] = tuple(ALL_GROUPS)
    comparison: str = "ff de football"
    scope_label: str = "France"

    @property
    def span(self) -> str:
        return f"{self.start}→{self.end}"


@dataclass
class Data:
    fed_long: pd.DataFrame
    fed_qpv: pd.DataFrame
    tennis_age: pd.DataFrame
    tennis_commune: pd.DataFrame
    scope: pd.DataFrame
    federations: pd.DataFrame
    departments: pd.DataFrame
    population: pd.DataFrame

    @property
    def tennis_key(self) -> str:
        return self.federations.loc[self.federations["code"] == TENNIS_CODE, "fed_key"].iloc[0]

    @property
    def bench_keys(self) -> set[str]:
        f = self.federations
        return set(f.loc[f["single_sport"] & (f["code"] != TENNIS_CODE), "fed_key"])

    def fed_name(self, key: str) -> str:
        n = str(self.federations.set_index("fed_key")["name"].get(key, key))
        n = re.sub(r"^(FF|F|Fédération française)\s+(de la |de l'|du |des |de |d'|d’)?", "", n).strip()
        return n[:1].upper() + n[1:]


# ------------------------------------------------------------------ filtering
def _years(f: Filters) -> list[int]:
    return list(range(f.start, f.end + 1))


def filter_long(d: Data, f: Filters, sex: bool = True, ages: bool = True) -> pd.DataFrame:
    df = d.fed_long
    m = df["year"].between(f.start, f.end) & df["dep"].isin(f.deps)
    if sex and f.sex != "All":
        m &= df["sex"] == f.sex
    if ages and set(f.ages) != set(ALL_GROUPS):
        m &= df["age_group"].isin(f.ages)
    return df[m]


def label_groups(d: Data, df: pd.DataFrame, comparison: str | None) -> pd.Series:
    """Map fed_key -> Tennis / comparison sport / benchmark / None (excluded)."""
    t, b = d.tennis_key, d.bench_keys
    keys = df["fed_key"].astype(str)
    out = pd.Series(np.where(keys == t, TENNIS, np.where(keys.isin(b), BENCH, None)), index=df.index)
    if comparison and comparison != t:
        out = out.where(keys != comparison, d.fed_name(comparison))
    return out


def series(d: Data, f: Filters) -> pd.DataFrame:
    """Licences per year for Tennis, the benchmark and the comparison sport (comparison is also
    kept inside the benchmark total, which is a fixed population of federations)."""
    df = filter_long(d, f)
    g = df.groupby(["year", "fed_key"], observed=True)["licences"].sum().reset_index()
    keys = g["fed_key"].astype(str)
    rows = [g[keys == d.tennis_key].assign(group=TENNIS),
            g[keys.isin(d.bench_keys)].assign(group=BENCH)]
    if f.comparison != d.tennis_key:
        rows.append(g[keys == f.comparison].assign(group=d.fed_name(f.comparison)))
    s = pd.concat(rows).groupby(["group", "year"], as_index=False)["licences"].sum()
    s = s.pivot(index="year", columns="group", values="licences").reindex(_years(f)).fillna(0)
    return s


def indexed(s: pd.DataFrame) -> pd.DataFrame:
    base = s.iloc[0].replace(0, np.nan)
    return s.div(base) * 100


def pct(a: float, b: float) -> float:
    return (b / a - 1) * 100 if a else np.nan


# ------------------------------------------------------------------ KPIs
def population(d: Data, f: Filters, year: int) -> int:
    p = d.population
    return int(p.loc[(p["year"] == year) & p["dep"].isin(f.deps), "population"].sum())


def women_share(d: Data, f: Filters, which: str = "tennis") -> pd.Series:
    """Women / (women + men) per year, ignoring the sex filter (unknown sex excluded).
    `which` = "tennis", "bench" or a federation key."""
    df = filter_long(d, f, sex=False)
    keys = df["fed_key"].astype(str)
    sel = keys.isin(d.bench_keys) if which == "bench" else keys == (d.tennis_key if which == "tennis" else which)
    df = df[sel & df["sex"].isin(["F", "H"])]
    g = df.groupby(["year", "sex"], observed=True)["licences"].sum().unstack()
    return (g["F"] / (g["F"] + g["H"]) * 100).reindex(_years(f))


def kpis(d: Data, f: Filters) -> dict:
    s = series(d, f)
    t0, t1 = s[TENNIS].iloc[0], s[TENNIS].iloc[-1]
    b0, b1 = s[BENCH].iloc[0], s[BENCH].iloc[-1]
    p0, p1 = population(d, f, f.start), population(d, f, f.end)
    ws = women_share(d, f, "tennis")
    trough_year = int(s[TENNIS].idxmin())
    return {
        "tennis_end": t1, "tennis_growth": pct(t0, t1),
        "bench_growth": pct(b0, b1), "gap_pp": pct(t0, t1) - pct(b0, b1),
        "per1000_end": t1 / p1 * 1000 if p1 else np.nan,
        "per1000_start": t0 / p0 * 1000 if p0 else np.nan,
        "women_end": ws.iloc[-1], "women_delta": ws.iloc[-1] - ws.iloc[0],
        "trough_year": trough_year, "trough_drop": pct(t0, s[TENNIS].min()),
        "bench_trough_drop": pct(b0, s[BENCH].min()),
    }


# ------------------------------------------------------------------ peers (resilience scatter)
def peer_keys(d: Data, min_size: int) -> set[str]:
    """Fixed peer set, defined nationally (2019 size), so rankings do not change membership with filters."""
    f = d.federations
    return set(f.loc[f["single_sport"] & (f["2019"] >= min_size), "fed_key"]) | {d.tennis_key}


def peers(d: Data, f: Filters, min_size: int) -> pd.DataFrame:
    """Single-sport federations: worst year vs start (COVID drop) and end vs start (recovery)."""
    df = filter_long(d, f)
    df = df[df["fed_key"].astype(str).isin(peer_keys(d, min_size))]
    g = df.groupby(["fed_key", "year"], observed=True)["licences"].sum().unstack().reindex(columns=_years(f))
    g = g[g.notna().all(axis=1) & (g[f.start] > 0)]
    g.index = g.index.astype(str)
    out = pd.DataFrame({
        "fed_key": g.index.astype(str),
        "start": g[f.start].values, "end": g[f.end].values,
        "worst": (g.min(axis=1) / g[f.start] - 1).values * 100,
        "growth": (g[f.end] / g[f.start] - 1).values * 100,
    })
    out["name"] = out["fed_key"].map(d.fed_name)
    return out.sort_values("start", ascending=False)


# ------------------------------------------------------------------ geography
def by_department(d: Data, f: Filters) -> pd.DataFrame:
    """Tennis level, growth and women's share per département (all départements, flag selection)."""
    df = d.fed_long
    m = (df["fed_key"].astype(str) == d.tennis_key) & df["year"].isin([f.start, f.end])
    if set(f.ages) != set(ALL_GROUPS):
        m &= df["age_group"].isin(f.ages)
    t = df[m]
    sel = t if f.sex == "All" else t[t["sex"] == f.sex]
    lic = sel.groupby(["dep", "year"], observed=True)["licences"].sum().unstack(fill_value=0)
    lic = lic.reindex(columns=[f.start, f.end], fill_value=0)
    fh = t[t["sex"].isin(["F", "H"]) & (t["year"] == f.end)].groupby(["dep", "sex"], observed=True)["licences"].sum().unstack(fill_value=0)
    pop = d.population[d.population["year"] == f.end].set_index("dep")["population"]
    out = d.departments.set_index("dep").copy()
    out.index = out.index.astype(str)
    lic.index = lic.index.astype(str); fh.index = fh.index.astype(str); pop.index = pop.index.astype(str)
    out["licences_start"] = lic[f.start]
    out["licences_end"] = lic[f.end]
    out["population"] = pop
    out["per1000"] = out["licences_end"] / out["population"] * 1000
    out["growth"] = (out["licences_end"] / out["licences_start"] - 1) * 100
    out["women_share"] = fh.get("F", 0) / (fh.get("F", 0) + fh.get("H", 0)) * 100
    out["selected"] = out.index.isin(f.deps)
    return out.reset_index()


def communes(d: Data, f: Filters, dep: str, n: int = 15) -> pd.DataFrame:
    c = d.tennis_commune
    c = c[(c["dep"].astype(str) == dep) & c["year"].isin([f.start, f.end])]
    w = c.pivot_table(index=["commune_code", "commune"], columns="year", values="licences", aggfunc="sum",
                      observed=True).reindex(columns=[f.start, f.end]).fillna(0)
    women = c[c["year"] == f.end].groupby("commune_code", observed=True)["women"].sum()
    w = w.reset_index()
    w["growth"] = np.where(w[f.start] > 0, (w[f.end] / w[f.start] - 1) * 100, np.nan)
    w["women_share"] = w["commune_code"].map(women) / w[f.end].replace(0, np.nan) * 100
    return w.sort_values(f.end, ascending=False).head(n)


# ------------------------------------------------------------------ who plays
def pyramid(d: Data, f: Filters) -> pd.DataFrame:
    t = d.tennis_age
    t = t[t["year"].isin([f.start, f.end]) & t["dep"].isin(f.deps) & t["sex"].isin(["F", "H"])
          & (t["age_band"] != "NR")]
    return t.groupby(["year", "sex", "age_band"], observed=True)["licences"].sum().reset_index()


def growth_by_age(d: Data, f: Filters) -> pd.DataFrame:
    df = filter_long(d, f, ages=False)
    df = df[df["age_group"] != "Unknown"]
    df = df.assign(group=label_groups(d, df, None)).dropna(subset=["group"])
    df = df[df["year"].isin([f.start, f.end])]
    g = df.groupby(["group", "age_group", "year"], observed=True)["licences"].sum().unstack()
    g = g.reindex(columns=[f.start, f.end])
    g["growth"] = (g[f.end] / g[f.start] - 1) * 100
    g["added"] = g[f.end] - g[f.start]
    return g.reset_index()


# ------------------------------------------------------------------ who is missing (QPV)
def qpv_shares(d: Data, f: Filters, min_size: int) -> pd.DataFrame:
    q = d.fed_qpv
    q = q[q["year"].between(f.start, f.end) & q["dep"].isin(f.deps) & (q["qpv"] != "Unallocated")]
    keys = q["fed_key"].astype(str)
    q = q[keys.isin(d.bench_keys | {d.tennis_key})]
    g = q.groupby(["fed_key", "year", "qpv"], observed=True)["licences"].sum().unstack(fill_value=0)
    g["total"] = g.sum(axis=1)
    g["share"] = g.get("In QPV", 0) / g["total"] * 100
    g = g.reset_index()
    g["fed_key"] = g["fed_key"].astype(str)
    per_fed = g[g["fed_key"].isin(peer_keys(d, min_size)) & (g["total"] > 0)].copy()
    per_fed["name"] = per_fed["fed_key"].map(d.fed_name)
    bench = g[g["fed_key"].isin(d.bench_keys)].groupby("year")[["In QPV", "total"]].sum()
    bench["share"] = bench["In QPV"] / bench["total"] * 100
    return per_fed, bench.reset_index()
