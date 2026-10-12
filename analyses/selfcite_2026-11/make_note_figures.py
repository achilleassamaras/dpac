"""Redraw the two note figures from the single analysis run (results.json + summary), with the
note's numbering: Figure 1 = reordering, Figure 2 = citation sources. No statistics are recomputed
except the group means plotted in Figure 2, which are the same as in figure1_data.csv."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import importlib
A = importlib.import_module("analyse_selfcite_2026-11")

summary, results, outdir = map(Path, sys.argv[1:4])
R = json.loads(results.read_text(encoding="utf-8"))
d, _, _ = A.load_level2(summary)
A.figure2(R["H1_primary"], R["level1"], outdir / "Figure_1_reordering.png")
A.figure1(d, outdir / "Figure_2_citation_sources.png")
print("ok")
