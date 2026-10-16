# Changelog

All notable changes to `dpac` are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Repository changes after the v1.1.0 release; no change to the package.

### Added

- `analyses/selfcite_2026-11/e1_recheck/`: sensitivity check E1 of the
  2026-11 analysis recomputed on 13 October 2026 with the corrected
  truncation flag of v1.1.0, from the run's cache (`results.md`,
  `results.json`). 13 researchers are left out instead of 12; only the E1
  sections differ, and every conclusion holds (`DEPARTURES.md`, item 10).
- The note that reports the 2026-11 analysis, now deposited: Samaras, A. G.
  (2026). Credit sharing reorders researchers more than self-citation
  handling: A note on the 2026 Stanford/Elsevier science-wide author
  databases. *MetaArXiv preprint*. https://doi.org/10.31222/osf.io/njb39_v1.
  Cited in the README (Analyses and Citation sections) and in the analysis
  folder's README.

## [1.1.0] — 2026-10-12

*Concept DOI: `10.5281/zenodo.20359542`. Version DOI: `10.5281/zenodo.23325076`.*

Adds the self-citation decomposition module and the first analysis folder,
and adapts the OpenAlex client to the 2026 OpenAlex API, which rejects the
page size of 200 that v1.0.0 requested.

### Added

- `dpac.selfcite` (`python -m dpac.selfcite`): decomposition of a
  researcher's OpenAlex citations into own, co-author, collaborator-network
  and independent citations, with total citations, *h*, hm (Schreiber, 2008)
  and equal- and harmonic-share author-level credit recomputed under seven
  self-citation rules: all citations; without own citations; without own and
  co-author citations (the rule of the Stanford/Elsevier science-wide author
  databases); also without network citations; and three fractional rules
  weighting each link by the share of the citing paper not held by
  overlapping authors (equal, harmonic and network variants). Researchers
  are processed four at a time with one shared throttle, request counter and
  cache; a run stops cleanly when the day's OpenAlex allowance is used up and
  resumes from the cache. Commands: `probe`, `cohort`, `resolve` (name
  matching for rows of the Stanford/Elsevier list), `run` and `report`.
  Names, institutions and OpenAlex ids go only to a private key file.
  Compared with the version used for the 2026-11 analysis, a citing paper
  whose 100-name author list carries no true count is now flagged as
  touching a capped list (see `analyses/selfcite_2026-11/DEPARTURES.md`,
  item 10).
- `analyses/selfcite_2026-11/`: the analysis plan (fixed before the data
  were fetched, reproduced verbatim), the departures from it, the sampling,
  analysis and figure scripts, and the field- and group-level results behind
  the note on self-citation handling and credit sharing in the 2026 (version
  9) Stanford/Elsevier science-wide author databases. No scientist-level
  data; the README explains what is withheld and how to reproduce the run.
- Optional OpenAlex API key: `OPENALEX_API_KEY`, or `api_key=` in
  `OpenAlexClient`, `fetch_orcid_works`, `compute_profile`, `sample_authors`
  and `sample_authors_stratified`. The key is masked in log and error
  messages, connection errors and timeouts included, and the `-v` option no
  longer lets `urllib3` log request URLs.
- `Work.authors_capped` and `ResearcherResult.n_works_capped` (also in the
  JSON output, the batch table and the plain-text summary).
- Tests: `tests/test_openalex.py` (15 tests), `tests/test_selfcite.py` (9)
  and `tests/test_selfcite_parallel.py` (22); 94 tests in total.
- `.gitignore` rules that keep run data (names, OpenAlex ids, list values
  that identify scientists) out of the repository.

### Changed

- `User-Agent` is `dpac/1.1`.
- HTTP errors from OpenAlex carry OpenAlex's own message (for example, why
  a request was rejected) and never the request URL.
- `mailto` / `DPAC_MAILTO` are still passed on, but documented as ignored:
  OpenAlex replaced its polite pool with API keys in 2026.
- Demonstration notebook: an API-key cell replaces the polite-pool cell, and
  the §7 note on byline order and long author lists replaces the obsolete
  note on a middle-position approximation (byline positions have been exact
  since v1.0.0). Outputs are cleared, as at the v1.0.0 packaging pass.
- README and `tool_spec.md`: sections on the API key, long author lists,
  `selfcite` and the `analyses/` folder.
- Name-matching tests use fictional names and institutions.

### Fixed

- Page size 200 → 100 (`per_page`) in `dpac/openalex.py` and
  `dpac/sample.py`. 100 is the maximum of the 2026 OpenAlex API, which
  rejected 200 with HTTP 400 when tested on 12 October 2026; v1.0.0
  requested 200 in the ORCID queries and in the sampler used by the
  demonstration notebook.
- Author lists capped at 100 names. OpenAlex lists at most the first 100
  authors of a work and no longer returns `authors_count`. A work with a
  100-name list is now flagged, since its equal and harmonic shares are
  upper bounds; the true count is used when OpenAlex returns it; and works
  on which the focal author comes after the 100th name, which cannot be
  matched by ORCID, are counted in a warning instead of being skipped
  silently.
- Demonstration notebook: the contact cell looked up an environment
  variable named after an e-mail address instead of `DPAC_MAILTO`, so no
  contact address was used; two references to section 5 now point to
  section 6.
