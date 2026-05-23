"""Unit tests for `dpac.schemes` and the byline-order resolution path of
`dpac.openalex._normalise_work`.

The harmonic-counting tests pin down the closed-form shares for small
author counts and verify the elementary properties of the scheme:
shares sum to 1, the head-to-tail ratio matches the harmonic ratio, and
the focal author's share moves with byline position rather than only
with author count.

The byline-order tests exercise `_normalise_work` against synthetic raw
OpenAlex payloads with the focal ORCID placed at known positions and
confirm that `focal_position` equals the `authorships` array index plus
one, regardless of what the `author_position` categorical field carries.
"""

from __future__ import annotations

import math

import pytest

from dpac.openalex import Work, _normalise_work, _position_to_index
from dpac.schemes import (
    apply_scheme,
    declared_share,
    equal_share,
    harmonic_share,
)


# ---------------------------------------------------------------------------
# Small constructor helpers
# ---------------------------------------------------------------------------


def _work(n_authors: int, focal_position: int,
          cited_by_count: int = 0, work_id: str = "W1") -> Work:
    """Build a minimal Work record for scheme unit tests."""
    return Work(
        openalex_id=work_id,
        doi=None,
        title="(test)",
        publication_year=2024,
        cited_by_count=cited_by_count,
        n_authors=n_authors,
        focal_position=focal_position,
        focal_position_known=True,
    )


def _raw_work(focal_orcid: str, byline_orcids: list[str],
              positions: list[str], pub_year: int = 2024,
              work_id: str = "https://openalex.org/W1") -> dict:
    """Build a synthetic OpenAlex raw `Work` payload.

    `byline_orcids` is the published byline order (left to right).
    `positions` carries the categorical `author_position` value for each
    byline slot, and may be set independently of the array order so that
    the tests can verify the array-derived rank is used regardless.
    """
    assert len(byline_orcids) == len(positions)
    authorships = [
        {
            "author": {"orcid": f"https://orcid.org/{o}" if o else None},
            "author_position": pos,
        }
        for o, pos in zip(byline_orcids, positions)
    ]
    return {
        "id": work_id,
        "doi": None,
        "title": "(test)",
        "publication_year": pub_year,
        "cited_by_count": 0,
        "authorships": authorships,
        "primary_location": {"source": {"issn_l": None}},
    }


# ---------------------------------------------------------------------------
# equal_share — regression guard
# ---------------------------------------------------------------------------


def test_equal_share_is_one_over_n():
    """equal_share assigns 1/n irrespective of byline position."""
    for n in (1, 2, 3, 5, 10, 100):
        for k in range(1, n + 1):
            assert equal_share(_work(n, k)) == pytest.approx(1.0 / n)


def test_equal_share_zero_authors_returns_zero():
    """A defensive degenerate case: n_authors <= 0 returns 0.0."""
    assert equal_share(_work(0, 0)) == 0.0


# ---------------------------------------------------------------------------
# harmonic_share — byline-position-dependent share
# ---------------------------------------------------------------------------


def test_harmonic_share_single_author_returns_one():
    """A solo-authored paper assigns the full unit share to the author."""
    assert harmonic_share(_work(1, 1)) == pytest.approx(1.0)


def test_harmonic_share_two_authors_closed_form():
    """For n=2, H_2 = 1 + 1/2 = 3/2; shares are 2/3 and 1/3."""
    h2 = 1.0 + 0.5
    assert h2 == pytest.approx(1.5)
    assert harmonic_share(_work(2, 1)) == pytest.approx(2.0 / 3.0)
    assert harmonic_share(_work(2, 2)) == pytest.approx(1.0 / 3.0)
    # Sum to one.
    assert (
        harmonic_share(_work(2, 1)) + harmonic_share(_work(2, 2))
        == pytest.approx(1.0)
    )


def test_harmonic_share_five_authors_closed_form():
    """For n=5, H_5 = 137/60; shares are 60/137, 30/137, 20/137, 15/137, 12/137."""
    h5_num = 137.0
    h5_den = 60.0  # 60 * (1 + 1/2 + 1/3 + 1/4 + 1/5) = 60 + 30 + 20 + 15 + 12 = 137
    expected = [
        60.0 / h5_num,
        30.0 / h5_num,
        20.0 / h5_num,
        15.0 / h5_num,
        12.0 / h5_num,
    ]
    got = [harmonic_share(_work(5, k)) for k in range(1, 6)]
    for g, e in zip(got, expected):
        assert g == pytest.approx(e)
    # Sum to one.
    assert sum(got) == pytest.approx(1.0)
    # Head-to-tail ratio equals 5 (i.e. 60/12), matching the harmonic
    # weighting of first vs last on a 5-author paper.
    assert got[0] / got[-1] == pytest.approx(5.0)
    # Confirm H_5 explicitly.
    h5 = sum(1.0 / k for k in range(1, 6))
    assert h5 == pytest.approx(h5_num / h5_den)


def test_harmonic_share_ten_authors_numerical_stability():
    """For n=10, shares sum to 1 within float tolerance, and the
    head-to-tail ratio equals 10 (the harmonic head/tail weighting).

    This is the numerical-stability check on a moderate author count.
    """
    n = 10
    shares = [harmonic_share(_work(n, k)) for k in range(1, n + 1)]
    assert sum(shares) == pytest.approx(1.0, rel=1e-12, abs=1e-12)
    # All positive and strictly decreasing in k.
    for k in range(1, n):
        assert shares[k - 1] > shares[k] > 0.0
    # Head/tail ratio is exactly n.
    assert shares[0] / shares[-1] == pytest.approx(float(n))


