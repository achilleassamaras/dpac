"""
Unit tests for dpac.selfcite on a small, hand-computed record.

Focal author A has four works:

    P1 (2010) [A, B]     P2 (2012) [C, A]     P3 (2015) [A]     P4 (2018) [A, D, E]

and is cited by six works (years in brackets):

    Q1 (2016) [A, X]     -> P1, P3     own, own
    Q2 (2016) [B, Y]     -> P1, P2     coauthor (B on P1), network (B before 2016)
    Q3 (2014) [D, Z]     -> P1         independent (D joins A only in 2018)
    Q4 (2020) [Z, W]     -> P2, P3, P4 independent x3
    Q5 (2020) [C, Z]     -> P2, P4     coauthor (C on P2), network (C since 2012)
    Q6 (2021) [?, Z]     -> P3         independent (one author without an id)

No network access is used.
"""

from __future__ import annotations

import math

import pytest

from dpac.selfcite import (
    analyse_author,
    author_metrics,
    classify_links,
    hm_index,
    score_candidate,
)

WORKS = [
    {"id": "P1", "year": 2010, "type": "article", "cbc": 3, "authors": ["A", "B"]},
    {"id": "P2", "year": 2012, "type": "article", "cbc": 3, "authors": ["C", "A"]},
    {"id": "P3", "year": 2015, "type": "article", "cbc": 3, "authors": ["A"]},
    {"id": "P4", "year": 2018, "type": "article", "cbc": 2, "authors": ["A", "D", "E"]},
]
CITING = [
    {"id": "Q1", "year": 2016, "authors": ["A", "X"], "refs": ["P1", "P3"]},
    {"id": "Q2", "year": 2016, "authors": ["B", "Y"], "refs": ["P1", "P2"]},
    {"id": "Q3", "year": 2014, "authors": ["D", "Z"], "refs": ["P1"]},
    {"id": "Q4", "year": 2020, "authors": ["Z", "W"], "refs": ["P2", "P3", "P4"]},
    {"id": "Q5", "year": 2020, "authors": ["C", "Z"], "refs": ["P2", "P4"]},
    {"id": "Q6", "year": 2021, "authors": [None, "Z"], "refs": ["P3"]},
    {"id": "Q4", "year": 2020, "authors": ["Z", "W"], "refs": ["P4"]},   # duplicate pair
]


def _cls(links):
    return {(l["citing"], l["cited"]): l["cls"] for l in links}


def test_classification():
    links = classify_links("A", WORKS, CITING)
    assert len(links) == 11
    c = _cls(links)
    assert c[("Q1", "P1")] == c[("Q1", "P3")] == "own"
    assert c[("Q2", "P1")] == "coauthor"
    assert c[("Q2", "P2")] == "network"
    assert c[("Q3", "P1")] == "independent"
    assert c[("Q5", "P2")] == "coauthor"
    assert c[("Q5", "P4")] == "network"
    assert all(c[("Q4", p)] == "independent" for p in ("P2", "P3", "P4"))
    assert c[("Q6", "P3")] == "independent"
    any_only = [(l["citing"], l["cited"]) for l in links if l["network_any_only"]]
    assert any_only == [("Q3", "P1")]


def test_fractional_weights():
    w = {(l["citing"], l["cited"]): l for l in classify_links("A", WORKS, CITING)}
    l = w[("Q1", "P1")]
    assert l["w_equal"] == pytest.approx(0.5)
    assert l["w_harmonic"] == pytest.approx(1 - (1 / 1.5))
    assert l["w_network"] == pytest.approx(0.5)
    l = w[("Q2", "P2")]                      # no overlap with P2, but B is a prior collaborator
    assert (l["w_equal"], l["w_harmonic"], l["w_network"]) == pytest.approx((1.0, 1.0, 0.5))
    l = w[("Q3", "P1")]                      # D not yet a collaborator in 2014
    assert l["w_network"] == pytest.approx(1.0)
    l = w[("Q6", "P3")]
    assert (l["w_equal"], l["w_network"]) == pytest.approx((1.0, 1.0))


def test_hm_index():
    # Schreiber's effective rank: 0.5, 1.0, 2.0, then 2.33 > 2 citations.
    assert hm_index([(3, 2), (3, 2), (3, 1), (2, 3)]) == pytest.approx(2.0)
    assert hm_index([]) == 0.0
    assert hm_index([(10, 1), (10, 1), (1, 1)]) == pytest.approx(2.0)


def test_author_metrics():
    links = classify_links("A", WORKS, CITING)
    m = author_metrics("A", WORKS, links)
    assert (m["n_own"], m["n_coauthor"], m["n_network"], m["n_independent"]) == (2, 2, 2, 5)
    assert m["self_rate_list_rule"] == pytest.approx(4 / 11)
    assert m["coauthor_share_of_self"] == pytest.approx(0.5)
    assert m["n_network_any_only"] == 1
    assert (m["all_cites"], m["all_h"]) == (11, 3)
    assert m["all_hm"] == pytest.approx(2.0)
    assert (m["excl_own_cites"], m["excl_own_h"]) == (9, 2)
    assert (m["excl_shared_cites"], m["excl_shared_h"]) == (7, 2)
    assert (m["excl_network_cites"], m["excl_network_h"]) == (5, 1)
    assert m["frac_equal_cites"] == pytest.approx(9.0)
    assert m["frac_harmonic_cites"] == pytest.approx(25 / 3)
    assert m["frac_network_cites"] == pytest.approx(8.0)
    assert m["all_cites_per_citing"] == pytest.approx(11 / 6)
    assert m["excl_shared_cites_per_citing"] == pytest.approx(7 / 5)
    assert m["excl_network_cites_per_citing"] == pytest.approx(5 / 3)
    assert m["all_credit_equal"] == pytest.approx(1.5 + 1.5 + 3 + 2 / 3)
    h3 = 1 + 1 / 2 + 1 / 3
    assert m["all_credit_harmonic"] == pytest.approx(3 / 1.5 + 3 * 0.5 / 1.5 + 3 + 2 / h3)


