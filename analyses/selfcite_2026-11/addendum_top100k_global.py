"""
Addendum to the Chat 27 analysis (written after the single run; descriptive only).

The plan asks for the share of each field's top-100,000 entrants who change
under each switch. This addendum adds the same quantity for the whole list,
so the per-field figures can be read against it. It changes no pre-specified
result.

Usage: python addendum_top100k_global.py TABLE1(.xlsx|.parquet) TABLE3.xlsx OUT.md
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

t1p, t3p, outp = map(Path, sys.argv[1:4])
t1 = pd.read_parquet(t1p) if t1p.suffix == ".parquet" else pd.read_excel(t1p, sheet_name="Data", engine="calamine")
t3 = pd.read_excel(t3p, engine="calamine")
comp = sum(np.log1p(t1[c]) / float(t3[c].iloc[0]) for c in ["hm25 (ns)", "ncs (ns)", "ncsf (ns)", "ncsfl (ns)"])
top_c = t1["rank"] <= 100000
top_ns = t1["rank (ns)"] <= 100000
top_comp = comp.rank(ascending=False, method="min") <= 100000
lines = [
    "# Addendum: top-100,000 changes, whole list (descriptive, added after the run)\n",
    f"- Top 100,000 by c: {int(top_c.sum()):,}; of these, not in the top 100,000 by c (ns): "
    f"{int((top_c & ~top_ns).sum()):,} ({(top_c & ~top_ns).sum() / top_c.sum():.1%}).",
    f"- Top 100,000 by c (ns): {int(top_ns.sum()):,}; of these, not in the top 100,000 by the co-authorship-aware "
    f"composite ranked within the list: {int((top_ns & ~top_comp).sum()):,} ({(top_ns & ~top_comp).sum() / top_ns.sum():.1%}; lower bound).",
]
outp.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
