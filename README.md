# `dpac`

> **Declared percentage-based author-contribution metrics from OpenAlex
> publication records.**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20359542.svg)](https://doi.org/10.5281/zenodo.20359542)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

`dpac` is the empirical software companion to the preprint *"A declared
percentage-based author-contribution system for weighted research metrics:
a proposal"* (Samaras, 2026, MetaArXiv). The package computes paper-level
and author-level bibliometric quantities — total citations, weighted
citations, raw and fractional *h*-indices — for any researcher whose ORCID
is registered in OpenAlex, under a chosen contribution-share scheme.

The package exists to let the two-tier comparison of §3.2 of the preprint
be exercised against real publication records without waiting for
declared-share metadata to become available in any database.

Since v1.1.0, the package also decomposes a researcher's citations into own,
co-author, collaborator-network and independent citations
([`dpac.selfcite`](#self-citation-decomposition-dpacselfcite)), and the
[`analyses/`](analyses/) folder holds the code and aggregated results of
analyses made with it.

## Important caveat

**Declared shares are not yet available in any bibliometric database.** The
proposed system requires that co-authors declare a contribution share for
each paper at acceptance, and that the declaration be carried in the
published record alongside the qualitative CRediT statement. Until that
pathway is operational, this package fills the gap with two algorithmic
imputation schemes that stand in for the declared shares:

- **Equal share.** 1/*n* across the author list. The simplest scheme;
  assigns the same fraction to every co-author regardless of byline order.
- **Harmonic counting** (Hodge and Greenberg, 1981; Hagen, 2008, 2010).
  Position-based; assigns *c*<sub>k</sub> = (1/*k*) / *H*<sub>n</sub>, with
  *H*<sub>n</sub> the *n*-th harmonic number and *k* the focal author's
  1-indexed byline rank on the paper. The byline rank *k* is read from the
  index of the matching entry in OpenAlex's `authorships` array (which
  preserves the published byline order), not from the categorical
  `author_position` field. Harmonic counting presumes a contribution-
  ordered byline convention: authors are listed in decreasing order of
  contribution. The presumption holds across much of chemistry, medicine,
  the life sciences, psychology, and the engineering disciplines, but does
  not hold in fields that use alphabetical or otherwise non-contribution-
  ordered listings — mathematics, parts of economics, and high-energy
  physics consortia among them. The interpretation of harmonic-counting
  results in those fields is the user's responsibility.

A third scheme, **declared shares**, is implemented as a passthrough for
user-supplied values; it is the proposal's target case and is operationally
identical to the proposed system once databases populate the field.

Results computed under the equal-share or harmonic schemes are *not*
substitutes for declared shares. They are stand-ins for demonstration and
sensitivity analysis. Any interpretation of an individual researcher's
metrics under these schemes should carry that qualifier.

## Installation

The package targets Python 3.9 or later. From a clone of the repository:

```bash
pip install -e .
```

For the demonstration notebook, install the notebook extras:

```bash
pip install -e ".[notebook]"
```

For development:

```bash
pip install -e ".[dev]"
pytest tests/
```

## Quick start

### Python

```python
from dpac import compute_profile

result = compute_profile(
    orcid="0000-0000-0000-0000",
    schemes=["equal", "harmonic"],
)
print(result.summary())
```

### Command line

```bash
# Single researcher
dpac --orcid 0000-0000-0000-0000

# JSON output
dpac --orcid 0000-0000-0000-0000 --json

# Cross-researcher comparison table
dpac --orcid-list orcids.txt --output table.csv

# Declared shares from a CSV
dpac --orcid 0000-0000-0000-0000 --schemes declared \
     --shares-csv my_shares.csv
```

### OpenAlex API key

OpenAlex meters usage per day and identifies users by API key, free at
https://openalex.org/settings/api; without a key, the daily allowance is
small. Set the key in the environment variable `OPENALEX_API_KEY`:

```bash
export OPENALEX_API_KEY=your-key        # Windows cmd: set OPENALEX_API_KEY=your-key
```

In Python, `api_key=` can also be passed to `compute_profile`,
`fetch_orcid_works` or `OpenAlexClient`. The key is sent as the `api_key`
query parameter and is never printed: log and error messages mask it.

The `--mailto` option, `mailto=` and `DPAC_MAILTO` are still accepted and
passed on, but OpenAlex has ignored `mailto` since it replaced its polite
pool with API keys in 2026.

## Finding an ORCID

An ORCID identifier takes the form `NNNN-NNNN-NNNN-NNNN`. To find one's
own:

- Visit https://orcid.org and sign in or register; the identifier appears
  at the top of the profile page.
- For another researcher, search at https://orcid.org/orcid-search or
  check the author's institutional or paper-affiliation page.

The package matches works to the focal author by ORCID and will silently
discard works on which the ORCID is not registered in the OpenAlex
authorships list. Coverage is therefore best for researchers whose ORCID
is well-populated on OpenAlex; a researcher with a partially-populated
ORCID may appear to have fewer publications than they do. Inspecting the
OpenAlex profile directly (`https://openalex.org/orcid/NNNN-NNNN-NNNN-NNNN`)
is a useful sanity check before drawing conclusions from the metrics.

## ORCID selection — guidance

The schemes implemented here are sensitive to the field-byline convention.
Three principles for selecting ORCIDs in a comparison exercise:

1. **Hold the field roughly constant.** Comparing a mathematician (whose
   field uses alphabetical bylines) against an experimental biologist
   (whose field uses contribution-ordered bylines) under the harmonic
   scheme will confound the byline convention with the contribution
   pattern. Comparisons are most defensible within a field.
2. **Hold the career stage roughly constant when reporting summary
   numbers.** The two-tier display absorbs career-stage differences
   honestly, but cross-researcher tables read more cleanly when career
   length is broadly comparable.
3. **Use your own ORCID first.** The most defensible application of the
   tool is self-applied. The privacy implications of running the tool on
   other researchers' ORCIDs without their knowledge are the user's call.

## What the package returns

For each researcher, the output is a side-by-side comparison of:

| Column | Definition |
|--------|------------|
| Paper-level total citations | Σ<sub>p</sub> *m*<sub>p</sub> across the focal author's works. |
| Paper-level raw *h*-index | Standard Hirsch (2005) integer index on the unweighted citation series. |
| Author-level weighted citations (per scheme) | Σ<sub>p</sub> *c*<sub>i,p</sub> · *m*<sub>p</sub> under the chosen scheme. |
| Author-level fractional *h*-index (per scheme) | Egghe (2008) fractional *h*-index on the share-weighted citation series. |
| Author-level effective papers (per scheme) | Σ<sub>p</sub> *c*<sub>i,p</sub> — a fractional paper count. |

When more than one scheme is requested, the author-level columns repeat
per scheme. The demonstration notebook formats the cross-researcher
version of this comparison as a table that mirrors Table 1 of the preprint.

## Long author lists

OpenAlex lists at most the first 100 authors of a work, and its 2026 API no
longer returns the true author count (`authors_count`). A work with exactly
100 listed authors is therefore flagged (`Work.authors_capped`, counted as
`n_works_capped` in the result and in the batch table): its true author
count is unknown, so the equal and harmonic shares computed for it are upper
bounds. Works on which the focal author comes after the 100th name cannot be
matched by ORCID and are skipped; a warning gives their number. When
OpenAlex does return `authors_count`, the true count is used.

## Self-citation decomposition (`dpac.selfcite`)

The `selfcite` module, added in v1.1.0, asks where a researcher's citations
come from. Every citation link, from a citing work *Q* to a cited work *P* of
the focal author *A*, is placed in exactly one class:

| Class | Definition |
|-------|------------|
| Own | *A* is an author of *Q*. |
| Co-author | *A* is not on *Q*, but another author of *P* is. |
| Collaborator network | Neither, but an author of *Q* had co-authored with *A* in or before the year of *Q*. |
| Independent | None of the above. |

The Stanford/Elsevier science-wide author databases (the "top-2% list")
count own and co-author links as self-citations, since *Q* and *P* share an
author; Scopus's author-level option removes own links only; neither removes
network links.

For each researcher, total citations, the *h*-index, Schreiber's (2008)
hm-index and the author-level credit under equal and harmonic shares are
recomputed under seven rules: all citations; without own links; without own
and co-author links (the list's rule); also without network links; and three
fractional rules that weight each link by the share of *Q* not held by
authors of *P* (equal or harmonic shares; Schubert, Glänzel and Thijs, 2006),
or not held by authors of *P* and earlier collaborators of *A*. Declared
shares would replace the imputed ones in both places.

### Command line

```bash
python -m dpac.selfcite probe                     # API key, page size, today's allowance
python -m dpac.selfcite resolve --input list_rows.csv --output authors_list.csv
python -m dpac.selfcite run --authors authors_list.csv --output-dir selfcite_out
python -m dpac.selfcite report --output-dir selfcite_out
python -m dpac.selfcite cohort --output authors_cohort.csv
```

- `resolve` matches rows of the top-2% list (columns `authfull`, `inst_name`,
  `cc2`, `np6025`, `nc9625`) to OpenAlex author ids by name search. Matches
  are flagged `high`, `check` or `none`; only rows with `use` = `Y` (set
  automatically for `high`) are run.
- `run` reads one or more author files (`openalex_id`, `use`, and optional
  `label`, `group` and `field` columns), processes four researchers at a time
  (`--workers`), and caches every response (`DPAC_SELFCITE_CACHE`, default
  `~/.dpac_cache/selfcite`). When the day's OpenAlex allowance is used up,
  it stops cleanly; the same command resumes from the cache. Records above
  `--max-citations` OpenAlex citations (default 60,000) are skipped.
- `report` rebuilds the group table and figure without new requests.
- `cohort` re-draws the ocean-engineering cohort of §5.2 of the preprint.

Each researcher costs about 5 list requests plus about 7 for every 1,000
citations; a name search costs as much as ten list requests.

### Outputs and privacy

`run` writes four files to the output folder:

- `selfcite_summary.csv` — one row per researcher: label, group, the input
  columns that do not name the person, and the metrics;
- `selfcite_groups.csv` — medians per group (and per field, when given);
- `selfcite_shares.png` — the four classes for every researcher, by group;
- `selfcite_key_PRIVATE.csv` — labels mapped to names and OpenAlex ids.

The key file must not be shared. Neither should the summary file when its
rows carry values copied from a public list, since those values identify the
person; [`analyses/selfcite_2026-11/`](analyses/selfcite_2026-11/) shows what
can be released instead.

## Caching

OpenAlex responses are cached to disk on first fetch, keyed by ORCID. The
default cache directory is `~/.dpac_cache`. Cached responses are read
silently on subsequent runs; pass `--no-cache` or `use_cache=False` to
force a refresh. Caching is on by default to be polite to the public API
and to keep notebook re-runs fast.

## Analyses

- [`analyses/selfcite_2026-11/`](analyses/selfcite_2026-11/) — self-citation
  handling and credit sharing in the 2026 (version 9) Stanford/Elsevier
  science-wide author databases: five fields, 596 listed scientists. The
  analysis plan, the scripts and the field- and group-level results; no
  scientist-level data. Reported in the note cited below
  (https://doi.org/10.31222/osf.io/njb39_v1).

## Versioning and changelog

The current release is **v1.1.0**. It adds the `selfcite` module and the
`analyses/` folder, and adapts the OpenAlex client to the 2026 API (page
size 100, API key, author lists capped at 100 names). v1.0.0 was the first
archived, citable release. The full version history is in
[`CHANGELOG.md`](CHANGELOG.md).

## Citation

If this package is used in published work, please cite both the preprint
and the software:

> Samaras, A. G. (2026). A declared percentage-based author-contribution
> system for weighted research metrics: a proposal. *MetaArXiv preprint*.
> https://doi.org/10.31222/osf.io/3mkz2_v1

> Samaras, A. G. (2026). *dpac: Declared percentage-based
> author-contribution metrics from OpenAlex publication records* (v1.1.0).
> Zenodo. https://doi.org/10.5281/zenodo.20359542

Work that uses the `selfcite` module or the results in
[`analyses/selfcite_2026-11/`](analyses/selfcite_2026-11/) should also cite
the note that reports them:

> Samaras, A. G. (2026). Credit sharing reorders researchers more than
> self-citation handling: A note on the 2026 Stanford/Elsevier science-wide
> author databases. *MetaArXiv preprint*.
> https://doi.org/10.31222/osf.io/njb39_v1

A machine-readable equivalent of the first two entries is provided in
[`CITATION.cff`](CITATION.cff), so that GitHub's "Cite this repository"
affordance returns them.

## Licence

MIT. See [`LICENSE`](LICENSE) for the full text.

## See also

- [`tool_spec.md`](tool_spec.md) — full design specification, including
  the metric definitions, the `selfcite` rules and the design decisions.
- [`CHANGELOG.md`](CHANGELOG.md) — version history.
- [`analyses/`](analyses/) — code and aggregated results of analyses made
  with the package.
- [`demonstration.ipynb`](demonstration.ipynb) — a working empirical
  demonstration that the user runs against real ORCIDs on their own
  machine.

## References

- Egghe, L. (2008). Mathematical theory of the *h*- and *g*-index in case
  of fractional counting of authorship. *Journal of the American Society
  for Information Science and Technology*, 59(10), 1608–1616.
- Hagen, N. T. (2008). Harmonic allocation of authorship credit:
  source-level correction of bibliometric bias assures accurate
  publication and citation analysis. *PLOS ONE*, 3(12), e4021.
- Hagen, N. T. (2010). Harmonic publication and citation counting:
  sharing authorship credit equitably — not equally, geometrically or
  arithmetically. *Scientometrics*, 84(3), 785–793.
- Hirsch, J. E. (2005). An index to quantify an individual's scientific
  research output. *Proceedings of the National Academy of Sciences*,
  102(46), 16569–16572.
- Hodge, S. E., and Greenberg, D. A. (1981). Publication credit.
  *Science*, 213(4511), 950.
- Schreiber, M. (2008). A modification of the *h*-index: the
  *h*<sub>m</sub>-index accounts for multi-authored manuscripts. *Journal
  of Informetrics*, 2(3), 211–216.
- Schubert, A., Glänzel, W., and Thijs, B. (2006). The weight of author
  self-citations. A fractional approach to self-citation counting.
  *Scientometrics*, 67(3), 503–514.
