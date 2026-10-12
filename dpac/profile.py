"""
High-level orchestration: pull an ORCID's works, apply one or more schemes,
return a result container with side-by-side comparison.

This is the entry point most users will call. The lower-level building
blocks in `openalex`, `schemes`, and `metrics` are also exposed for users
who want finer control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .openalex import Work, fetch_orcid_works
from .schemes import apply_scheme
from .metrics import (
    paper_level_metrics,
    author_level_metrics,
    PaperLevelMetrics,
    AuthorLevelMetrics,
)


@dataclass
class ResearcherResult:
    """All computed quantities for a single researcher."""

    orcid: str
    works: list[Work]
    paper_level: PaperLevelMetrics
    author_level: dict[str, AuthorLevelMetrics]   # keyed by scheme name
    shares: dict[str, list[float]] = field(default_factory=dict)

    @property
    def n_works_capped(self) -> int:
        """Works whose author list OpenAlex cut at 100 names (true count unknown).

        Their equal and harmonic shares are approximate (upper bounds).
        """
        return sum(1 for w in self.works if getattr(w, "authors_capped", False))

    # ----- presentation -----

    def summary(self) -> str:
        """Return a multi-line, plain-text comparison table."""
        lines = []
        lines.append(f"Researcher: {self.orcid}")
        lines.append(f"Works analysed: {self.paper_level.n_papers}")
        lines.append("")
        header = (
            f"{'Metric':<32}"
            f"{'Paper-level':>14}"
        )
        for scheme in self.author_level:
            header += f"{'Author-' + scheme:>16}"
        lines.append(header)
        lines.append("-" * len(header))

        # Row: total citations
        row = (
            f"{'Total citations':<32}"
            f"{self.paper_level.total_citations:>14}"
        )
        for scheme, m in self.author_level.items():
            row += f"{m.weighted_citations:>16.1f}"
        lines.append(row)

        # Row: h-index (raw vs fractional)
        row = (
            f"{'h-index (raw / fractional)':<32}"
            f"{self.paper_level.raw_h_index:>14}"
        )
        for scheme, m in self.author_level.items():
            row += f"{m.fractional_h_index:>16.2f}"
        lines.append(row)

        # Row: effective paper count
        row = (
            f"{'Effective papers':<32}"
            f"{self.paper_level.n_papers:>14}"
        )
        for scheme, m in self.author_level.items():
            row += f"{m.effective_papers:>16.2f}"
        lines.append(row)

        if self.n_works_capped:
            lines.append("")
            lines.append(
                f"Note: {self.n_works_capped} works list 100 authors, the most "
                f"OpenAlex returns; their shares are approximate (upper bounds)."
            )

        return "\n".join(lines)

    def as_dict(self) -> dict:
        """Serialisable summary, for JSON output."""
        return {
            "orcid": self.orcid,
            "n_works": len(self.works),
            "n_works_capped": self.n_works_capped,
            "paper_level": {
                "n_papers": self.paper_level.n_papers,
                "total_citations": self.paper_level.total_citations,
                "raw_h_index": self.paper_level.raw_h_index,
            },
            "author_level": {
                scheme: {
                    "weighted_citations": m.weighted_citations,
                    "fractional_h_index": m.fractional_h_index,
                    "fractional_h_index_floor": m.fractional_h_index_floor,
                    "effective_papers": m.effective_papers,
                }
                for scheme, m in self.author_level.items()
            },
        }


# ----- public entry point -----


def compute_profile(
    orcid: Optional[str] = None,
    works: Optional[list[Work]] = None,
    schemes: list[str] = None,
    declared: Optional[dict] = None,
    mailto: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    use_cache: bool = True,
    work_types: Optional[list[str]] = None,
    api_key: Optional[str] = None,
) -> ResearcherResult:
    """Compute paper- and author-level metrics for one researcher.

    Either `orcid` or `works` must be supplied. When `orcid` is given, the
    works are fetched from OpenAlex (cached on disk by default). When
    `works` is given, the OpenAlex fetch is skipped.

    Pass `work_types=['article']` to restrict to journal articles when
    fetching from OpenAlex (no effect when `works` is supplied directly).

    `api_key` is the OpenAlex API key; when omitted, $OPENALEX_API_KEY is
    used if set.

    Returns a `ResearcherResult` container.
    """
    if works is None and orcid is None:
        raise ValueError("either `orcid` or `works` must be supplied")

    if schemes is None:
        schemes = ["equal", "harmonic"]

    if works is None:
        works = fetch_orcid_works(
            orcid, mailto=mailto, cache_dir=cache_dir,
            use_cache=use_cache, work_types=work_types, api_key=api_key,
        )

    p_level = paper_level_metrics(works)
    a_level: dict[str, AuthorLevelMetrics] = {}
    shares_by_scheme: dict[str, list[float]] = {}
    for scheme in schemes:
        shares = apply_scheme(works, scheme, declared=declared)
        a_level[scheme] = author_level_metrics(works, shares, scheme)
        shares_by_scheme[scheme] = shares

    return ResearcherResult(
        orcid=orcid or "(no ORCID)",
        works=works,
        paper_level=p_level,
        author_level=a_level,
        shares=shares_by_scheme,
    )
