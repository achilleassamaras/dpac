"""
Chat 27 analysis of the Chat 26 five-field self-citation run.

Implements `ANALYSIS_PLAN_2026-11.md` (fixed in Chat 26, before the data were
fetched). Run once; its output is the basis of the note.

Inputs (no names in the Level 2 files):
    selfcite_summary.csv           Level 2, one row per researcher (labels only)
    sample_2026-11_design.csv      group sizes in the list and in the draw
    Table_1_Authors_career_...xlsx v9 career-long list (Level 1)
    Table_3_maxlog_career_...xlsx  maxlog normalisers for the c-score

Usage:
    python analyse_selfcite_2026-11.py SUMMARY DESIGN TABLE1 TABLE3 OUTDIR

TABLE1 may also be a Parquet copy of the Data sheet (same columns).

Outputs in OUTDIR: results.md (every pre-specified result), results.json,
CSV tables, Figure_1_citation_sources.png, Figure_2_reordering.png.
Only field- and group-level aggregates are written; no names or labels.

Implementation choices where the plan is silent (stated in results.md):
  * Inclusion step 2: the run used high-confidence name matches only (the
    optional hand review of `check` rows was skipped in Chat 26), so `use = Y`
    is equivalent to `match_flag == high`. Sensitivity check E2 is therefore
    identical to the primary analysis.
  * Quintiles: researchers are ranked within the field (average ranks for
    ties) and quintile = ceil(5 * rank / n), so tied values share a quintile.
  * H1 test: one-sided bootstrap p-value, the share of resamples in which
    D(credit) <= D(list rule) (or Q likewise), with Holm correction across the
    five fields. The same resampled researchers are used for every rule, so
    the comparison is paired.
  * Pooled random-reference analysis: all R researchers ranked together, as
    the list ranks scientists across fields.
  * H5: frac_equal and frac_harmonic are each compared with the list rule
    (excl_shared); frac_network with its binary counterpart (excl_network).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

SEED = 20261012
N_BOOT = 2000
ALPHA = 0.05
MIN_CELL = 20
COV_LO, COV_HI = 0.25, 4.0
TRUNC_MAX = 0.10

FIELDS = {
    "ENG": "Engineering",
    "PHY": "Physics & Astronomy",
    "MED": "Clinical Medicine",
    "MAT": "Mathematics & Statistics",
    "ECO": "Economics & Business",
}
GROUPS = {"S": "Self-citation-only entrants", "B": "High bundled citations",
          "C": "Comparison group", "R": "Random reference"}

# Rankings compared with the baseline (all_cites), in the order of Figure 2.
RULES = [
    ("self_list", "Self-citations: list rule", "all_cites", "excl_shared_cites"),
    ("self_network", "Self-citations: also network", "all_cites", "excl_network_cites"),
    ("self_frac", "Self-citations: fractional (equal)", "all_cites", "frac_equal_cites"),
    ("credit_equal", "Credit: equal shares", "all_cites", "all_credit_equal"),
    ("credit_harmonic", "Credit: harmonic shares", "all_cites", "all_credit_harmonic"),
    ("h_self", "h: list rule", "all_h", "excl_shared_h"),
    ("h_credit", "h -> hm", "all_h", "all_hm"),
]
H1_PAIRS = [  # (credit rule, self rule)
    ("credit_equal", "self_list"),
    ("credit_harmonic", "self_list"),
    ("h_credit", "h_self"),
]


# ----------------------------------------------------------------------
# Small statistics helpers
# ----------------------------------------------------------------------

def quintile(x: np.ndarray) -> np.ndarray:
    r = stats.rankdata(x, method="average")
    return np.minimum(5, np.ceil(5 * r / len(x))).astype(int)


def reorder(base: np.ndarray, alt: np.ndarray) -> tuple[float, float]:
    """D = 1 - Spearman rho; Q = share changing quintile."""
    rho = stats.spearmanr(base, alt).statistic
    q = float(np.mean(quintile(base) != quintile(alt)))
    return 1.0 - float(rho), q


def cliffs_delta(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    x, y = x[~np.isnan(x)], y[~np.isnan(y)]
    gt = (x[:, None] > y[None, :]).sum()
    lt = (x[:, None] < y[None, :]).sum()
    return float((gt - lt) / (len(x) * len(y)))


def holm(pvals: dict) -> dict:
    """Holm-adjusted p-values for {key: p}; NaN entries are left out."""
    items = sorted(((p, k) for k, p in pvals.items() if p is not None and not math.isnan(p)))
    m = len(items)
    adj, running = {}, 0.0
    for i, (p, k) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adj[k] = running
    return {k: adj.get(k, float("nan")) for k in pvals}


def boot_idx(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(0, n, size=(N_BOOT, n))


def ci(a) -> list:
    a = np.asarray(a, float)
    a = a[~np.isnan(a)]
    if len(a) == 0:
        return [float("nan"), float("nan")]
    return [float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))]


def median_ci(x, rng) -> tuple[float, list]:
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    idx = boot_idx(len(x), rng)
    return float(np.median(x)), ci(np.median(x[idx], axis=1))


def r3(v):
    if isinstance(v, (list, tuple)):
        return [r3(u) for u in v]
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    return round(float(v), 4)


# ----------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------

def load_level2(path: Path) -> tuple[pd.DataFrame, list, pd.DataFrame]:
    d = pd.read_csv(path)
    steps = [("drawn and matched (run input)", len(d))]
    excluded = []
    d1 = d[d["status"] == "ok"]
    excluded.append(d[d["status"] != "ok"].assign(reason="status: " + d["status"]))
    steps.append(("1. status ok", len(d1)))
    d2 = d1[d1["match_flag"] == "high"]
    steps.append(("2. name match approved (high confidence)", len(d2)))
    cov = d2["all_cites"] / d2["nc9625"]
    d3 = d2[(cov >= COV_LO) & (cov <= COV_HI)].copy()
    excluded.append(d2[~d2.index.isin(d3.index)].assign(reason="coverage outside 0.25-4"))
    steps.append(("3. OpenAlex coverage 0.25-4 x list citations", len(d3)))
    ex = pd.concat(excluded)[["field_code", "group_code", "reason"]]
    return d3, steps, ex


def load_level1(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    try:
        return pd.read_excel(path, sheet_name="Data", engine="calamine")
    except (ImportError, ValueError):
        return pd.read_excel(path, sheet_name="Data")


def load_maxlog(path: Path) -> dict:
    try:
        t = pd.read_excel(path, engine="calamine")
    except (ImportError, ValueError):
        t = pd.read_excel(path)
    return {c: float(t[c].iloc[0]) for c in t.columns}


# ----------------------------------------------------------------------
# Analyses
# ----------------------------------------------------------------------

def validation(d: pd.DataFrame) -> dict:
    out = {}
    for fc in FIELDS:
        x = d[d.field_code == fc]
        v1 = stats.spearmanr(x["self_rate_list_rule"], x["self_pct_list"] / 100).statistic
        diff = float(np.median(x["self_rate_list_rule"] - x["self_pct_list"] / 100))
        v2 = stats.spearmanr(x["excl_shared_cites_per_citing"], x["cprat_ns_list"]).statistic
        out[fc] = {"n": len(x), "V1_rho": float(v1), "V1_median_diff_points": 100 * diff,
                   "V2_rho": float(v2), "flag_V1_below_0.6": bool(v1 < 0.6)}
    return out


def h1_block(x: pd.DataFrame, rng: np.random.Generator, test: bool) -> dict:
    """Point estimates, bootstrap intervals and paired tests for one set of researchers."""
    n = len(x)
    cols = {r[0]: (x[r[2]].to_numpy(float), x[r[3]].to_numpy(float)) for r in RULES}
    point = {k: reorder(b, a) for k, (b, a) in cols.items()}
    res = {"n": n, "tested": test, "rules": {}, "ratios": {}}
    idx = boot_idx(n, rng)
    boots = {k: np.empty((N_BOOT, 2)) for k in cols}
    for i in range(N_BOOT):
        ii = idx[i]
        for k, (b, a) in cols.items():
            boots[k][i] = reorder(b[ii], a[ii])
    for k in cols:
        res["rules"][k] = {"D": point[k][0], "D_ci": ci(boots[k][:, 0]),
                           "Q": point[k][1], "Q_ci": ci(boots[k][:, 1])}
    for cr, sr in H1_PAIRS + [("credit_equal", "self_network"), ("credit_harmonic", "self_network")]:
        for j, m in enumerate(("D", "Q")):
            num, den = boots[cr][:, j], boots[sr][:, j]
            with np.errstate(divide="ignore", invalid="ignore"):
                ratio_b = num / den
            pt = point[cr][j] / point[sr][j] if point[sr][j] > 0 else float("inf")
            p = (np.sum(num - den <= 0) + 1) / (N_BOOT + 1)
            res["ratios"][f"{m}:{cr}/{sr}"] = {"ratio": pt, "ratio_ci": ci(np.where(np.isfinite(ratio_b), ratio_b, np.nan)),
                                              "n_inf": int(np.sum(~np.isfinite(ratio_b))),
                                              "p_one_sided": float(p)}
    return res


def level1(t1: pd.DataFrame, maxlog: dict) -> dict:
    comp_cols = ["hm25 (ns)", "ncs (ns)", "ncsf (ns)", "ncsfl (ns)"]
    t1 = t1.copy()
    t1["composite_ns"] = sum(np.log1p(t1[c]) / maxlog[c] for c in comp_cols)
    t1["rank_composite"] = t1["composite_ns"].rank(ascending=False, method="min")
    top_c = t1["rank"] <= 100000
    top_ns = t1["rank (ns)"] <= 100000
    top_comp = t1["rank_composite"] <= 100000
    cnt = t1["sm-subfield-1 count"]
    with_self = (t1["rank"] <= 100000) | (t1["rank sm-subfield-1"] <= 0.02 * cnt)
    without = (t1["rank (ns)"] <= 100000) | (t1["rank sm-subfield-1 (ns)"] <= 0.02 * cnt)
    t1["selfdep"] = (with_self & ~without)
    out = {"_all": {"listed": len(t1), "selfdep": int(t1["selfdep"].sum()),
                    "top100k_c": int(top_c.sum()), "top100k_ns": int(top_ns.sum()),
                    "top100k_composite_within_list": int(top_comp.sum())}}
    for fc, field in FIELDS.items():
        m = t1["sm-field"] == field
        x = t1[m]
        d_self, q_self = reorder(x["c"].to_numpy(), x["c (ns)"].to_numpy())
        d_cred, q_cred = reorder(x["c (ns)"].to_numpy(), x["composite_ns"].to_numpy())
        a, b, c = top_c & m, top_ns & m, top_comp & m
        out[fc] = {
            "listed": int(m.sum()),
            "selfdep_share": float(x["selfdep"].mean()),
            "median_self_pct": float(100 * x["self%"].median()),
            "median_hm_h": float((x["hm25"] / x["h25"]).median()),
            "D_self": d_self, "Q_self": q_self, "D_credit": d_cred, "Q_credit": q_cred,
            "top100k_c_in_field": int(a.sum()),
            "top100k_change_self": float((a & ~top_ns).sum() / a.sum()) if a.sum() else float("nan"),
            "top100k_ns_in_field": int(b.sum()),
            "top100k_change_credit_lower_bound": float((b & ~top_comp).sum() / b.sum()) if b.sum() else float("nan"),
        }
    return out


def one_sided_mw(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    x, y = x[~np.isnan(x)], y[~np.isnan(y)]
    return float(stats.mannwhitneyu(x, y, alternative="greater").pvalue)


def h2_h4(d: pd.DataFrame, rng: np.random.Generator) -> dict:
    out = {"H2": {}, "H3": {}, "H4": {}}
    p2, p3a, p3b, p4 = {}, {}, {}, {}
    for fc in FIELDS:
        x = d[d.field_code == fc]
        ok = x["coauthor_share_of_self"].notna()
        r = stats.spearmanr(x.loc[ok, "coauthor_share_of_self"], x.loc[ok, "median_team_size"], alternative="greater")
        med, mci = median_ci(x["coauthor_share_of_self"], rng)
        out["H2"][fc] = {"n": int(ok.sum()), "rho": float(r.statistic), "p": float(r.pvalue),
                         "median_coauthor_share_of_self": med, "ci": mci,
                         "median_team_size": float(x["median_team_size"].median())}
        p2[fc] = float(r.pvalue)

        b, c = x[x.group_code == "B"], x[x.group_code == "C"]
        p = one_sided_mw(b["share_network"], c["share_network"])
        rr = stats.spearmanr(x["share_network"], x["cprat_ns_list"], alternative="greater")
        frac = (b["excl_shared_cites_per_citing"] - b["excl_network_cites_per_citing"]) / (b["excl_shared_cites_per_citing"] - 1)
        frac = frac.replace([np.inf, -np.inf], np.nan)
        fmed, fci = median_ci(frac, rng)
        out["H3"][fc] = {"n_B": len(b), "n_C": len(c),
                         "median_network_B": float(b["share_network"].median()),
                         "median_network_C": float(c["share_network"].median()),
                         "cliffs_delta": cliffs_delta(b["share_network"], c["share_network"]), "p_mw": p,
                         "rho_network_cprat": float(rr.statistic), "p_rho": float(rr.pvalue),
                         "B_excess_removed_by_network_median": fmed, "ci": fci}
        p3a[fc], p3b[fc] = p, float(rr.pvalue)

        s = x[x.group_code == "S"]
        p = one_sided_mw(s["share_own"], c["share_own"])
        out["H4"][fc] = {"n_S": len(s), "n_C": len(c),
                         "median_own_S": float(s["share_own"].median()),
                         "median_own_C": float(c["share_own"].median()),
                         "cliffs_delta": cliffs_delta(s["share_own"], c["share_own"]), "p_mw": p}
        p4[fc] = p
    for key, ps, name in (("H2", p2, "p_holm"), ("H3", p3a, "p_holm"), ("H3", p3b, "p_rho_holm"), ("H4", p4, "p_holm")):
        adj = holm(ps)
        for fc in FIELDS:
            out[key][fc][name] = adj[fc]
    ok = d["coauthor_share_of_self"].notna()
    r = stats.spearmanr(d.loc[ok, "coauthor_share_of_self"], d.loc[ok, "median_team_size"], alternative="greater")
    out["H2"]["pooled"] = {"n": int(ok.sum()), "rho": float(r.statistic), "p": float(r.pvalue)}
    rr = stats.spearmanr(d["share_network"], d["cprat_ns_list"], alternative="greater")
    out["H3"]["pooled"] = {"rho_network_cprat": float(rr.statistic), "p_rho": float(rr.pvalue)}
    order = sorted(FIELDS, key=lambda f: -out["H2"][f]["median_coauthor_share_of_self"])
    out["H2"]["observed_order"] = order
    out["H2"]["expected_order"] = ["MED", "PHY", "ENG", "ECO|MAT", "ECO|MAT"]
    return out


def h5(d: pd.DataFrame, rng: np.random.Generator) -> dict:
    rules = ["excl_own", "excl_shared", "excl_network", "frac_equal", "frac_harmonic", "frac_network"]
    tests = [("frac_equal", "excl_shared"), ("frac_harmonic", "excl_shared"), ("frac_network", "excl_network")]
    out = {"kept": {}, "tests": {f"{a}>{b}": {} for a, b in tests}}
    for fc in FIELDS:
        x = d[d.field_code == fc]
        out["kept"][fc] = {}
        for r in rules:
            med, mci = median_ci(x[f"{r}_h"] / x["all_h"], rng)
            cmed = float((x[f"{r}_cites"] / x["all_cites"]).median())
            out["kept"][fc][r] = {"h_kept_median": med, "ci": mci, "cites_kept_median": cmed}
        for a, b in tests:
            ka, kb = x[f"{a}_h"] / x["all_h"], x[f"{b}_h"] / x["all_h"]
            diff = (ka - kb).to_numpy()
            nz = int(np.sum(diff != 0))
            p = float(stats.wilcoxon(ka, kb, alternative="greater").pvalue) if nz else float("nan")
            out["tests"][f"{a}>{b}"][fc] = {"n": len(x), "n_nonzero": nz,
                                            "share_higher": float(np.mean(diff > 0)),
                                            "share_lower": float(np.mean(diff < 0)), "p": p}
    for key in out["tests"]:
        adj = holm({fc: out["tests"][key][fc]["p"] for fc in FIELDS})
        for fc in FIELDS:
            out["tests"][key][fc]["p_holm"] = adj[fc]
    return out


def run_h1(d: pd.DataFrame, label: str) -> dict:
    """H1 per field on a given set, with Holm across the fields that are tested."""
    out = {}
    for k, fc in enumerate(FIELDS):
        x = d[d.field_code == fc]
        rng = np.random.default_rng(SEED + k)
        out[fc] = h1_block(x, rng, test=len(x) >= MIN_CELL)
    keys = list(next(iter(out.values()))["ratios"].keys())
    for key in keys:
        adj = holm({fc: out[fc]["ratios"][key]["p_one_sided"] for fc in FIELDS if out[fc]["tested"]})
        for fc in FIELDS:
            out[fc]["ratios"][key]["p_holm"] = adj.get(fc, float("nan"))
    return out


# ----------------------------------------------------------------------
# Figures
# ----------------------------------------------------------------------

INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
C_OWN, C_CO, C_NET = "#2E75B6", "#1BA39C", "#D88536"   # validated (dataviz validator, light)
C_SELF, C_CRED = "#2E75B6", "#D88536"


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=8.5, length=0)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.set_axisbelow(True)


def figure1(d: pd.DataFrame, path: Path) -> pd.DataFrame:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "DejaVu Sans"
    rows = []
    for fc in FIELDS:
        for g in "SBCR":
            x = d[(d.field_code == fc) & (d.group_code == g)]
            rows.append({"field_code": fc, "group_code": g, "n": len(x),
                         "own": x["share_own"].mean(), "coauthor": x["share_coauthor"].mean(),
                         "network": x["share_network"].mean()})
    t = pd.DataFrame(rows)
    fig, axes = plt.subplots(5, 1, figsize=(6.6, 7.4), sharex=True)
    xmax = 0.5
    for ax, fc in zip(axes, FIELDS):
        _style(ax)
        tt = t[t.field_code == fc].reset_index(drop=True)
        for i, r in tt.iterrows():
            y = 3 - i
            left = 0.0
            for col, colr in (("own", C_OWN), ("coauthor", C_CO), ("network", C_NET)):
                ax.barh(y, r[col], left=left, height=0.62, color=colr, edgecolor="white", linewidth=1.2)
                left += r[col]
            ax.text(left + 0.006, y, f"{left:.0%}", va="center", ha="left", fontsize=8, color=INK2)
        names = {"S": "Self-citation-only", "B": "High bundled", "C": "Comparison", "R": "Random reference"}
        ax.set_yticks([3, 2, 1, 0])
        ax.set_yticklabels([f"{names[g]} (n={int(tt.loc[tt.group_code == g, 'n'].iloc[0])})" for g in "SBCR"])
        ax.set_title(FIELDS[fc], loc="left", fontsize=9.5, color=INK, pad=3, fontweight="bold")
        ax.set_xlim(0, xmax)
        ax.set_ylim(-0.6, 3.6)
    axes[-1].xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    axes[-1].set_xlabel("Mean share of citation links (independent citations are the remainder)", fontsize=8.5, color=INK2)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=C_OWN, label="Own (focal author on citing paper)"),
                        Patch(color=C_CO, label="Co-author (another author of the cited paper)"),
                        Patch(color=C_NET, label="Collaborator network (earlier co-author of the focal author, not on the cited paper)")],
               loc="upper center", ncol=1, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)
    return t


def figure2(h1: dict, l1: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams["font.family"] = "DejaVu Sans"
    show = ["self_list", "self_network", "self_frac", "credit_equal", "credit_harmonic"]
    labels = {"self_list": "Self-citations: list rule", "self_network": "Self-citations: also network",
              "self_frac": "Self-citations: fractional", "credit_equal": "Credit: equal shares",
              "credit_harmonic": "Credit: harmonic shares"}
    fig, axes = plt.subplots(5, 1, figsize=(6.6, 7.8), sharex=True)
    vals = [h1[fc]["rules"][k]["D_ci"][1] for fc in FIELDS for k in show] + \
           [l1[fc][k] for fc in FIELDS for k in ("D_self", "D_credit")]
    lo = min(min(h1[fc]["rules"][k]["D_ci"][0] for fc in FIELDS for k in show),
             min(l1[fc][k] for fc in FIELDS for k in ("D_self", "D_credit")))
    for ax, fc in zip(axes, FIELDS):
        _style(ax)
        for i, k in enumerate(show):
            y = 4 - i
            r = h1[fc]["rules"][k]
            col = C_SELF if k.startswith("self") else C_CRED
            ax.plot(r["D_ci"], [y, y], color=col, lw=2, solid_capstyle="round")
            ax.plot([r["D"]], [y], "o", ms=6.5, color=col, mec="white", mew=1.2, zorder=3)
        ax.plot([l1[fc]["D_self"]], [4], "o", ms=7.5, mfc="none", mec=C_SELF, mew=1.5, zorder=4)
        ax.plot([l1[fc]["D_credit"]], [1], "o", ms=7.5, mfc="none", mec=C_CRED, mew=1.5, zorder=4)
        ax.set_yticks([4, 3, 2, 1, 0])
        ax.set_yticklabels([labels[k] for k in show])
        ax.set_ylim(-0.6, 4.6)
        ax.set_title(f"{FIELDS[fc]} (n={h1[fc]['n']})", loc="left", fontsize=9.5, color=INK, pad=3, fontweight="bold")
        ax.set_xscale("log")
    axes[-1].set_xlim(max(1e-4, lo * 0.7), max(vals) * 1.4)
    axes[-1].xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    axes[-1].set_xlabel("Reordering D = 1 − Spearman ρ against total citations (log scale)", fontsize=8.5, color=INK2)
    handles = [Line2D([], [], color=C_SELF, marker="o", lw=2, label="Self-citation rule (Level 2, 95% interval)"),
               Line2D([], [], color=C_CRED, marker="o", lw=2, label="Credit-sharing rule (Level 2, 95% interval)"),
               Line2D([], [], color=INK2, marker="o", mfc="none", lw=0, label="Level 1, all listed scientists in the field: c→c (ns) and c (ns)→composite")]
    fig.legend(handles=handles, loc="upper center", ncol=1, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(path, dpi=200, facecolor="white")
    plt.close(fig)


# ----------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------

def pct(v, nd=1):
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{100 * v:.{nd}f}%"


def f3(v, nd=3):
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def fp(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return "–"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def write_report(R: dict, path: Path) -> None:
    L = []
    w = L.append
    w("# Chat 27 analysis results (run once against ANALYSIS_PLAN_2026-11)\n")
    w(f"Seed {SEED}; {N_BOOT} bootstrap resamples within field; Holm across the five fields; alpha {ALPHA}.\n")
    w("## Inclusion\n")
    for s, n in R["inclusion"]["steps"]:
        w(f"- {s}: {n}")
    w("\nExcluded (field, group, reason):")
    for e in R["inclusion"]["excluded"]:
        w(f"- {e['field_code']}-{e['group_code']}: {e['reason']}")
    w("\nIncluded per cell (S / B / C / R):")
    for fc in FIELDS:
        c = R["inclusion"]["cells"][fc]
        w(f"- {fc}: " + " / ".join(f"{g} {c[g]}" for g in "SBCR") + f" = {sum(c.values())}" +
          ("  (R below 20: described, not tested)" if c["R"] < MIN_CELL else ""))
    w("\n## A. Validation\n")
    w("| Field | n | V1 ρ | V1 median diff (points) | V2 ρ | flag |\n|---|---|---|---|---|---|")
    for fc in FIELDS:
        v = R["validation"][fc]
        w(f"| {fc} | {v['n']} | {f3(v['V1_rho'],2)} | {f3(v['V1_median_diff_points'],1)} | {f3(v['V2_rho'],2)} | {'ρ<0.6' if v['flag_V1_below_0.6'] else ''} |")
    for setname, title in (("H1_primary", "B. H1, primary: full Level-2 set per field"),
                           ("H1_R", "B. H1, secondary: random reference group only"),
                           ("H1_sens_E1", "E1. H1 without researchers with share_links_trunc > 0.10")):
        w(f"\n## {title}\n")
        w("| Field | n | rule | D [95% CI] | Q [95% CI] |\n|---|---|---|---|---|")
        for fc in FIELDS:
            h = R[setname][fc]
            for k, lab, *_ in RULES:
                r = h["rules"][k]
                w(f"| {fc} | {h['n']} | {lab} | {f3(r['D'],4)} [{f3(r['D_ci'][0],4)}, {f3(r['D_ci'][1],4)}] | "
                  f"{pct(r['Q'])} [{pct(r['Q_ci'][0])}, {pct(r['Q_ci'][1])}] |")
        w("\nRatios (credit / self), bootstrap interval, one-sided p, Holm p (tested fields only):\n")
        w("| Field | ratio | value [95% CI] | p | p Holm |\n|---|---|---|---|---|")
        for fc in FIELDS:
            h = R[setname][fc]
            for key, r in h["ratios"].items():
                w(f"| {fc}{'' if h['tested'] else ' (not tested)'} | {key} | {f3(r['ratio'],2)} [{f3(r['ratio_ci'][0],2)}, {f3(r['ratio_ci'][1],2)}]"
                  f"{' (inf in ' + str(r['n_inf']) + ')' if r['n_inf'] else ''} | {fp(r['p_one_sided'])} | {fp(r['p_holm'])} |")
    p = R["H1_R_pooled"]
    w(f"\n### Pooled random reference (n={p['n']}, ranked across fields)\n")
    for k, lab, *_ in RULES:
        r = p["rules"][k]
        w(f"- {lab}: D {f3(r['D'],4)} [{f3(r['D_ci'][0],4)}, {f3(r['D_ci'][1],4)}]; Q {pct(r['Q'])} [{pct(r['Q_ci'][0])}, {pct(r['Q_ci'][1])}]")
    for key, r in p["ratios"].items():
        w(f"- {key}: {f3(r['ratio'],2)} [{f3(r['ratio_ci'][0],2)}, {f3(r['ratio_ci'][1],2)}], p {fp(r['p_one_sided'])}")
    w("\n## B. H1, Level 1 analogue (all listed scientists per field)\n")
    w("| Field | listed | self-cit.-only entrants | D self (c→c ns) | Q self | D credit (c ns→composite) | Q credit | top-100k change, self | top-100k change, credit (lower bound) |")
    w("|---|---|---|---|---|---|---|---|---|")
    for fc in FIELDS:
        v = R["level1"][fc]
        w(f"| {fc} | {v['listed']:,} | {pct(v['selfdep_share'])} | {f3(v['D_self'],4)} | {pct(v['Q_self'])} | {f3(v['D_credit'],4)} | {pct(v['Q_credit'])} | "
          f"{pct(v['top100k_change_self'])} of {v['top100k_c_in_field']:,} | {pct(v['top100k_change_credit_lower_bound'])} of {v['top100k_ns_in_field']:,} |")
    a = R["level1"]["_all"]
    w(f"\nWhole list: {a['listed']:,} listed; {a['selfdep']:,} self-citation-only entrants.")
    for key, title in (("H2_H4", "C. H2–H4"), ("H2_H4_sens_E1", "E1. H2–H4 without share_links_trunc > 0.10")):
        h = R[key]
        w(f"\n## {title}\n")
        w("H2 (co-author share of self-citations rises with team size; Spearman, one-sided):\n")
        w("| Field | n | median co-author share of self [95% CI] | median team size | ρ | p | p Holm |\n|---|---|---|---|---|---|---|")
        for fc in FIELDS:
            v = h["H2"][fc]
            w(f"| {fc} | {v['n']} | {pct(v['median_coauthor_share_of_self'])} [{pct(v['ci'][0])}, {pct(v['ci'][1])}] | {f3(v['median_team_size'],1)} | {f3(v['rho'],2)} | {fp(v['p'])} | {fp(v['p_holm'])} |")
        v = h["H2"]["pooled"]
        w(f"\nPooled: ρ {f3(v['rho'],2)} (n {v['n']}), p {fp(v['p'])}. Observed order of field medians: {' > '.join(h['H2']['observed_order'])}; expected MED > PHY > ENG > ECO, MAT.\n")
        w("H3 (network share B > C, Mann–Whitney one-sided; network share vs list cprat (ns), Spearman one-sided):\n")
        w("| Field | n B / C | median network B | median network C | Cliff's δ | p | p Holm | ρ(network, cprat ns) | p Holm | B excess bundling removed by network [95% CI] |")
        w("|---|---|---|---|---|---|---|---|---|---|")
        for fc in FIELDS:
            v = h["H3"][fc]
            w(f"| {fc} | {v['n_B']} / {v['n_C']} | {pct(v['median_network_B'])} | {pct(v['median_network_C'])} | {f3(v['cliffs_delta'],2)} | {fp(v['p_mw'])} | {fp(v['p_holm'])} | "
              f"{f3(v['rho_network_cprat'],2)} | {fp(v['p_rho_holm'])} | {pct(v['B_excess_removed_by_network_median'],0)} [{pct(v['ci'][0],0)}, {pct(v['ci'][1],0)}] |")
        v = h["H3"]["pooled"]
        w(f"\nPooled ρ(network, cprat ns) {f3(v['rho_network_cprat'],2)}, p {fp(v['p_rho'])}.\n")
        w("H4 (own share S > C, Mann–Whitney one-sided):\n")
        w("| Field | n S / C | median own S | median own C | Cliff's δ | p | p Holm |\n|---|---|---|---|---|---|---|")
        for fc in FIELDS:
            v = h["H4"][fc]
            w(f"| {fc} | {v['n_S']} / {v['n_C']} | {pct(v['median_own_S'])} | {pct(v['median_own_C'])} | {f3(v['cliffs_delta'],2)} | {fp(v['p_mw'])} | {fp(v['p_holm'])} |")
    h = R["H5"]
    w("\n## D. H5: share of h kept under each rule (median [95% CI]); citations kept (median)\n")
    rules = ["excl_own", "excl_shared", "excl_network", "frac_equal", "frac_harmonic", "frac_network"]
    w("| Field | " + " | ".join(rules) + " |\n|---|" + "---|" * len(rules))
    for fc in FIELDS:
        k = h["kept"][fc]
        w(f"| {fc} | " + " | ".join(f"h {pct(k[r]['h_kept_median'])} [{pct(k[r]['ci'][0])}, {pct(k[r]['ci'][1])}]; cites {pct(k[r]['cites_kept_median'])}" for r in rules) + " |")
    w("\nPaired Wilcoxon (one-sided; zero differences dropped):\n")
    w("| Test | Field | n | n non-zero | share higher | share lower | p | p Holm |\n|---|---|---|---|---|---|---|---|")
    for key, per in h["tests"].items():
        for fc in FIELDS:
            v = per[fc]
            w(f"| {key} | {fc} | {v['n']} | {v['n_nonzero']} | {pct(v['share_higher'])} | {pct(v['share_lower'])} | {fp(v['p'])} | {fp(v['p_holm'])} |")
    w("\n## E. Sensitivity\n")
    w(f"- E1: {R['sens']['E1_removed']} researchers with share_links_trunc > 0.10 removed ({R['sens']['E1_by_field']}); results above.")
    w("- E2: not applicable — every included match is high-confidence (hand review of `check` rows was skipped in Chat 26); identical to the primary analysis.")
    w(f"- E3: skipped above 80,000 OpenAlex citations: {R['sens']['E3']}.")
    w("\n## Table 1 of the note\n")
    w("| Field | Listed (L1) | Self-cit.-only entrants (L1) | Included (L2) | Median team size | Own | Co-author | Network | h kept, list rule | h kept, fractional (equal) | V1 ρ |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for r in R["table1"]:
        w(f"| {r['field']} | {r['listed']:,} | {pct(r['selfdep_share'])} | {r['included']} | {f3(r['median_team_size'],1)} | {pct(r['own'])} | {pct(r['coauthor'])} | "
          f"{pct(r['network'])} | {pct(r['h_kept_list'])} | {pct(r['h_kept_frac'])} | {f3(r['V1_rho'],2)} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        print(__doc__)
        return 1
    summary, design, table1, table3, outdir = map(Path, argv[1:])
    outdir.mkdir(parents=True, exist_ok=True)
    R: dict = {}

    d, steps, excluded = load_level2(summary)
    cells = {fc: {g: int(((d.field_code == fc) & (d.group_code == g)).sum()) for g in "SBCR"} for fc in FIELDS}
    R["inclusion"] = {"steps": steps, "excluded": excluded.to_dict("records"), "cells": cells}
    R["design"] = pd.read_csv(design).to_dict("records")
    R["validation"] = validation(d)

    R["H1_primary"] = run_h1(d, "primary")
    R["H1_R"] = run_h1(d[d.group_code == "R"], "R")
    for fc in FIELDS:  # R cells below 20 are described, not tested
        R["H1_R"][fc]["tested"] = cells[fc]["R"] >= MIN_CELL
    keys = list(R["H1_R"]["ENG"]["ratios"].keys())
    for key in keys:
        adj = holm({fc: R["H1_R"][fc]["ratios"][key]["p_one_sided"] for fc in FIELDS if R["H1_R"][fc]["tested"]})
        for fc in FIELDS:
            R["H1_R"][fc]["ratios"][key]["p_holm"] = adj.get(fc, float("nan"))
    R["H1_R_pooled"] = h1_block(d[d.group_code == "R"], np.random.default_rng(SEED + 99), test=True)

    rng = np.random.default_rng(SEED + 10)
    R["H2_H4"] = h2_h4(d, rng)
    R["H5"] = h5(d, np.random.default_rng(SEED + 20))

    e1 = d[d["share_links_trunc"] <= TRUNC_MAX]
    R["H1_sens_E1"] = run_h1(e1, "E1")
    R["H2_H4_sens_E1"] = h2_h4(e1, np.random.default_rng(SEED + 30))
    full = pd.read_csv(summary)
    sk = full[full["status"].str.startswith("skipped", na=False)]
    R["sens"] = {"E1_removed": int(len(d) - len(e1)),
                 "E1_by_field": {fc: int(((d.field_code == fc) & (d.share_links_trunc > TRUNC_MAX)).sum()) for fc in FIELDS},
                 "E3": {f"{r.field_code}-{r.group_code}": int(((sk.field_code == r.field_code) & (sk.group_code == r.group_code)).sum())
                        for r in sk.itertuples()}}

    t1 = load_level1(table1)
    R["level1"] = level1(t1, load_maxlog(table3))

    table = []
    for fc in FIELDS:
        x = d[d.field_code == fc]
        table.append({"field": FIELDS[fc], "listed": R["level1"][fc]["listed"],
                      "selfdep_share": R["level1"][fc]["selfdep_share"], "included": len(x),
                      "median_team_size": float(x["median_team_size"].median()),
                      "own": float(x["share_own"].median()), "coauthor": float(x["share_coauthor"].median()),
                      "network": float(x["share_network"].median()),
                      "h_kept_list": R["H5"]["kept"][fc]["excl_shared"]["h_kept_median"],
                      "h_kept_frac": R["H5"]["kept"][fc]["frac_equal"]["h_kept_median"],
                      "V1_rho": R["validation"][fc]["V1_rho"]})
    R["table1"] = table
    pd.DataFrame(table).to_csv(outdir / "note_table1.csv", index=False)

    fig1 = figure1(d, outdir / "Figure_1_citation_sources.png")
    fig1.to_csv(outdir / "figure1_data.csv", index=False)
    figure2(R["H1_primary"], R["level1"], outdir / "Figure_2_reordering.png")
    f2 = [{"field_code": fc, "rule": k, **{m: R["H1_primary"][fc]["rules"][k][m] for m in ("D", "Q")},
           "D_lo": R["H1_primary"][fc]["rules"][k]["D_ci"][0], "D_hi": R["H1_primary"][fc]["rules"][k]["D_ci"][1]}
          for fc in FIELDS for k, *_ in RULES]
    pd.DataFrame(f2).to_csv(outdir / "figure2_data.csv", index=False)

    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if (math.isnan(o) or math.isinf(o)) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        return o
    (outdir / "results.json").write_text(json.dumps(clean(R), indent=1), encoding="utf-8")
    write_report(R, outdir / "results.md")
    print((outdir / "results.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
