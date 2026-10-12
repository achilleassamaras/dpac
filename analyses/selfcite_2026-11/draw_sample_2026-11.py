"""
Draw the Chat 26 sample from the 2026 (v9) career-long top-2% list.

Five fields with different team sizes and self-citation cultures, the three
Chat 24 groups in each, 40 scientists per field and group (600 rows; about
500 are expected to survive name matching), plus a separate random reference
group of 25 per field.

Groups (percentiles are taken within the scientist's primary subfield, over
everyone listed in that subfield):

  S  Self-citation-only entrants: listed only through the two routes that
     count self-citations (top 100,000 by c, or top 2% of the subfield by c);
     fails both self-citation-free routes.
  B  High bundled citations: not an S entrant; citations per citing paper
     without self-citations, cprat (ns), at or above the subfield's 95th
     percentile.
  C  Comparison group: not an S entrant; self-citation rate between the
     subfield's 40th and 60th percentiles, and cprat (ns) at or below the
     subfield median.
  R  Random reference: random draw from everyone eligible in the field
     (any group), excluding people already drawn into S, B or C.

Eligibility (all groups, as in Chat 24): 50 to 1,000 papers (np6025) and at
most 50,000 citations including self-citations (nc9625), so that OpenAlex
matching is reliable and each record stays within the run's citation cap.

Usage (from the run folder):

    python draw_sample_2026-11.py "<path to Table_1_Authors_career_...xlsx>" [output folder]

Writes sample_2026-11.csv, random_reference_2026-11.csv and
sample_2026-11_design.csv (counts per cell, for the methods text) to the
output folder (default: the current folder).
Reading the 100 MB workbook takes a few minutes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261012
PER_CELL = 40
PER_FIELD_R = 25
FIELDS = {
    "Engineering": "ENG",
    "Physics & Astronomy": "PHY",
    "Clinical Medicine": "MED",
    "Mathematics & Statistics": "MAT",
    "Economics & Business": "ECO",
}
GROUPS = {
    "S": "Self-citation-only entrants",
    "B": "High bundled citations",
    "C": "Comparison group",
    "R": "Random reference",
}
NP_MIN, NP_MAX, NC_MAX = 50, 1000, 50000

# ISO 3166 alpha-3 (lower case, as in the list) to alpha-2, for the OpenAlex country filter.
# Fixed table (from pycountry) for every country code in v9 Table 1, so the draw needs no extra package.
_CC = dict(x.split(":") for x in (
    "alb:AL and:AD are:AE arg:AR arm:AM asm:AS atg:AG aus:AU aut:AT aze:AZ bdi:BI bel:BE ben:BJ bfa:BF "
    "bgd:BD bgr:BG bhr:BH bhs:BS bih:BA blr:BY bmu:BM bra:BR brb:BB brn:BN bwa:BW caf:CF can:CA che:CH "
    "chl:CL chn:CN civ:CI cmr:CM col:CO cri:CR cub:CU cuw:CW cyp:CY cze:CZ deu:DE dnk:DK dza:DZ ecu:EC "
    "egy:EG esp:ES est:EE eth:ET fin:FI fji:FJ flk:FK fra:FR fro:FO gbr:GB geo:GE gha:GH gmb:GM gnb:GW "
    "grc:GR grd:GD grl:GL gtm:GT guf:GF hkg:HK hrv:HR hti:HT hun:HU idn:ID ind:IN irl:IE irn:IR irq:IQ "
    "isl:IS isr:IL ita:IT jam:JM jor:JO jpn:JP kaz:KZ ken:KE kgz:KG khm:KH kir:KI kna:KN kor:KR kwt:KW "
    "lao:LA lbn:LB lbr:LR lby:LY lie:LI lka:LK lso:LS ltu:LT lux:LU lva:LV mac:MO mar:MA mco:MC mda:MD "
    "mdg:MG mex:MX mkd:MK mli:ML mlt:MT mmr:MM mne:ME mng:MN moz:MZ mrt:MR mtq:MQ mus:MU mwi:MW mys:MY "
    "nam:NA ncl:NC ner:NE nga:NG nic:NI nld:NL nor:NO npl:NP nzl:NZ omn:OM pak:PK pan:PA per:PE phl:PH "
    "png:PG pol:PL pri:PR prk:KP prt:PT pry:PY pse:PS pyf:PF qat:QA rou:RO rus:RU rwa:RW sau:SA sdn:SD "
    "sen:SN sgp:SG slb:SB sle:SL slv:SV smr:SM srb:RS ssd:SS svk:SK svn:SI swe:SE swz:SZ syr:SY tcd:TD "
    "tha:TH tls:TL tto:TT tun:TN tur:TR twn:TW tza:TZ uga:UG ukr:UA ury:UY usa:US uzb:UZ ven:VE vnm:VN "
    "vut:VU wsm:WS yem:YE zaf:ZA zmb:ZM zwe:ZW "
).split())


def _cc2(c3) -> str:
    return _CC.get(str(c3).lower(), "") if isinstance(c3, str) else ""


RENAME = {
    "nc9625 (ns)": "nc9625_ns", "h25 (ns)": "h25_ns", "hm25 (ns)": "hm25_ns", "hm25": "hm25",
    "rank (ns)": "rank_ns", "c (ns)": "c_ns", "npciting (ns)": "npciting_ns", "cprat": "cprat_all",
    "rank sm-subfield-1": "rank_sub", "rank sm-subfield-1 (ns)": "rank_sub_ns", "sm-subfield-1 count": "sub_count",
    "nps": "nps", "cpsf": "cpsf", "npsfl": "npsfl", "ncs": "ncs", "ncsf": "ncsf", "ncsfl": "ncsfl",
    "nps (ns)": "nps_ns", "ncs (ns)": "ncs_ns", "ncsf (ns)": "ncsf_ns", "ncsfl (ns)": "ncsfl_ns",
}


def load(path: str) -> pd.DataFrame:
    try:
        return pd.read_excel(path, sheet_name="Data", engine="calamine")
    except (ImportError, ValueError):
        return pd.read_excel(path, sheet_name="Data")


def classify(d: pd.DataFrame) -> pd.DataFrame:
    cnt = d["sm-subfield-1 count"]
    with_self = (d["rank"] <= 100000) | (d["rank sm-subfield-1"] <= 0.02 * cnt)
    without = (d["rank (ns)"] <= 100000) | (d["rank sm-subfield-1 (ns)"] <= 0.02 * cnt)
    d = d.assign(selfdep=(with_self & ~without).astype(int))
    by = d.groupby("sm-subfield-1")
    d["sub_cprat_ns_p95"] = d["sm-subfield-1"].map(by["cprat (ns)"].quantile(0.95))
    d["sub_cprat_ns_p50"] = d["sm-subfield-1"].map(by["cprat (ns)"].median())
    d["sub_self_p40"] = d["sm-subfield-1"].map(by["self%"].quantile(0.40))
    d["sub_self_p60"] = d["sm-subfield-1"].map(by["self%"].quantile(0.60))
    d["is_S"] = d["selfdep"] == 1
    d["is_B"] = (d["selfdep"] == 0) & (d["cprat (ns)"] >= d["sub_cprat_ns_p95"])
    d["is_C"] = ((d["selfdep"] == 0) & d["self%"].between(d["sub_self_p40"], d["sub_self_p60"])
                 & (d["cprat (ns)"] <= d["sub_cprat_ns_p50"]))
    d["eligible"] = d["np6025"].between(NP_MIN, NP_MAX) & (d["nc9625"] <= NC_MAX)
    return d


def _rows(x: pd.DataFrame, field: str, code: str, g: str) -> pd.DataFrame:
    out = pd.DataFrame({
        "label": [f"{FIELDS[field]}-{g}-{k:03d}" for k in range(1, len(x) + 1)],
        "group": GROUPS[g], "group_code": g, "field": field, "field_code": FIELDS[field],
        "authfull": x["authfull"].values, "inst_name": x["inst_name"].values,
        "cntry": x["cntry"].values, "cc2": [_cc2(c) for c in x["cntry"]],
        "subfield": x["sm-subfield-1"].values,
        "np6025": x["np6025"].values, "nc9625": x["nc9625"].values, "h25": x["h25"].values,
        "self_pct_list": (100 * x["self%"]).round(1).values,
        "cprat_ns_list": x["cprat (ns)"].round(3).values,
        "hm_h_list": (x["hm25"] / x["h25"]).round(3).values,
        "selfdep": x["selfdep"].values,
    })
    extra = x[[c for c in RENAME if c in x.columns]].rename(columns=RENAME).reset_index(drop=True)
    extra["firstyr"], extra["lastyr"], extra["cosmo"] = x["firstyr"].values, x["lastyr"].values, x["cosmo"].values
    return pd.concat([out.reset_index(drop=True), extra], axis=1)


def draw(d: pd.DataFrame):
    rng = np.random.RandomState(SEED)
    parts, refs, design = [], [], []
    for field in FIELDS:
        f = d[d["sm-field"] == field].sort_values(["rank", "authfull"], kind="mergesort")
        taken = set()
        for g in "SBC":
            pool = f[f[f"is_{g}"] & f["eligible"]]
            pick = pool.iloc[rng.permutation(len(pool))[:PER_CELL]]
            taken |= set(pick.index)
            parts.append(_rows(pick, field, FIELDS[field], g))
            design.append({"field": field, "group": GROUPS[g], "listed_in_group": int(f[f"is_{g}"].sum()),
                           "eligible": len(pool), "drawn": len(pick)})
        pool = f[f["eligible"] & ~f.index.isin(taken)]
        pick = pool.iloc[rng.permutation(len(pool))[:PER_FIELD_R]]
        refs.append(_rows(pick, field, FIELDS[field], "R"))
        design.append({"field": field, "group": GROUPS["R"], "listed_in_group": len(f),
                       "eligible": int(f["eligible"].sum()), "drawn": len(pick)})
    return _interleave(pd.concat(parts, ignore_index=True)), _interleave(pd.concat(refs, ignore_index=True)), pd.DataFrame(design)


def _interleave(x: pd.DataFrame) -> pd.DataFrame:
    """Order rows 001 of every cell, then 002, ...: a run stopped part-way leaves balanced cells."""
    k = x["label"].str[-3:].astype(int)
    f = x["field"].map({f: i for i, f in enumerate(FIELDS)})
    g = x["group_code"].map({g: i for i, g in enumerate(GROUPS)})
    return x.assign(_k=k, _f=f, _g=g).sort_values(["_k", "_f", "_g"]).drop(columns=["_k", "_f", "_g"]).reset_index(drop=True)


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__)
        return 1
    d = classify(load(argv[1]))
    sample, ref, design = draw(d)
    here = Path(argv[2]) if len(argv) > 2 else Path(".")
    here.mkdir(parents=True, exist_ok=True)
    sample.to_csv(here / "sample_2026-11.csv", index=False, encoding="utf-8", lineterminator="\n")
    ref.to_csv(here / "random_reference_2026-11.csv", index=False, encoding="utf-8", lineterminator="\n")
    design.to_csv(here / "sample_2026-11_design.csv", index=False, encoding="utf-8", lineterminator="\n")
    print(design.to_string(index=False))
    print(f"\nWrote {len(sample)} rows to sample_2026-11.csv and {len(ref)} to random_reference_2026-11.csv.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
