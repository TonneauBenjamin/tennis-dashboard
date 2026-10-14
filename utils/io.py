"""Input/output and project constants.

- Constants: paths and settings loaded once from seeds.json (single source of truth).
- fetch_raw(): cached downloads of the raw open data (~1.2 GB, never committed): each file is
  downloaded once into data/raw/ and skipped on later runs when its size matches the published size.
- Loaders for the small processed parquet files the app reads.
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

import pandas as pd
import requests

# ------------------------------------------------------------------ constants (from seeds.json)
ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
ASSETS = ROOT / "assets"
GEOJSON_PATH = ASSETS / "departements.geojson"
QUALITY_PATH = DATA_PROCESSED / "quality_report.json"

with open(ROOT / "seeds.json", encoding="utf-8") as fh:
    SEEDS: dict = json.load(fh)

YEARS: list[int] = SEEDS["years"]
TENNIS_CODE: str = SEEDS["tennis_code"]
COLORS: dict = SEEDS["colors"]
AGE_BANDS: list[str] = SEEDS["age_bands"]
AGE_GROUPS: dict[str, list[str]] = SEEDS["age_groups"]
BAND_TO_GROUP: dict[str, str] = {b: g for g, bands in AGE_GROUPS.items() for b in bands}
POP_LAST_YEAR: int = SEEDS["population_last_year"]

# Identifier columns of the INJEP 2019+ files (see licences-dictionnaire-des-variables.xlsx).
ID_COLS = ["Code Commune", "Commune", "Code QPV", "Nom QPV", "Département",
           "Région", "Statut géo", "Code", "Fédération"]
IN_SCOPE = "1.Champ geoc"  # geocoded: mainland France + overseas départements except Mayotte

SEX_LABELS = {"F": "Women", "H": "Men", "NR": "Unknown"}
AGE_BAND_LABELS = {b: b.replace(" à ", "–") for b in AGE_BANDS}

PROCESSED_FILES = [
    "fed_long.parquet", "fed_qpv.parquet", "tennis_age.parquet", "tennis_commune.parquet",
    "scope.parquet", "federations.parquet", "departments.parquet", "population.parquet",
]

CHUNK = 1 << 20  # 1 MiB


def download(url: str, dest: Path, expected_bytes: int | None = None, retries: int = 3) -> Path:
    """Stream `url` to `dest` atomically. Skip if `dest` already exists with the expected size."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and (expected_bytes is None or dest.stat().st_size == expected_bytes):
        print(f"  cached  {dest.name}")
        return dest
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
                    for chunk in resp.iter_content(CHUNK):
                        tmp.write(chunk)
            got = Path(tmp.name).stat().st_size
            if expected_bytes is not None and got != expected_bytes:
                raise OSError(f"size mismatch for {dest.name}: got {got}, expected {expected_bytes}")
            shutil.move(tmp.name, dest)
            print(f"  fetched {dest.name} ({got / 1e6:.1f} MB)")
            return dest
        except Exception as err:  # network errors, HTTP errors, truncated files
            last_err = err
            print(f"  attempt {attempt}/{retries} failed for {dest.name}: {err}")
    raise RuntimeError(f"Could not download {url}") from last_err


def raw_licence_path(year: int) -> Path:
    return DATA_RAW / f"lic-data-{year}.csv"


def fetch_raw() -> dict[str, Path]:
    """Download every raw input listed in seeds.json (cached)."""
    src = SEEDS["sources"]
    paths: dict[str, Path] = {}
    for year, meta in src["licences"]["files"].items():
        paths[f"lic_{year}"] = download(meta["url"], raw_licence_path(int(year)), meta["bytes"])
    paths["population"] = download(src["population"]["url"], DATA_RAW / "poplegales2017-2021.parquet",
                                   src["population"]["bytes"])
    paths["geometry"] = download(src["geometry"]["url"], DATA_RAW / "departements-avec-outre-mer.geojson")
    return paths


# ---------------------------------------------------------------- app-side loaders
def processed_ready() -> bool:
    return all((DATA_PROCESSED / f).exists() for f in PROCESSED_FILES) and GEOJSON_PATH.exists()


def read_processed(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA_PROCESSED / f"{name}.parquet")


def read_geojson() -> dict:
    with open(GEOJSON_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def read_quality() -> dict:
    with open(QUALITY_PATH, encoding="utf-8") as fh:
        return json.load(fh)
