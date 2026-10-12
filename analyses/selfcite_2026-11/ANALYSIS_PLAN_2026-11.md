> **Preface (added for the dpac v1.1.0 release).** The plan below is
> reproduced verbatim. It was written on 12 October 2026, before the OpenAlex
> citation data were fetched, and was not registered on a public registry.
> One change was made after the OpenAlex API probe of the same day, still
> before any citation data were fetched: §7, item 4 was reworded, because
> OpenAlex no longer returns the true author count (`authors_count`). The
> plan was then run once. Departures from it and choices it left open are
> listed in [`DEPARTURES.md`](DEPARTURES.md).
>
> The plan uses the numbering of the author's working sessions: *Chat 24*
> is the pilot run of 9–10 October 2026 (ocean engineering; unpublished),
> *Chat 26* is this run (sample drawn and citation data fetched), and
> *Chat 27* is the analysis, run once against this plan. `authors_log.md`
> is the author's project log, which is not part of this repository. The
> local paths in §8 refer to the author's machine; the public sources are
> given in [`README.md`](README.md).

---

# Analysis plan: self-citation decomposition across five fields (run 2026-11)

Written in Chat 26 (12 October 2026), before any Chat 26 data were fetched. It fixes what the Chat 27 note will compute and report. Any departure is logged in `authors_log.md` and stated in the note.

## 1. The message being tested

> How credit is shared among co-authors reorders researchers far more than how self-citations are handled. The 2026 list refines the second and leaves the first to a single indicator (hm). Declared contribution shares would address both.

Chat 24 found this in one field: ocean engineering, 100 researchers. Rank correlation was 0.99 under the list's self-citation rule, against 0.97 for equal-share credit and 0.94 for harmonic credit. The researchers who changed fifth were 12%, 24% and 34% respectively. Chat 26 tests whether the pattern holds in five fields that differ in team size and self-citation culture.

## 2. Data

**Level 1, the list itself.** v9 Table 1, career-long, all 243,949 entries, restricted to five fields:

| Field | Listed | Self-citation-only entrants | Median self-citation rate | Median hm/h |
|---|---|---|---|---|
| Engineering | 19,516 | 5.0% | 12.9% | 0.54 |
| Physics & Astronomy | 21,480 | 7.2% | 16.2% | 0.50 |
| Clinical Medicine | 74,888 | 2.8% | 10.8% | 0.39 |
| Mathematics & Statistics | 2,971 | 7.3% | 12.4% | 0.68 |
| Economics & Business | 4,838 | 2.9% | 4.6% | 0.59 |

**Level 2, OpenAlex.** The sample in `sample_2026-11.csv` has 40 scientists per field and group (600 rows); `random_reference_2026-11.csv` has 25 per field (125 rows). Seed 20261012. Groups:

- **S** *Self-citation-only entrants*: listed only through the two routes that count self-citations.
- **B** *High bundled citations*: citations per citing paper without self-citations at or above the subfield's 95th percentile.
- **C** *Comparison group*: self-citation rate between the subfield's 40th and 60th percentiles, and citations per citing paper at or below the subfield median.
- **R** *Random reference*: random draw from everyone eligible in the field.

Eligibility for all groups: 50–1,000 papers and at most 50,000 citations.

**Inclusion for analysis** (applied in this order, with counts reported for each):

1. `status` = ok.
2. Name match approved: `use` = Y.
3. OpenAlex coverage plausible: `all_cites` between 0.25 and 4 times the list's `nc9625`. Outside that range, the profile is probably wrong or split.
4. A cell with fewer than 20 included researchers is described but not tested.

## 3. Measures (all from `selfcite_summary.csv`)

| Measure | Columns |
|---|---|
| Citation sources | `share_own`, `share_coauthor`, `share_network`, `share_independent` |
| List-rule self-citation rate | `self_rate_list_rule` (own + co-author) |
| Co-author part of self-citations | `coauthor_share_of_self` |
| Bundling | `{all, excl_shared, excl_network}_cites_per_citing` |
| Self-citation rules | `all`, `excl_own`, `excl_shared` (list rule), `excl_network`, `frac_equal`, `frac_harmonic`, `frac_network`, each with `_cites`, `_h`, `_hm` |
| Credit sharing | `all_credit_equal`, `all_credit_harmonic`, `all_hm` |
| Team size | `median_team_size`, `n_works_over_100_authors`, `share_links_trunc` |
| List values for validation | `self_pct_list`, `cprat_ns_list`, `hm_h_list`, plus the passed-through Table 1 columns |

## 4. Analyses

### A. Validation (reported first; no exclusions follow from it)

- **V1.** Spearman correlation and median difference between `self_rate_list_rule` and `self_pct_list`/100, per field. Chat 24 gave ρ = 0.89 with a median difference of about one point.
- **V2.** Spearman correlation between `excl_shared_cites_per_citing` and `cprat_ns_list`, per field. Chat 24 gave ρ = 0.94.
- A field with ρ < 0.6 in V1 is flagged in the note as less reliable at Level 2.

### B. Headline: what reorders researchers (H1)

**Reordering** between two rankings of the same researchers is measured as:

- *D* = 1 − Spearman ρ;
- *Q*, the share of researchers who change quintile.

Quintiles are formed within the field. The baseline ranking is total citations (`all_cites`).

