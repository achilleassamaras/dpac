# Departures from the analysis plan and implementation choices

The analysis plan ([`ANALYSIS_PLAN_2026-11.md`](ANALYSIS_PLAN_2026-11.md)) was
fixed on 12 October 2026, before the citation data were fetched, and the
analysis script was run once against it. Items 1–9 below are the departures
from the plan and the choices made where the plan is silent; they were logged
when the analysis was run, and the note states them or the run settings that
follow from them. Item 10 was found later, when the code was prepared for
release.

## Implementation choices where the plan is silent

1. **Inclusion step 2 (name match approved).** No lower-confidence name
   matches (`check`) were reviewed by hand, so an approved match is a
   high-confidence automatic match (`match_flag` = `high`). Sensitivity check
   E2, which keeps high-confidence matches only, is therefore identical to the
   primary analysis.
2. **H1 test.** One-sided paired bootstrap *p*-value: the share of resamples
   in which *D* (or *Q*) under the credit rule is not larger than under the
   list's self-citation rule. The same resampled researchers are used for
   every rule, and the *p*-values are Holm-corrected across the five fields.
   Bootstrap seeds are derived from 20261012 (20261012 plus the field index
   for the per-field intervals; fixed offsets for the other blocks, as set in
   `analyse_selfcite_2026-11.py`).
3. **Quintiles.** Researchers are ranked within the field with average ranks
   for ties, and quintile = ⌈5 × rank / *n*⌉, so tied researchers share a
   quintile.
4. **Pooled random reference group.** The pooled R group (*n* = 102) is
   ranked across fields, as the list ranks scientists across fields.
5. **H5 (fractional rules).** `frac_equal` and `frac_harmonic` are each
   compared with the list's rule (`excl_shared`), and `frac_network` with its
   binary counterpart (`excl_network`). A fractional rule gives weight 1 to
   every link without author overlap, so it can never keep less than its
   binary counterpart: H5 holds by construction. The Wilcoxon tests in
   `results.md` are therefore uninformative, and the note reports H5 as
   sizes (the share of *h* kept, and the share of researchers who keep more).

## Additions and presentation

6. **Whole-list addendum.** The share of the whole list's top 100,000 that
   changes under each switch (self-citations; co-authorship-aware composite)
   was added after the run ([`addendum_top100k_global.py`](addendum_top100k_global.py),
   [`addendum_top100k_global.md`](addendum_top100k_global.md)). It is
   descriptive and changes no pre-specified result.
7. **Figures and table of the note.** The note numbers the two figures in the
   opposite order from plan §6, so that the main result comes first: Figure 1
   shows the reordering and Figure 2 the citation sources. The note's Table 1
   is transposed (fields as columns), with rows added for *Q* and for the
   co-author share of self-citations.
8. **Changes from the pilot design.** The changes from the earlier pilot run
   listed in plan §7 are not repeated in the note, since the pilot is
   unpublished; the note states the run settings instead (citations from
   1996–2025; articles, reviews, books and book chapters; records above 80,000
   OpenAlex citations skipped).
9. **Figure legends.** The figure legends were relabelled after the run.
   [`make_note_figures.py`](make_note_figures.py) redraws the two figures
   from `results.json` and the run summary with the note's numbering; nothing
   was recomputed except the group means plotted in the note's Figure 2,
   which equal those in [`figure1_data.csv`](figure1_data.csv) (the run's
   numbering).

## Found after the run

10. **Capped citing papers and the truncation flag.** A review of the code
    for the v1.1.0 release found that `dpac.selfcite`, as run, flagged a
    citation link as touching an author list capped at 100 names when the
    cited paper's list was capped, but not when only the citing paper's list
    was: the check on the citing paper relied on the true author count,
    which OpenAlex no longer returned at the time of the run. The flag enters
    only sensitivity check E1 (researchers with more than 10% of such links
    left out; 12 in the run) and the descriptive share of such links; it
    enters no rule, measure or other result. Since a corrected flag can only
    raise each researcher's share, the 12 researchers left out in E1 are a
    lower bound. The module is corrected in v1.1.0 (with a test), so a
    re-run with v1.1.0 gives a different E1. The released `results.md` and
    `results.json` are those of the run as made. E1 was recomputed on
    13 October 2026 with v1.1.0 from the run's cache (no new OpenAlex
    requests; same scripts, seeds and settings): 13 researchers are left out
    instead of 12 (ENG 1, PHY 6, MED 6), only the E1 sections differ, and
    every H1–H4 conclusion holds. The recomputed files are in
    [`e1_recheck/`](e1_recheck/) (`results.md`, `results.json`); the note
    reports this E1.
