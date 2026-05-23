# `dpac`

> **Declared percentage-based author-contribution metrics from OpenAlex
> publication records.**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.PLACEHOLDER.svg)](https://doi.org/10.5281/zenodo.PLACEHOLDER) <!-- replace PLACEHOLDER with the Zenodo DOI assigned at first tagged release -->
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

### Polite-pool contact

OpenAlex asks API users to identify themselves by mailto so that requests
can be routed through the polite pool. Either pass `--mailto your@email` on
the CLI, set the environment variable `DPAC_MAILTO`, or pass `mailto=` to
`compute_profile`.

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

## Caching

OpenAlex responses are cached to disk on first fetch, keyed by ORCID. The
default cache directory is `~/.dpac_cache`. Cached responses are read
silently on subsequent runs; pass `--no-cache` or `use_cache=False` to
force a refresh. Caching is on by default to be polite to the public API
and to keep notebook re-runs fast.

## Versioning and changelog

The current release is **v1.0.0** — the first archived, citable release.
The full version history is in [`CHANGELOG.md`](CHANGELOG.md).

## Citation

If this package is used in published work, please cite both the preprint
and the software:

> Samaras, A. G. (2026). A declared percentage-based author-contribution
> system for weighted research metrics: a proposal. *MetaArXiv preprint*.

> Samaras, A. G. (2026). *dpac: Declared percentage-based
> author-contribution metrics from OpenAlex publication records* (v1.0.0).
> Zenodo. https://doi.org/10.5281/zenodo.PLACEHOLDER

A machine-readable equivalent is provided in [`CITATION.cff`](CITATION.cff)
so that GitHub's "Cite this repository" affordance returns the entries
above.

## Licence

MIT. See [`LICENSE`](LICENSE) for the full text.

## See also

- [`tool_spec.md`](tool_spec.md) — full design specification, including
  the metric definitions and the design decisions taken for v1.0.0.
- [`CHANGELOG.md`](CHANGELOG.md) — version history.
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
