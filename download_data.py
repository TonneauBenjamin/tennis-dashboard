"""Download (cached) and process all raw data into data/processed/.

Usage:
    python download_data.py                 # download raw files if missing, then process
    python download_data.py --raw-dir DIR   # use already-downloaded files in DIR (no network)

Runtime ≈ 2 minutes and ~3 GB RAM peak for the five 250 MB licence files.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.io import YEARS  # noqa: E402
from utils import io, prep  # noqa: E402


def local_paths(raw_dir: Path) -> dict[str, Path]:
    paths = {f"lic_{y}": raw_dir / f"lic-data-{y}.csv" for y in YEARS}
    paths["population"] = raw_dir / "poplegales2017-2021.parquet"
    paths["geometry"] = raw_dir / "departements-avec-outre-mer.geojson"
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        sys.exit("Missing raw files:\n  " + "\n  ".join(missing))
    return paths


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw-dir", type=Path, default=None, help="folder with raw files (skips download)")
    args = ap.parse_args()

    t0 = time.time()
    print("1/2 raw data")
    raw = local_paths(args.raw_dir) if args.raw_dir else io.fetch_raw()
    print("2/2 cleaning, validation, aggregation")
    q = prep.run(raw)
    ok = all(c["consistent"] for c in q["cross_checks"])
    print(json.dumps({"cross_checks_pass": ok, "processed_bytes": q["processed_bytes"]}, indent=2))
    print(f"done in {time.time() - t0:.0f}s")
    if not ok:
        sys.exit("Cross-table validation failed: see data/processed/quality_report.json")


if __name__ == "__main__":
    main()
