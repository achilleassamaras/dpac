"""
Unit tests for dpac.

These exercise the metric definitions on small, hand-computable inputs.
The OpenAlex client is not exercised here — it requires network access
and is best tested against the real API on the user's machine. Tests
operate on constructed Work records.
"""

from __future__ import annotations

import math

import pytest

from dpac import (
    apply_scheme,
    author_level_metrics,
    paper_level_metrics,
    raw_h_index,
    fractional_h_index,
    equal_share,
    harmonic_share,
    compute_profile,
)
from dpac.openalex import Work


# ----- helpers -----


def make_work(
    cited_by_count: int = 0,
    n_authors: int = 1,
    focal_position: int = 1,
    publication_year: int = 2020,
    openalex_id: str = "",
    focal_position_known: bool = True,
) -> Work:
    """Build a minimal Work record for tests."""
    return Work(
        openalex_id=openalex_id or f"W{id(object())}",
        doi=None,
        title="test",
        publication_year=publication_year,
        cited_by_count=cited_by_count,
        n_authors=n_authors,
        focal_position=focal_position,
        focal_position_known=focal_position_known,
    )


# ----- schemes -----


class TestEqualShare:
    def test_single_author(self):
        assert equal_share(make_work(n_authors=1, focal_position=1)) == 1.0

    def test_two_authors(self):
        assert equal_share(make_work(n_authors=2, focal_position=1)) == 0.5
        assert equal_share(make_work(n_authors=2, focal_position=2)) == 0.5

    def test_ten_authors(self):
        assert equal_share(make_work(n_authors=10, focal_position=5)) == 0.1


class TestHarmonicShare:
    def test_single_author(self):
        # H_1 = 1, c_1 = (1/1)/1 = 1
        assert harmonic_share(make_work(n_authors=1, focal_position=1)) == 1.0

    def test_two_authors_first(self):
        # H_2 = 1 + 0.5 = 1.5, c_1 = 1 / 1.5 = 2/3
        assert math.isclose(
            harmonic_share(make_work(n_authors=2, focal_position=1)),
            2.0 / 3.0,
        )

    def test_two_authors_last(self):
        # c_2 = 0.5 / 1.5 = 1/3
        assert math.isclose(
            harmonic_share(make_work(n_authors=2, focal_position=2)),
            1.0 / 3.0,
        )

    def test_three_authors_sum(self):
        # The shares of all three authors should sum to exactly 1.
        total = sum(
            harmonic_share(make_work(n_authors=3, focal_position=k))
            for k in (1, 2, 3)
        )
        assert math.isclose(total, 1.0)

    def test_last_author_decreases_with_n(self):
        # Last author's share shrinks as n grows.
        s2 = harmonic_share(make_work(n_authors=2, focal_position=2))
        s10 = harmonic_share(make_work(n_authors=10, focal_position=10))
        assert s2 > s10


class TestApplyScheme:
    def test_equal(self):
        works = [
            make_work(n_authors=2, focal_position=1),
            make_work(n_authors=4, focal_position=2),
        ]
        assert apply_scheme(works, "equal") == [0.5, 0.25]

    def test_unknown_scheme(self):
        with pytest.raises(ValueError, match="unknown scheme"):
            apply_scheme([], "wibble")

    def test_declared_requires_mapping(self):
        with pytest.raises(ValueError, match="declared"):
            apply_scheme([make_work()], "declared")

    def test_declared_passthrough(self):
        w = make_work(openalex_id="W123")
        out = apply_scheme([w], "declared", declared={"W123": 0.42})
        assert out == [0.42]

    def test_declared_partial_coverage(self):
        # An entry without a declared share returns 0.0.
        w1 = make_work(openalex_id="W123")
        w2 = make_work(openalex_id="W456")
        out = apply_scheme(
            [w1, w2], "declared", declared={"W123": 0.5}
        )
        assert out == [0.5, 0.0]


# ----- metrics -----


class TestRawHIndex:
    def test_empty(self):
        assert raw_h_index([]) == 0

    def test_simple(self):
        # rank 1: 10>=1, rank 2: 5>=2, rank 3: 4>=3, rank 4: 2<4 -> h=3
        assert raw_h_index([10, 5, 4, 2, 1]) == 3

    def test_all_equal(self):
        assert raw_h_index([3, 3, 3]) == 3

    def test_single_low(self):
        assert raw_h_index([0]) == 0


class TestFractionalHIndex:
    def test_empty(self):
        assert fractional_h_index([]) == (0.0, 0)

    def test_integer_case(self):
        # Series {10,5,4,2,1}: raw h=3, fractional h falls in (3,4)
        # h0=3, v_h0=4, v_next=2; line from (3,4) to (4,2) crosses y=x at
        # 4 - 2(x-3) = x -> 10 - 2x = x -> x = 10/3
        h_real, h_floor = fractional_h_index([10, 5, 4, 2, 1])
        assert math.isclose(h_real, 10.0 / 3.0)
        assert h_floor == 3

    def test_all_clear(self):
        # All three entries clear all ranks; h_real = n = 3
        assert fractional_h_index([3, 3, 3]) == (3.0, 3)

    def test_below_one(self):
        # Top entry below 1: h0=0, return top entry as fractional value
        h_real, h_floor = fractional_h_index([0.7])
        assert math.isclose(h_real, 0.7)
        assert h_floor == 0


class TestPaperLevelMetrics:
    def test_aggregates(self):
        works = [
            make_work(cited_by_count=10),
            make_work(cited_by_count=5),
            make_work(cited_by_count=4),
            make_work(cited_by_count=2),
        ]
        p = paper_level_metrics(works)
        assert p.n_papers == 4
        assert p.total_citations == 21
        assert p.raw_h_index == 3


class TestAuthorLevelMetrics:
    def test_equal_share_halves_citations(self):
        works = [
            make_work(cited_by_count=10, n_authors=2, focal_position=1),
            make_work(cited_by_count=5, n_authors=2, focal_position=2),
        ]
        shares = apply_scheme(works, "equal")
        a = author_level_metrics(works, shares, "equal")
        assert a.weighted_citations == 7.5
        assert a.effective_papers == 1.0

    def test_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="same length"):
            author_level_metrics([make_work()], [], "equal")


# ----- profile orchestration -----


class TestComputeProfile:
    def test_with_provided_works(self):
        # Sole-author and small-group mix
        works = [
            make_work(cited_by_count=20, n_authors=1, focal_position=1),
            make_work(cited_by_count=10, n_authors=3, focal_position=1),
            make_work(cited_by_count=6, n_authors=3, focal_position=2),
        ]
        r = compute_profile(works=works, schemes=["equal", "harmonic"])
        assert r.paper_level.n_papers == 3
        assert r.paper_level.total_citations == 36
        # Equal-share weighted citations: 20 + 10/3 + 6/3 = 25.333...
        assert math.isclose(
            r.author_level["equal"].weighted_citations, 20 + 10 / 3 + 6 / 3
        )
        assert set(r.shares) == {"equal", "harmonic"}

    def test_requires_input(self):
        with pytest.raises(ValueError, match="orcid"):
            compute_profile()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