| Change of rule | Compared rankings |
|---|---|
| Self-citations, list rule | `all_cites` → `excl_shared_cites` |
| Self-citations, also excluding the network | `all_cites` → `excl_network_cites` |
| Self-citations, fractional overlap | `all_cites` → `frac_equal_cites` |
| Credit, equal shares | `all_cites` → `all_credit_equal` |
| Credit, harmonic shares | `all_cites` → `all_credit_harmonic` |
| h family: self-citations vs credit | `all_h` → `excl_shared_h`, against `all_h` → `all_hm` |

**H1:** *D*(equal credit) / *D*(list rule) > 1 in every field. The same holds for harmonic credit and for *Q*.

1. **Primary:** each field's full Level-2 set (S + B + C + R, about 120 researchers). S and B are over-represented, which inflates the self-citation effect, so this is a conservative test of H1.
2. **Secondary:** the R group alone, per field and pooled. R is representative but small, so its intervals will be wide.
3. **Level 1 analogue,** using all listed scientists in each field:
   - self-citation handling: *D* and *Q* between `c` and `c (ns)`;
   - credit sharing: *D* and *Q* between `c (ns)` and the co-authorship-aware composite (hm, single, single+first and single+first+last, each log-normalised with Table 3, without self-citations);
   - in addition, the share of each field's top 100,000 entrants who change under each switch.

### C. Where self-citations come from (H2–H4)

- **H2 (team size).** The co-author share of self-citations rises with team size.
  - Test: Spearman correlation between `coauthor_share_of_self` and `median_team_size`, within each field and pooled.
  - Expected order of field medians, from highest: Clinical Medicine > Physics > Engineering > Economics, Mathematics.
- **H3 (bundling and the network).**
  - `share_network` is higher in B than in C (one-sided Mann–Whitney, per field). Chat 24: 12.4% against 4.7%.
  - `share_network` correlates positively with `cprat_ns_list`. Chat 24: ρ = 0.64.
  - Reported quantity: the part of B's excess bundling that the network removes, (`excl_shared_cpc` − `excl_network_cpc`) / (`excl_shared_cpc` − 1). Chat 24: about a quarter.
- **H4 (own self-citation).** `share_own` is higher in S than in C (one-sided Mann–Whitney, per field). Chat 24: 12.0% against 6.4%.

### D. Fractional rule (H5, descriptive)

- Report the median *h* kept, relative to `all_h`, under each rule per field.
- **H5:** the fractional rules keep more of *h* than the list rule (paired Wilcoxon per field). This is the evidence that share-based weighting is less blunt than all-or-nothing exclusion.

### E. Sensitivity (reported in a footnote or supplement)

1. H1–H4 repeated without researchers whose `share_links_trunc` exceeds 0.10. This mainly affects Physics and Clinical Medicine, where some citing or cited papers list more than 100 authors.
2. H1–H4 repeated with high-confidence matches only, dropping hand-approved `check` rows.
3. The number skipped as above 80,000 OpenAlex citations, per cell.

## 5. Statistics

- **Effect sizes:**
  - medians, with bootstrap 95% intervals (2,000 resamples of researchers within field, seed 20261012, percentile method);
  - Cliff's δ for group contrasts;
  - the ratio *D*(credit)/*D*(self) with its bootstrap interval.
- **Tests:** Mann–Whitney (groups), Wilcoxon signed-rank (paired rules) and Spearman (associations).
- **Multiple testing:** Holm correction within each hypothesis across the five fields, α = 0.05.
- **Reporting rule:** every pre-specified result is reported, including any field where a hypothesis fails. If H1 fails in a field, the note says "in k of five fields" rather than dropping the field.

## 6. What goes into the note (two figures, one table)

- **Figure 1. Where self-citations come from.**
  - One panel per field.
  - For S, B, C and R, the mean share of citation links that are own, co-author or collaborator-network (independent is the remainder).
- **Figure 2. What reorders researchers.**
  - One row per field.
  - *D*, with a 95% interval, for the three self-citation rules and the two credit-sharing rules (filled markers, Level 2).
  - The Level 1 list analogue as hollow markers.
  - This figure carries the message.
- **Table 1.** Per field:
  - listed scientists and the self-citation-only entrant share (Level 1);
  - researchers included (Level 2);
  - median team size;
  - median own, co-author and network shares;
  - median *h* kept under the list rule and under the fractional rule;
  - V1 ρ.

The note does not contain individual researchers, names or labels that could be traced, or country breakdowns at Level 2, where the sample is too small for them.

## 7. Changes from the Chat 24 design (to be stated in the methods)

1. Five fields instead of three engineering and ocean subfields.
2. C percentiles are taken within each primary subfield. Chat 24 pooled three subfields with near-identical distributions.
3. New random reference group R.
4. OpenAlex lists at most 100 authors per paper. Where OpenAlex returns `authors_count`, team size, equal shares, hm and harmonic credit use the true author count. Where it does not, lists of 100 names are flagged as capped. Either way, the links affected are flagged and analysed in sensitivity check E1.
5. `cites:` batches of 100 work ids instead of 50, with automatic splitting if OpenAlex refuses a batch.
6. Run settings:
   - citations from 1996–2025;
   - work types article, review, book chapter and book;
   - records above 80,000 OpenAlex citations skipped;
   - four researchers fetched in parallel.

## 8. Inputs Chat 27 needs

- `selfcite_summary.csv`, `selfcite_groups.csv`, `selfcite_shares.png` and `sample_2026-11_design.csv` from the run folder.
- v9 Table 1 and Table 3 (career) for Level 1, read directly from `E:\CIVIL_ENGINEERING\PAPERS_JOURNALS\ARTICLE_PERCENTAGE_BASED\stanford_top2_list_2026`.
- The analysis script is written in Chat 27 against this plan. It is run once; its output is the basis of the note.