- Sampler paging: the number of pages follows the requested sample size
  (it was capped at ten pages).
- Batch table of the command-line tool: the new `n_works_capped` column
  comes last, after the per-scheme columns.

## [1.0.0] — 2026-05-23

*Concept DOI: `10.5281/zenodo.20359542`. Version DOI: `10.5281/zenodo.20359543`.*

The first archived, citable release of the package. Tagged in GitHub and
deposited to Zenodo for DOI assignment.

### Functionality

- Paper-level metrics: total citations, raw *h*-index.
- Author-level metrics under three contribution-share schemes:
  - `equal_share` — 1/*n* across the author list, byline-position-blind.
  - `harmonic_share` — Hodge & Greenberg (1981) / Hagen (2008, 2010);
    *c*<sub>k</sub> = (1/*k*) / *H*<sub>n</sub>, with *k* read from the
    index of the focal author's matching entry in OpenAlex's
    `authorships` array (which preserves the published byline order).
  - `declared_share` — passthrough for user-supplied declared shares;
    the proposal's target case, operationally identical to the proposed
    system once databases populate the field.
- Author-level *h*-index variants per scheme: fractional *h*-index in
  the Egghe (2008) sense on the share-weighted citation series.
- OpenAlex client with on-disk caching, polite-pool `mailto`, configurable
  throttle, and full work-list pagination via cursor.
- Stratified random sampling of OpenAlex authors by field-defining topic
  identifier and *h*-index band (`sample.py`), used to build the
  100-researcher ocean-engineering cohort reported in §5.2 of the
  preprint. The default configuration of `sample_authors_stratified`
  reproduces that cohort: five contiguous works_count bands spanning 5
  to 1000, 20 authors per band, *h*-index floor of 5.
- Command-line interface: single-ORCID summary, ORCID-list batch, JSON or
  tabular output, declared-shares CSV intake.

### Changed during the v1.0.0 pre-tag pass

- `sample_authors_stratified` defaults updated to match the preprint's
  100-researcher empirical cohort: `bands=[(5, 20), (21, 50), (51, 75),
  (76, 100), (101, 1000)]`, `per_band=20`, `min_h_index=5`. The bands
  are inclusive-inclusive `[lo, hi]` and contiguous: every integer
  works_count in the covered range lands in exactly one band. The
  previous wider-band, 4-per-band defaults are superseded.
- Demonstration notebook `demonstration.ipynb` realigned with the
  preprint. The synthetic continuous-time-trajectories section (former
  §6) and the mock-data trajectories subsection (former §7.3) were
  removed in line with the chat-9 project decision to drop synthetic
  trajectories from the preprint. The cohort-vs-archetypes section
  (former §7.4) is renumbered to §6.3 and its visualisation cell now
  renders the equal-share and harmonic-counting scatters side by side,
  mirroring Figure 1 of the preprint. Section numbers downstream of the
  deletions are renumbered accordingly (§7 → §6, §8 → §7, §9 → §8).
- `cumulative_trajectory` removed from `dpac.metrics`, and
  `ResearcherResult.trajectory` removed from `dpac.profile`. Neither
  function was covered by the test suite or re-exported at the `dpac`
  package level, and both are tied to the synthetic-trajectories
  framing that the chat-9 decision dropped from the preprint.
  Trajectory-related mentions in `README.md` and `tool_spec.md` are
  scrubbed in step.
- Pre-rendered cohort artefacts (`cohort_narrow_bands_100researchers_v02.csv`
  and `narrow_bands_100researchers_v02.png`) dropped from the repository.
  The demonstration notebook re-produces both on a default run, writing
  `cohort_ocean_engineering.csv` and `cohort_ocean_engineering.png` to
  the working directory; the `SAVE_OUTPUTS` flag at the top of the §6.3
  visualisation cell controls whether files are written (default True).
  This separates the package's shipped surface from the artefacts of any
  one cohort run.

### Notes on the development trajectory before v1.0.0

A pre-v1.0.0 development trajectory existed internally (drafted as v0.1
in the chat-7 design pass, with byline-order resolution added in the
chat-8 implementation and exercised in chat-9 against the ocean-
engineering cohort whose results are reported in §5.2 of the preprint).
That history is preserved here for traceability:

- *Pre-release design pass.* Paper-level and author-level metric
  primitives, equal-share scheme, harmonic scheme keyed on the
  categorical `author_position` field (`first`/`middle`/`last`),
  fractional *h*-index, OpenAlex client with caching, demonstration
  notebook. The categorical-only byline resolution approximated all
  middle ranks on a paper of *n* ≥ 3 authors by the centre of the
  {2, ..., *n* − 1} range, which conflated co-authors at substantively
  different byline positions.
- *Pre-release byline-order pass.* True byline-order resolution for
  harmonic counting: *k* read from the `authorships` array index rather
  than from the categorical `author_position` field, removing the
  middle-position approximation. Any harmonic-counting numbers obtained
  under the pre-release design pass are superseded by v1.0.0.

The 48-test unit suite covers all schemes (including the regression
case at *n* = 5, *k* ∈ {2, 3, 4} that the array-index resolution
distinguishes), paper- and author-level metric primitives, raw and
fractional *h*-index closed-form cases, and the byline-order resolution
path of `openalex._normalise_work`.
