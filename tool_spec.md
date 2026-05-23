# `dpac` — Tool specification (v1.0.0)

**Purpose.** This document specifies the design of `dpac`, a small Python
package that computes paper-level and author-level bibliometric quantities from an
OpenAlex publication record under a chosen contribution-share scheme. The package
is the empirical software companion to the preprint *"A declared percentage-based
author-contribution system for weighted research metrics: a proposal"* and provides
the working artefact referenced from §5.2 of that preprint.

The package supports two algorithmic imputation schemes — equal share and harmonic
counting — that stand in for the declared shares the proposal specifies. The
imputations are not a substitute for declared shares; they are placeholders that
allow the two-tier comparison of §3.2 of the preprint to be exercised against real
publication records while no database yet carries declared-share metadata.

## Data model

The unit of input is an OpenAlex `Work` record, retrieved by ORCID through the
public OpenAlex API. The fields used by the package are: `id`, `doi`,
`publication_year`, `cited_by_count`, the `authorships` array (in published byline
order), `authorships[].author.orcid`, `authorships[].author_position` (one of
`first`, `middle`, or `last`; used as a consistency-check signal only), and the
host venue's `issn_l` when present. The author of interest is identified by ORCID
and matched against the `authorships` array on each work.

A normalised internal record carries, per work, the author count *n*, the focal
author's 1-indexed byline rank (read from the index of the matching entry in the
`authorships` array; see "Position mapping" under design decisions), the citation
count, the publication year, and any optional paper-level metric the user supplies
alongside (for example a journal-level score keyed by ISSN).

## Imputation schemes

Each scheme produces a share *c*<sub>i,p</sub> ∈ [0, 1] satisfying
Σ<sub>i</sub> *c*<sub>i,p</sub> = 1 across the author list of paper *p*.

