"""
Paper-level and author-level metric computations.

Definitions follow §3.1 of the preprint:

    For a paper p with n co-authors, the co-authors declare contribution
    shares c_i,p summing to 1. For any paper-level metric m_p, the
    author-level analogue for contributor i is M_i,p = c_i,p * m_p.
    Aggregated across a record, M_i = sum_p c_i,p * m_p.

Two `h`-index variants are implemented:

- raw_h_index, the standard Hirsch (2005) integer index on the unweighted
  citation series.
- fractional_h_index, the Egghe (2008) extension to fractional counting:
  the citation series is replaced by the share-weighted series, sorted in
  descending order, and h is the largest real value such that the h-th
  sorted weighted value is at least h. A non-integer index is returned
  along with its integer floor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .openalex import Work


@dataclass
class PaperLevelMetrics:
    """Paper-level aggregates for a researcher's record."""

    n_papers: int
    total_citations: int
    raw_h_index: int


@dataclass
class AuthorLevelMetrics:
    """Author-level aggregates under a chosen share scheme."""

    scheme: str
    weighted_citations: float
    fractional_h_index: float
    fractional_h_index_floor: int
    effective_papers: float          # sum of shares — a `fractional paper count`


def paper_level_metrics(works: Iterable[Work]) -> PaperLevelMetrics:
    """Compute paper-level aggregates for a record."""
    works_list = list(works)
    cites = [w.cited_by_count for w in works_list]
    return PaperLevelMetrics(
        n_papers=len(works_list),
        total_citations=sum(cites),
        raw_h_index=raw_h_index(cites),
    )


def author_level_metrics(
    works: Iterable[Work],
    shares: Iterable[float],
    scheme_name: str,
) -> AuthorLevelMetrics:
    """Compute author-level aggregates under a given share series."""
    works_list = list(works)
    shares_list = list(shares)
    if len(works_list) != len(shares_list):
        raise ValueError(
            "works and shares must be the same length "
            f"(got {len(works_list)} works, {len(shares_list)} shares)"
        )

    weighted = [
        s * w.cited_by_count for s, w in zip(shares_list, works_list)
    ]
    f_h, f_h_floor = fractional_h_index(weighted)
    return AuthorLevelMetrics(
        scheme=scheme_name,
        weighted_citations=sum(weighted),
        fractional_h_index=f_h,
        fractional_h_index_floor=f_h_floor,
        effective_papers=sum(shares_list),
    )


def raw_h_index(citations: Iterable[float]) -> int:
    """Standard Hirsch (2005) h-index on a (possibly weighted) citation list.

    The largest integer h such that at least h items in the list have value
    at least h. Used with integer citation counts to produce the canonical
    h-index, and reused internally on weighted series as a sanity reference.
    """
    sorted_c = sorted(citations, reverse=True)
    h = 0
    for rank, value in enumerate(sorted_c, start=1):
        if value >= rank:
            h = rank
        else:
            break
    return h


def fractional_h_index(weighted_citations: Iterable[float]) -> tuple[float, int]:
    """Egghe (2008) fractional h-index on a share-weighted citation series.

    The weighted citations are sorted in descending order. The fractional
    h-index is defined as the real value h such that the h-th sorted entry,
    interpolated linearly between rank positions, equals h. Equivalently,
    the largest real h with weighted[ceil(h)] >= h.

    The function returns (h_real, h_floor) where h_real is the real-valued
    index and h_floor = floor(h_real). When the series is empty the return
    value is (0.0, 0).
    """
    sorted_c = sorted(weighted_citations, reverse=True)
    n = len(sorted_c)
    if n == 0:
        return 0.0, 0

    # Find the integer h0 such that sorted_c[h0-1] >= h0 and
    # sorted_c[h0] < h0+1 (with sorted_c indexed 0-based).
    h0 = 0
    for rank in range(1, n + 1):
        if sorted_c[rank - 1] >= rank:
            h0 = rank
        else:
            break

    # The fractional refinement: between rank h0 (value v_h0 >= h0) and
    # rank h0+1 (value v_next < h0+1, or absent), linearly interpolate to
    # find the real h where the linear segment from (h0, v_h0) to
    # (h0+1, v_next) crosses the line y = x.
    if h0 == 0:
        # No paper meets rank=1; the curve starts below the y=x line.
        # Fractional index is the value of the top entry (in [0, 1)).
        return float(sorted_c[0]), 0
    if h0 == n:
        # All n entries clear the bar; the index is at least n.
        return float(h0), h0

    v_h0 = sorted_c[h0 - 1]
    v_next = sorted_c[h0]
    # Linear segment: y(x) = v_h0 + (v_next - v_h0) * (x - h0), x in [h0, h0+1]
    # Solve y(x) = x: v_h0 + (v_next - v_h0) * (x - h0) = x
    # => x (1 - (v_next - v_h0)) = v_h0 - (v_next - v_h0) * h0
    # => x = (v_h0 - (v_next - v_h0) * h0) / (1 - (v_next - v_h0))
    slope = v_next - v_h0
    denom = 1.0 - slope
    if abs(denom) < 1e-12:
        return float(h0), h0
    h_real = (v_h0 - slope * h0) / denom
    # Clamp to [h0, h0+1] to absorb any numerical wobble.
    h_real = max(float(h0), min(float(h0) + 1.0, h_real))
    return h_real, h0
