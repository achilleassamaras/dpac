# `dpac` — Tool specification (v1.1.0)

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
count, the publication year, a flag for author lists capped at 100 names (see
"Author lists capped at 100 names" under design decisions), and any optional
paper-level metric the user supplies alongside (for example a journal-level score
keyed by ISSN).

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
│   ├── selfcite.py          citation-source decomposition and self-citation rules
│   └── cli.py               command-line entry point
├── tests/
│   ├── test_metrics.py      unit tests on synthetic inputs
│   ├── test_schemes.py      unit tests for schemes and byline-order resolution
│   ├── test_openalex.py     page size, API key, capped author lists
│   ├── test_selfcite.py     classification, rules, metrics, caching
│   └── test_selfcite_parallel.py   parallel runs, stopping, capped lists, outputs
├── analyses/
│   └── selfcite_2026-11/    plan, scripts and aggregated results of the 2026 analysis
└── demonstration.ipynb      empirical demonstration notebook
```

## Design decisions

The following choices were made deliberately for v1.0.0; the API key, page-size
and author-list items were added in v1.1.0 for the 2026 OpenAlex API.

- **Library footprint kept minimal.** `requests` for the API, the Python standard
  library for everything else. No `pandas` dependency in the core (the notebook is
  free to import it); no plotting library in the core (`matplotlib` is invoked
  only in the notebook).
- **Caching is on by default and on disk.** Each ORCID query is stored as a JSON
  file keyed by ORCID and query parameters; subsequent runs read from cache. The
  cache directory defaults to `~/.dpac_cache` and is overridable.
- **Throttling and API key.** Requests carry a `User-Agent` identifying the
  package (`dpac/1.1`) and, when one is set, the OpenAlex API key
  (`OPENALEX_API_KEY`, sent as the `api_key` query parameter). The key is masked
  in every log and error message; HTTP errors carry OpenAlex's own message
  instead of the request URL. A `mailto` contact is still passed on when set,
  although OpenAlex has ignored it since it replaced its polite pool with API
  keys in 2026. A small inter-request sleep is applied.
- **Page size.** Requests ask for 100 results per page (`per_page`), the maximum
  that the 2026 OpenAlex API accepts; larger values are rejected with HTTP 400.
- **Author lists capped at 100 names.** OpenAlex lists at most the first 100
  authors of a work. When the record carries `authors_count`, *n* is the true
  count. When it does not (the 2026 API no longer returns the field) and exactly
  100 names are listed, *n* is 100, a lower bound, and the work is flagged
  (`authors_capped`); the equal and harmonic shares on it are then upper bounds.
  Works on which the focal author comes after the 100th name cannot be matched by
  ORCID and are skipped, with a warning giving their number.
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

## Self-citation decomposition (`dpac.selfcite`)

Added in v1.1.0. The module asks where a researcher's citations come from, and
how citations, *h*, hm and author-level credit change under different
self-citation rules.

**Data.** For the focal author *A*, identified by OpenAlex author id, the module
fetches every work of the chosen types (default: article, review, book chapter,
book) with its year, citation count and author ids, and then every work citing
them, published in a chosen window (default 1996–2025), with its year, author ids
and references. Citing works are requested in `cites:` filters of up to 100 work
ids; a filter that OpenAlex rejects as too long is split in two. Responses are
reduced to ids, years and author lists before caching (gzip JSON, keyed by a
cache version), so that re-runs read from the cache at no cost.

**Classes.** Each distinct link from a citing work *Q* to a cited work *P* of *A*
is placed in exactly one class: *own* (*A* is on *Q*); *co-author* (*A* is not
on *Q*, another author of *P* is); *collaborator network* (neither, but an
author of *Q* had co-authored a work of *A* in or before the year of *Q*);
*independent* (none of these).

**Rules.** Seven rules weight the links:

| Rule | Weight of a link |
|------|------------------|
| `all` | 1 |
| `excl_own` | 0 for own links, else 1 |
| `excl_shared` (the top-2% list's rule) | 0 for own and co-author links, else 1 |
| `excl_network` | 1 for independent links only |
| `frac_equal` | 1 − (authors of *Q* who are on *P*) / *n*<sub>Q</sub> |
| `frac_harmonic` | 1 − (harmonic byline shares on *Q* of those authors) |
| `frac_network` | 1 − (share of *Q* held by authors of *P* or by earlier collaborators of *A*) |

The fractional rules follow the equal-share overlap idea of Schubert, Glänzel and
Thijs (2006); declared shares would replace the imputed ones.

**Metrics.** Under each rule: weighted citations, *h*, Schreiber's (2008) hm
(each paper advances the effective rank by 1/*n*), and the author-level credit
Σ<sub>p</sub> *c*<sub>A,p</sub> · *m*<sub>p</sub> under equal and harmonic
shares. Also reported: the share of links in each class, the list-rule
self-citation rate, the co-author share of self-citations, citations per citing
paper, the median team size, and two flags for author lists capped at 100 names
(`n_works_over_100_authors`, `share_links_trunc`). When the focal author is not
among the listed names of a capped list, the harmonic share is the mean share of
the unlisted positions (true count known) or zero.

**Running.** Researchers are processed in parallel (default four at a time). All
workers share one throttle (start slots booked under a lock), one request
counter and one cache; each thread has its own HTTP session. When OpenAlex
reports the daily allowance used up, every worker stops at its next request and
the outputs written so far are kept; the same command resumes. Records above a
citation cap (default 60,000 OpenAlex citations) are skipped.

**Name resolution.** For rows of the top-2% list, candidates from an OpenAlex
author search (filtered by country when given) are scored on surname and given
name, institution, works count and citation count. A match is `high` when its
score is at least 6.5 and at least 1.5 above the runner-up, `check` otherwise,
and `none` when no candidate shares the surname.

**Outputs and privacy.** The summary file carries labels, groups, the input
columns that do not name the person, and the metrics; names, institutions and
OpenAlex ids go only to `selfcite_key_PRIVATE.csv`. Input columns copied from a
public list can still identify a person, so summary files built from such lists
are not for release; the `analyses/` folder releases field- and group-level
results only.

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
- Schreiber, M. (2008). A modification of the *h*-index: the *h*<sub>m</sub>-index
  accounts for multi-authored manuscripts. *Journal of Informetrics*, 2(3),
  211–216.
- Schubert, A., Glänzel, W., and Thijs, B. (2006). The weight of author
  self-citations. A fractional approach to self-citation counting.
  *Scientometrics*, 67(3), 503–514.
- Marušić, A., Bošnjak, L., and Jerončić, A. (2011). A systematic review of
  research on the meaning, ethics and practices of authorship across scholarly
  disciplines. *PLOS ONE*, 6(9), e23477.