class FakeSource:
    """Serves WORKS and CITING the way OpenAlexSource does, batch by batch."""

    def __init__(self, works, citing):
        self.works, self.citing, self.calls = works, citing, []

    def author_works(self, aid, work_types):
        return self.works

    def citing_works(self, batch, years):
        self.calls.append(tuple(batch))
        out = []
        for q in self.citing:
            refs = [r for r in q["refs"] if r in batch]
            if refs and years[0] <= q["year"] <= years[1]:
                out.append({**q, "refs": refs})
        return out


def test_pipeline_batches_and_years():
    src = FakeSource(WORKS, CITING)
    m, links = analyse_author(src, "https://openalex.org/A", None, (1996, 2025), 10_000, batch_size=2)
    assert src.calls == [("P1", "P2"), ("P3", "P4")]
    assert m["status"] == "ok" and m["n_links"] == 11
    m2, _ = analyse_author(FakeSource(WORKS, CITING), "A", None, (2015, 2025), 10_000, batch_size=2)
    assert m2["n_links"] == 10                       # Q3 (2014) drops out


def test_pipeline_skips_large_records():
    m, links = analyse_author(FakeSource(WORKS, CITING), "A", None, (1996, 2025), max_citations=5)
    assert m["status"].startswith("skipped") and links == []


def test_name_scoring():
    # Fictional names and institutions.
    good = {"display_name": "Alex B. Testauthor", "works_count": 120, "cited_by_count": 2500,
            "last_known_institutions": [{"display_name": "Northfield University of Technology"}]}
    other = {"display_name": "Chris Testauthor", "works_count": 40, "cited_by_count": 300,
             "last_known_institutions": [{"display_name": "Southfield University"}]}
    s_good = score_candidate(good, "Testauthor", "Alex B.", "Northfield University of Technology", 110, 2000)
    s_other = score_candidate(other, "Testauthor", "Alex B.", "Northfield University of Technology", 110, 2000)
    assert s_good >= 6.5 and s_good - s_other >= 1.5
    assert score_candidate({"display_name": "Pat Example"}, "Testauthor", "A.", "", 0, 0) == 0.0


class _Resp:
    def __init__(self, status, payload, headers=None):
        self.status_code, self._p, self.headers = status, payload, headers or {}

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


def test_openalex_source_parsing_paging_cache_and_retry(tmp_path, monkeypatch):
    from dpac import selfcite

    monkeypatch.setattr(selfcite.time, "sleep", lambda s: None)
    page1 = {"meta": {"next_cursor": "abc"}, "results": [
        {"id": "https://openalex.org/W1", "publication_year": 2020, "type": "article", "cited_by_count": 4,
         "authorships": [{"author": {"id": "https://openalex.org/A9"}}, {"author": {"id": None}}]}]}
    page2 = {"meta": {"next_cursor": None}, "results": [
        {"id": "https://openalex.org/W2", "publication_year": 2021, "type": "review", "cited_by_count": 0,
         "authorships": [{"author": {"id": "https://openalex.org/A9"}}]}]}
    citing = {"meta": {"next_cursor": None}, "results": [
        {"id": "https://openalex.org/W7", "publication_year": 2022,
         "authorships": [{"author": {"id": "https://openalex.org/A5"}}],
         "referenced_works": ["https://openalex.org/W1", "https://openalex.org/W99"]}]}
    calls = []
    script = [_Resp(429, {}), _Resp(200, page1), _Resp(200, page2), _Resp(200, citing)]

    def fake_get(url, params=None, timeout=None):
        calls.append((url, dict(params)))
        return script.pop(0)

    src = selfcite.OpenAlexSource(mailto="x@example.org", cache_dir=tmp_path)
    monkeypatch.setattr(src._session, "get", fake_get)
    works = src.author_works("https://openalex.org/A9", ["article", "review"])
    assert [w["id"] for w in works] == ["W1", "W2"]
    assert works[0]["authors"] == ["A9", None] and works[0]["cbc"] == 4
    assert calls[0][1]["filter"] == "author.id:A9,type:article|review" and calls[0][1]["mailto"] == "x@example.org"
    assert calls[2][1]["cursor"] == "abc"
    cw = src.citing_works(["W1"], (1996, 2025))
    assert cw == [{"id": "W7", "year": 2022, "authors": ["A5"], "refs": ["W1"]}]
    assert calls[3][1]["filter"] == "cites:W1,publication_year:1996-2025"
    n = len(calls)
    assert src.author_works("A9", ["review", "article"]) == works      # served from cache
    assert len(calls) == n


def test_daily_quota_stops_instead_of_retrying(tmp_path, monkeypatch):
    from dpac import selfcite

    sleeps = []
    monkeypatch.setattr(selfcite.time, "sleep", lambda s: sleeps.append(s))
    src = selfcite.OpenAlexSource(cache_dir=tmp_path)
    monkeypatch.setattr(src._session, "get", lambda url, params=None, timeout=None: _Resp(
        429, {"error": "Rate limited", "message": "Daily budget exceeded"}, {"X-RateLimit-Remaining": "0"}))
    with pytest.raises(selfcite.QuotaExceeded):
        src.author_works("A1", None)
    assert [s for s in sleeps if s >= 1] == []          # no back-off loop on a daily limit