def test_harmonic_share_focal_at_specific_middle_position():
    """A focal author at position k=3 on a 5-author paper receives the
    3rd harmonic share, which is strictly smaller than the 2nd and
    strictly greater than the 4th. This pins position-specific behaviour
    on the middle three ranks of a 5-author paper, where a categorical-
    only (`first`/`middle`/`last`) resolution would conflate them.
    """
    s2 = harmonic_share(_work(5, 2))
    s3 = harmonic_share(_work(5, 3))
    s4 = harmonic_share(_work(5, 4))
    assert s2 > s3 > s4 > 0.0
    # Pin exact value for k=3 on n=5: (1/3) / (137/60) = 60 / (3*137) = 20/137.
    assert s3 == pytest.approx(20.0 / 137.0)


def test_harmonic_share_out_of_range_returns_zero():
    """Defensive: shares for k <= 0 or k > n return 0.0 rather than raise."""
    assert harmonic_share(_work(5, 0)) == 0.0
    assert harmonic_share(_work(5, 6)) == 0.0
    assert harmonic_share(_work(0, 0)) == 0.0


# ---------------------------------------------------------------------------
# declared_share — passthrough behaviour
# ---------------------------------------------------------------------------


def test_declared_share_returns_value_when_present():
    w = _work(3, 2, work_id="W42")
    assert declared_share(w, {"W42": 0.4}) == pytest.approx(0.4)


def test_declared_share_returns_zero_when_absent():
    w = _work(3, 2, work_id="W42")
    assert declared_share(w, {"W99": 0.4}) == 0.0


# ---------------------------------------------------------------------------
# apply_scheme — dispatcher
# ---------------------------------------------------------------------------


def test_apply_scheme_equal_and_harmonic_lengths_match_input():
    works = [_work(2, 1), _work(3, 2), _work(5, 4)]
    eq = apply_scheme(works, "equal")
    hm = apply_scheme(works, "harmonic")
    assert len(eq) == len(works)
    assert len(hm) == len(works)


def test_apply_scheme_unknown_scheme_raises():
    with pytest.raises(ValueError):
        apply_scheme([_work(2, 1)], "geometric")


def test_apply_scheme_declared_requires_mapping():
    with pytest.raises(ValueError):
        apply_scheme([_work(2, 1)], "declared")


# ---------------------------------------------------------------------------
# _position_to_index and _normalise_work — byline-order resolution
# ---------------------------------------------------------------------------


def test_position_to_index_uses_array_index_for_first():
    """First-listed author -> rank 1, known True."""
    pos, known = _position_to_index("first", 0, 5)
    assert pos == 1 and known is True


def test_position_to_index_uses_array_index_for_last():
    """Last-listed author -> rank n, known True."""
    pos, known = _position_to_index("last", 4, 5)
    assert pos == 5 and known is True


def test_position_to_index_resolves_middle_to_exact_index():
    """A focal author at byline index 2 on a 5-author paper resolves to
    rank 3 — the exact array-derived index, not an approximation of the
    `middle` category.
    """
    pos, known = _position_to_index("middle", 2, 5)
    assert pos == 3 and known is True


def test_position_to_index_resolves_late_middle_to_exact_index():
    """A focal author at byline index 3 on a 5-author paper resolves to
    rank 4 — distinguishing it from index 2 (rank 3) on the same paper,
    which a `middle`-only categorical resolution would conflate with it.
    """
    pos, known = _position_to_index("middle", 3, 5)
    assert pos == 4 and known is True


def test_position_to_index_handles_categorical_disagreement():
    """If the categorical field disagrees with the array (e.g. position
    says 'first' but index is 2), the array-derived rank wins. The
    inconsistency is logged at DEBUG (not tested here) and `known`
    remains True.
    """
    pos, known = _position_to_index("first", 2, 5)
    assert pos == 3 and known is True


def test_normalise_work_focal_at_array_index_two():
    """End-to-end: focal ORCID is at array index 2 (byline rank 3) on a
    5-author paper; `_normalise_work` should set focal_position = 3.
    """
    focal = "0000-0001-2345-6789"
    others = [f"0000-0000-0000-{i:04d}" for i in range(4)]
    byline = [others[0], others[1], focal, others[2], others[3]]
    positions = ["first", "middle", "middle", "middle", "last"]
    raw = _raw_work(focal, byline, positions)
    work = _normalise_work(raw, focal)
    assert work is not None
    assert work.n_authors == 5
    assert work.focal_position == 3
    assert work.focal_position_known is True


def test_normalise_work_focal_at_first():
    focal = "0000-0001-2345-6789"
    byline = [focal, "0000-0000-0000-0001", "0000-0000-0000-0002"]
    positions = ["first", "middle", "last"]
    raw = _raw_work(focal, byline, positions)
    work = _normalise_work(raw, focal)
    assert work is not None
    assert work.focal_position == 1
    assert work.focal_position_known is True


def test_normalise_work_focal_at_last():
    focal = "0000-0001-2345-6789"
    byline = ["0000-0000-0000-0001", "0000-0000-0000-0002", focal]
    positions = ["first", "middle", "last"]
    raw = _raw_work(focal, byline, positions)
    work = _normalise_work(raw, focal)
    assert work is not None
    assert work.focal_position == 3
    assert work.focal_position_known is True


def test_normalise_work_returns_none_when_focal_orcid_absent():
    focal = "0000-0001-2345-6789"
    byline = ["0000-0000-0000-0001", "0000-0000-0000-0002"]
    positions = ["first", "last"]
    raw = _raw_work(focal, byline, positions)
    work = _normalise_work(raw, focal)
    assert work is None
