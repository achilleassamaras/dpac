# Self-citation handling and credit sharing in the 2026 top-2% list

This folder holds the code, the analysis plan and the aggregated results
behind a short note on how the 2026 (version 9) Stanford/Elsevier
science-wide author databases, the "top-2% list", handle self-citations and
co-author credit: Samaras, A.G. (2026), *Credit sharing reorders researchers
more than self-citation handling: A note on the 2026 Stanford/Elsevier
science-wide author databases*, MetaArXiv,
https://doi.org/10.31222/osf.io/njb39_v1. The analysis asks
which of the two choices reorders researchers more, in five fields:
Engineering, Physics & Astronomy, Clinical Medicine, Mathematics &
Statistics, and Economics & Business.

Two levels of data are used:

- **Level 1:** the career-long table of the list itself (all listed
  scientists in the five fields);
- **Level 2:** the OpenAlex citation records of 596 listed scientists, drawn
  in four groups per field, with every citation link classified as own,
  co-author, collaborator-network or independent by
  [`dpac.selfcite`](../../README.md#self-citation-decomposition-dpacselfcite).

The plan was fixed on 12 October 2026, before the citation data were
fetched, and the analysis was run once against it. Only field- and
group-level results are released here: no file in this folder names a
scientist, gives an identifier, or reports a metric for a single scientist.
As the plan requires, the inclusion section of `results.md` lists the five
records left out by field, group and reason (two above 80,000 OpenAlex
citations, three outside the coverage range), without any value.

## Files

| File | Content |
|------|---------|
| [`ANALYSIS_PLAN_2026-11.md`](ANALYSIS_PLAN_2026-11.md) | The analysis plan, verbatim, with a short preface. |
| [`DEPARTURES.md`](DEPARTURES.md) | Departures from the plan and choices it left open (nine items), and one issue found later (item 10). |
| [`draw_sample_2026-11.py`](draw_sample_2026-11.py) | Draws the Level 2 sample from the public list (seed 20261012). |
| [`analyse_selfcite_2026-11.py`](analyse_selfcite_2026-11.py) | The analysis against the plan: inclusion, validation, H1–H5, sensitivity, tables and figures. |
| [`addendum_top100k_global.py`](addendum_top100k_global.py) | Whole-list top-100,000 comparison, added after the run (descriptive). |
| [`make_note_figures.py`](make_note_figures.py) | Redraws the two figures with the note's numbering. |
| [`results.md`](results.md) | Every pre-specified result, as written by the single run. |
| [`results.json`](results.json) | The same results in machine-readable form. |
| [`note_table1.csv`](note_table1.csv) | Field-level values of the note's Table 1. |
| [`figure1_data.csv`](figure1_data.csv) | Data of the note's Figure 2: mean shares of own, co-author and network citations by field and group (Figure 1 in the run's numbering). |
| [`figure2_data.csv`](figure2_data.csv) | Level 2 data of the note's Figure 1: reordering *D* (with 95% interval) and *Q* by field and rule (Figure 2 in the run's numbering). The Level 1 markers come from `results.json` (`level1`). |
| [`addendum_top100k_global.md`](addendum_top100k_global.md) | Output of the addendum script. |
| [`Figure_1_reordering.png`](Figure_1_reordering.png) | The note's Figure 1: what reorders researchers. |
| [`Figure_2_citation_sources.png`](Figure_2_citation_sources.png) | The note's Figure 2: where self-citations come from. |
| [`e1_recheck/`](e1_recheck/) | Sensitivity check E1 recomputed with the corrected flag of v1.1.0 (`results.md`, `results.json`; 13 October 2026, from the run's cache). Only the E1 sections differ from `results.md`; see [`DEPARTURES.md`](DEPARTURES.md), item 10. |

The scripts are those of the run, with the figure legends relabelled
afterwards ([`DEPARTURES.md`](DEPARTURES.md), item 9). Their docstrings and
the plan refer to the author's working sessions by number (*Chat 24*, *26*,
*27*); the preface of the plan explains them. The run used the `selfcite`
module as it stood on 12 October 2026; v1.1.0 corrects one flag that enters
sensitivity check E1 only ([`DEPARTURES.md`](DEPARTURES.md), item 10), and
E1 as recomputed with v1.1.0 is in [`e1_recheck/`](e1_recheck/).

## What is withheld, and why

The following run files are not released:

- `sample_2026-11.csv` and `random_reference_2026-11.csv`: the drawn
  scientists, with names, institutions and list values;
- `authors_sample.csv` and `authors_reference.csv`: the name matches, with
  OpenAlex author ids;