**Equal share.** *c*<sub>i,p</sub> = 1/*n*. The simplest scheme; assigns the same
fraction to every co-author regardless of byline order. Implemented as the baseline
for comparison.

**Harmonic counting** (Hodge and Greenberg, 1981; Hagen, 2008, 2010). For a paper
with *n* co-authors, the share assigned to the author at byline position *k* is

> *c*<sub>k,p</sub> = (1/*k*) / Σ<sub>j=1..n</sub> (1/*j*).

The denominator is the *n*-th harmonic number *H*<sub>n</sub>. Harmonic counting
is the most defensible position-based scheme in the literature when bylines are
ordered by contribution. The byline rank *k* is read from the order of the
`authorships` array on the OpenAlex `Work` record — that array preserves the
published byline order — rather than from the categorical `author_position`
field, so that middle-position ranks are exact rather than approximated.

Harmonic counting presumes a contribution-ordered byline convention: authors are
listed in decreasing order of contribution. The presumption holds across much of
chemistry, the medical and life sciences, psychology, and the engineering
disciplines (Marušić et al., 2011), but not in fields that use alphabetical or
otherwise non-contribution-ordered listings — mathematics, parts of economics,
and high-energy physics consortia among them. The interpretation of
harmonic-counting results in those fields is the user's responsibility, and
harmonic numbers reported for cohorts that span the boundary should carry the
caveat explicitly.

A third scheme — **declared shares**, the proposal's target case — is implemented
as a passthrough that reads explicit share values from a user-supplied CSV (one
row per paper, one column per co-author or one column per ORCID), validates the
row-sums to 1.0 within tolerance, and applies the values directly. This scheme is
operationally identical to the proposed system once declared shares are available
in publication metadata.

## Metric definitions

For a focal author with publication record {*p*}, citation count *m*<sub>p</sub>
on each paper, and share *c*<sub>i,p</sub> under the chosen scheme, the package
computes:

- **Paper count.** The cardinality of {*p*}.
- **Total citations (paper-level).** *C* = Σ<sub>p</sub> *m*<sub>p</sub>.
- **Weighted citations (author-level).** *C*<sub>w</sub> = Σ<sub>p</sub>
  *c*<sub>i,p</sub> · *m*<sub>p</sub>.
- **Raw *h*-index.** The largest integer *h* such that at least *h* papers each
  have at least *h* citations (Hirsch, 2005).
- **Fractional *h*-index.** The fractional analogue of Egghe (2008): the citation
  series {*m*<sub>p</sub>} is replaced by the share-weighted series
  {*c*<sub>i,p</sub> · *m*<sub>p</sub>}, sorted in descending order; the
  fractional *h*-index is the largest *h* such that the *h*-th sorted weighted
  value is at least *h*. The output is generally non-integer; the package returns
  the raw real-valued index along with its floor.
- **Top-share papers.** A diagnostic listing of the focal author's papers ranked
  by author-level weighted citation contribution.

## Public interface

### Function-level

A single high-level entry point assembles a researcher's full result set under one
or more schemes:

```python
from dpac import compute_profile

result = compute_profile(orcid="0000-0000-0000-0000",
                        schemes=["equal", "harmonic"],
                        cache_dir=".dpac_cache")
print(result.summary())   # tabular comparison
```

Lower-level functions are exposed for direct use: `fetch_orcid_works(orcid)`,
`apply_scheme(works, scheme)`, `paper_level_metrics(works)`,
`author_level_metrics(works, shares)`, and `fractional_h_index(weighted_citations)`.

### CLI

The command-line interface mirrors the high-level function. A single ORCID query
prints the comparison table to stdout:

```
dpac --orcid 0000-0000-0000-0000 --schemes equal,harmonic
dpac --orcid 0000-0000-0000-0000 --schemes equal,harmonic --json > out.json
dpac --orcid 0000-0000-0000-0000 --schemes declared --shares-csv my_shares.csv
```

A batch mode accepts a file of ORCIDs and produces the cross-researcher table that
mirrors Table 1 of the preprint:

```
dpac --orcid-list orcids.txt --schemes equal,harmonic --output table.csv
```

## Repository layout

```
dpac/
├── README.md
├── tool_spec.md             (this file)
├── CHANGELOG.md
├── CITATION.cff
├── LICENSE
├── requirements.txt
├── pyproject.toml
├── dpac/
│   ├── __init__.py
│   ├── openalex.py          API client, caching, throttling, byline-order resolution
│   ├── schemes.py           imputation schemes (equal, harmonic, declared)
│   ├── metrics.py           paper-level, author-level, h-index variants
│   ├── profile.py           high-level orchestration; result container
│   ├── sample.py            stratified random sampling from an OpenAlex topic
│   └── cli.py               command-line entry point
├── tests/
│   ├── test_metrics.py      unit tests on synthetic inputs
│   └── test_schemes.py      unit tests for schemes and byline-order resolution
└── demonstration.ipynb      empirical demonstration notebook
```

## Design decisions

The following choices are made deliberately for v1.0.0.

- **Library footprint kept minimal.** `requests` for the API, the Python standard
  library for everything else. No `pandas` dependency in the core (the notebook is
  free to import it); no plotting library in the core (`matplotlib` is invoked
  only in the notebook).
- **Caching is on by default and on disk.** Each ORCID query is stored as a JSON
  file keyed by ORCID and query parameters; subsequent runs read from cache. The
  cache directory defaults to `~/.dpac_cache` and is overridable.
- **Throttling.** Requests carry a `User-Agent` identifying the package and a
  mailto contact (configurable through an environment variable, per the OpenAlex
  polite-pool convention). A small inter-request sleep is applied.
- **ORCID matching is strict.** A work is included in the focal author's record
  only if the ORCID matches one of the entries in `authorships[].author.orcid`.
  Name-based fallback is not implemented; the user is directed to ensure the
  ORCID is well-populated on OpenAlex before running.
- **Position mapping.** The focal author's byline rank is read directly from
  the index of the matching entry in the `authorships` array on the OpenAlex
  `Work` record, since OpenAlex preserves the published byline order in that
  array. The categorical `author_position` field (`first`/`middle`/`last`) is
  read only as a light consistency-check signal: when it disagrees with the
  array-derived rank (e.g. `first` reported for an entry that is not at array
  index 0), a debug log entry is emitted and the array-derived rank is used
  regardless. Middle-position ranks are therefore exact, not collapsed to a
  central approximation.

## Deferred to a future release

The following items remain open for subsequent work.

- **JCR / SCImago integration.** Author-level analogues of journal-impact metrics
  require a journal-score table keyed by ISSN. The current release accepts
  user-supplied paper-level metrics through the function interface; a future
  release may bundle a JCR or SCImago wrapper.
- **Cross-source reconciliation.** A second API (Crossref, Web of Science, Scopus)
  could verify the OpenAlex author lists and citation counts. The current release
  trusts OpenAlex.
- **Declared-share metadata parsing.** Once any database starts to expose declared
  shares in the canonical channel proposed in the preprint, a future release will
  read them directly and the declared-shares scheme will stop being a CSV
  passthrough.

## Changelog

The full version history is maintained in [`CHANGELOG.md`](CHANGELOG.md).

## References

The two-line bibliographic anchors for the technical content above are:

- Egghe, L. (2008). Mathematical theory of the *h*- and *g*-index in case of
  fractional counting of authorship. *Journal of the American Society for
  Information Science and Technology*, 59(10), 1608–1616.
- Hagen, N. T. (2008). Harmonic allocation of authorship credit: source-level
  correction of bibliometric bias assures accurate publication and citation
  analysis. *PLOS ONE*, 3(12), e4021.
- Hagen, N. T. (2010). Harmonic publication and citation counting: sharing
  authorship credit equitably — not equally, geometrically or arithmetically.
  *Scientometrics*, 84(3), 785–793.
- Hirsch, J. E. (2005). An index to quantify an individual's scientific research
  output. *Proceedings of the National Academy of Sciences*, 102(46),
  16569–16572.
- Hodge, S. E., and Greenberg, D. A. (1981). Publication credit. *Science*,
  213(4511), 950.
- Marušić, A., Bošnjak, L., and Jerončić, A. (2011). A systematic review of
  research on the meaning, ethics and practices of authorship across scholarly
  disciplines. *PLOS ONE*, 6(9), e23477.
