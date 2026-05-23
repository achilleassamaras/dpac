# Changelog

All notable changes to `dpac` are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-23

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
