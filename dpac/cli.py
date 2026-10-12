"""
Command-line interface for dpac.

Usage examples:

    dpac --orcid 0000-0000-0000-0000
    dpac --orcid 0000-0000-0000-0000 --schemes equal,harmonic
    dpac --orcid 0000-0000-0000-0000 --json > out.json
    dpac --orcid-list orcids.txt --output table.csv
    dpac --orcid 0000-0000-0000-0000 --schemes declared \\
         --shares-csv my_shares.csv

The declared-shares CSV is read as one row per paper with at least two
columns: an identifier column (`work_id` or `doi`) and a `share` column
giving the focal author's declared share for that paper. Additional
columns are ignored.

The OpenAlex API key is read from the environment variable
OPENALEX_API_KEY (not from the command line, so that it stays out of the
shell history).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from .profile import compute_profile


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dpac",
        description=(
            "Compute paper-level and author-level bibliometric quantities "
            "under one or more contribution-share schemes."
        ),
    )
    parser.add_argument(
        "--orcid",
        help="ORCID identifier for a single researcher.",
    )
    parser.add_argument(
        "--orcid-list",
        help=(
            "Path to a text file containing one ORCID per line. "
            "Output is a cross-researcher comparison table."
        ),
    )
    parser.add_argument(
        "--schemes",
        default="equal,harmonic",
        help=(
            "Comma-separated list of share-imputation schemes to apply. "
            "Built-in: equal, harmonic. Add 'declared' along with "
            "--shares-csv to use user-supplied declared shares. "
            "Default: equal,harmonic."
        ),
    )
    parser.add_argument(
        "--shares-csv",
        help=(
            "Path to a CSV of declared shares, required when 'declared' "
            "is among the schemes. Columns: work_id (or doi), share."
        ),
    )
    parser.add_argument(
        "--mailto",
        help=(
            "Contact email passed to OpenAlex as mailto (ignored by OpenAlex "
            "since 2026; the API key in $OPENALEX_API_KEY is what counts). "
            "Also reads $DPAC_MAILTO."
        ),
    )
    parser.add_argument(
        "--cache-dir",
        help="Directory for cached OpenAlex responses. Default: ~/.dpac_cache.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable read-from-cache (writes still happen).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of the plain-text summary table.",
    )
    parser.add_argument(
        "--output",
        help="Output file path (used with --orcid-list for the CSV table).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose logging.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    # urllib3 logs full request URLs at DEBUG, and the URL carries the API key.
    logging.getLogger("urllib3").setLevel(logging.INFO)

    if not args.orcid and not args.orcid_list:
        parser.error("either --orcid or --orcid-list must be supplied")

    schemes = [s.strip() for s in args.schemes.split(",") if s.strip()]
    declared = None
    if "declared" in schemes:
        if not args.shares_csv:
            parser.error(
                "scheme 'declared' requires --shares-csv pointing to a CSV "
                "of declared shares."
            )
        declared = _load_shares_csv(args.shares_csv)

    cache_dir = Path(args.cache_dir) if args.cache_dir else None
    use_cache = not args.no_cache
    if not os.environ.get("OPENALEX_API_KEY"):
        logging.info(
            "No OPENALEX_API_KEY set: OpenAlex allows only a small number of "
            "requests a day without a key (free at openalex.org/settings/api)."
        )

    if args.orcid:
        result = compute_profile(
            orcid=args.orcid,
            schemes=schemes,
            declared=declared,
            mailto=args.mailto,
            cache_dir=cache_dir,
            use_cache=use_cache,
        )
        if args.json:
            print(json.dumps(result.as_dict(), indent=2))
        else:
            print(result.summary())
        return 0

    # orcid-list mode
    orcid_path = Path(args.orcid_list)
    orcids = [
        line.strip()
        for line in orcid_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    rows = []
    for orc in orcids:
        try:
            r = compute_profile(
                orcid=orc,
                schemes=schemes,
                declared=declared,
                mailto=args.mailto,
                cache_dir=cache_dir,
                use_cache=use_cache,
            )
        except Exception as exc:                                # noqa: BLE001
            logging.error("failed for ORCID %s: %s", orc, exc)
            continue

        row = {
            "orcid": orc,
            "n_papers": r.paper_level.n_papers,
            "total_citations": r.paper_level.total_citations,
            "raw_h_index": r.paper_level.raw_h_index,
        }
        for scheme, m in r.author_level.items():
            row[f"weighted_citations_{scheme}"] = round(m.weighted_citations, 1)
            row[f"fractional_h_{scheme}"] = round(m.fractional_h_index, 2)
            row[f"effective_papers_{scheme}"] = round(m.effective_papers, 2)
        row["n_works_capped"] = r.n_works_capped
        rows.append(row)

    if not rows:
        print("No researchers processed successfully.", file=sys.stderr)
        return 1

    fieldnames = list(rows[0])
    out_path = Path(args.output) if args.output else None
    if out_path:
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} rows to {out_path}")
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return 0


def _load_shares_csv(path: str) -> dict[str, float]:
    """Parse a declared-shares CSV into a {id: share} mapping."""
    mapping: dict[str, float] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get("work_id") or row.get("doi")
            if not key:
                continue
            try:
                mapping[key.strip()] = float(row["share"])
            except (KeyError, ValueError):
                continue
    return mapping


if __name__ == "__main__":
    sys.exit(main())