- `selfcite_summary.csv`: one row per scientist, with a label, the list
  values (papers, citations, *h* and others) and the OpenAlex metrics;
- `selfcite_key_PRIVATE.csv`: labels mapped to names and OpenAlex ids;
- `selfcite_shares.png` (one bar per scientist), `selfcite_groups.csv`
  (superseded by `results.md`) and the request cache.

The summary file carries no names, but its list values identify each
scientist when matched against the public list, and the labels can be
re-created with the draw script. Releasing it would publish citation
metrics of named people who did not take part in the study. The sample
itself is not secret: anyone can redraw it from the public list with
[`draw_sample_2026-11.py`](draw_sample_2026-11.py) and the seed. What is
withheld is the link between named scientists and their OpenAlex records
and metrics. The repository's `.gitignore` keeps these file patterns out of
version control.

## How to reproduce

**Inputs.**

- The 2026 list: Ioannidis, J.P.A. (2026). August 2026 data-update for
  "Updated science-wide author databases of standardized citation
  indicators". Elsevier Data Repository, V9.
  https://elsevier.digitalcommonsdata.com/datasets/btchxktzyw/9. The
  scripts read the career-long Table 1 (sheet `Data`) and the career-long
  Table 3 (maxlog normalisers).
- An OpenAlex API key (free at https://openalex.org/settings/api) and,
  for the full run, prepaid OpenAlex credit or several days of the free
  allowance: about 45,000 requests in all, name searches billed at ten list
  requests each, or about US$4–5 at OpenAlex's 2026 prices. The run stops
  cleanly when a day's allowance is used up and resumes from its cache.
- Python 3.9 or later with dpac (`pip install -e .` from the repository
  root) and, for the scripts, `pandas`, `numpy`, `scipy`, `matplotlib`,
  `openpyxl` and `python-calamine`. The addendum script reads the workbooks
  with `python-calamine` only; the other two scripts use it when installed
  (it reads the 100 MB workbook much faster) and fall back to `openpyxl`.

**Steps** (from a working folder outside the repository, since steps 1–3
write files that name scientists):

```bash
# 1. Draw the sample (writes sample_2026-11.csv, random_reference_2026-11.csv
#    and sample_2026-11_design.csv; the first two name scientists)
python draw_sample_2026-11.py "Table_1_Authors_career_....xlsx" .

# 2. Match the list rows to OpenAlex author ids
export OPENALEX_API_KEY=your-key           # Windows cmd: set OPENALEX_API_KEY=your-key
python -m dpac.selfcite probe
python -m dpac.selfcite resolve --input sample_2026-11.csv --output authors_sample.csv
python -m dpac.selfcite resolve --input random_reference_2026-11.csv --output authors_reference.csv

# 3. Decompose the citations (the settings of the released run)
python -m dpac.selfcite run --authors authors_sample.csv authors_reference.csv \
    --output-dir selfcite_out --max-citations 80000

# 4. Analyse, add the whole-list comparison, redraw the figures
python analyse_selfcite_2026-11.py selfcite_out/selfcite_summary.csv sample_2026-11_design.csv \
    "Table_1_Authors_career_....xlsx" "Table_3_....xlsx" results
python addendum_top100k_global.py "Table_1_Authors_career_....xlsx" "Table_3_....xlsx" \
    results/addendum_top100k_global.md
python make_note_figures.py selfcite_out/selfcite_summary.csv results/results.json results
```

The other run settings are the module defaults: citations from 1996–2025;
articles, reviews, books and book chapters; four researchers at a time.
`DPAC_SELFCITE_CACHE` sets the cache folder (default
`~/.dpac_cache/selfcite`).

**Expect differences.** The released results come from a single run on
12 October 2026, with OpenAlex as it was that day. OpenAlex changes
continuously (new works, citations and author disambiguation), and the name
search can return different candidates, so a re-run will reproduce the
procedure exactly but the numbers only approximately. Level 1 results depend
on the list alone and reproduce exactly. Sensitivity check E1 differs from
`results.md` under v1.1.0, which corrects the truncation flag; the values
to expect are those in [`e1_recheck/`](e1_recheck/)
([`DEPARTURES.md`](DEPARTURES.md), item 10).

## Citation

Please cite the software (see the repository [`README.md`](../../README.md)
and [`CITATION.cff`](../../CITATION.cff)) and the note:

> Samaras, A. G. (2026). Credit sharing reorders researchers more than
> self-citation handling: A note on the 2026 Stanford/Elsevier science-wide
> author databases. *MetaArXiv preprint*.
> https://doi.org/10.31222/osf.io/njb39_v1
