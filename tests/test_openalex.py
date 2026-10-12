"""Unit tests for the OpenAlex access layer of the core package (v1.1).

Covers the changes made for the 2026 OpenAlex API: page size 100
(`per_page`), the optional API key (sent as `api_key`, never printed),
author lists capped at 100 names, and the package User-Agent. No network
access: `requests.get` is replaced by a recording fake.
"""

from __future__ import annotations

import logging

import pytest
import requests

import dpac
from dpac import compute_profile
from dpac.openalex import (
    AUTHORSHIP_CAP,
    DEFAULT_PER_PAGE,
    DEFAULT_USER_AGENT,
    OpenAlexClient,
    _normalise_work,
    fetch_orcid_works,
    redact_api_key,
)
from dpac.sample import sample_authors_stratified
from dpac.schemes import equal_share, harmonic_share

FOCAL = "0000-0000-0000-0042"           # placeholder ORCID
KEY = "test-key-123"


class _Resp:
    def __init__(self, status=200, payload=None, url="https://api.openalex.org/works"):
        self.status_code = status
        self._payload = payload if payload is not None else {}
        self.url = url
        self.text = ""

    def json(self):
        return self._payload


class _Recorder:
    """Stands in for requests.get; returns queued responses and records calls."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": dict(params or {}), "headers": dict(headers or {})})
        return self.responses.pop(0)


def _authorship(orcid=None, aid="A0"):
    return {"author": {"id": f"https://openalex.org/{aid}", "orcid": f"https://orcid.org/{orcid}" if orcid else None},
            "author_position": "middle"}


def _raw(n_listed, focal_at=None, authors_count=None, wid="W1", year=2020, cites=10):
    auths = [_authorship(None, f"A{i}") for i in range(n_listed)]
    if focal_at is not None:
        auths[focal_at] = _authorship(FOCAL, "AF")
    rec = {"id": f"https://openalex.org/{wid}", "doi": None, "title": "t", "publication_year": year,
           "cited_by_count": cites, "authorships": auths}
    if authors_count is not None:
        rec["authors_count"] = authors_count
    return rec


@pytest.fixture(autouse=True)
def _no_env_key(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    monkeypatch.delenv("DPAC_MAILTO", raising=False)


# ---------------------------------------------------------------------------
# Page size, API key, User-Agent
# ---------------------------------------------------------------------------


def test_page_size_is_100_and_cursor_paging(tmp_path, monkeypatch):
    rec = _Recorder([
        _Resp(payload={"results": [_raw(3, 0, wid="W1")], "meta": {"next_cursor": "c2"}}),
        _Resp(payload={"results": [_raw(3, 1, wid="W2")], "meta": {"next_cursor": None}}),
    ])
    monkeypatch.setattr(requests, "get", rec)
    out = OpenAlexClient(cache_dir=tmp_path).fetch_works_by_orcid(FOCAL, use_cache=False)
    assert len(out) == 2 and len(rec.calls) == 2
    for c in rec.calls:
        assert c["params"]["per_page"] == DEFAULT_PER_PAGE == 100
        assert "per-page" not in c["params"]
        assert c["headers"]["User-Agent"] == DEFAULT_USER_AGENT
    assert rec.calls[1]["params"]["cursor"] == "c2"
    assert DEFAULT_USER_AGENT.startswith("dpac/1.1 ")


def test_api_key_sent_only_when_set(tmp_path, monkeypatch):
    rec = _Recorder([_Resp(payload={"results": [], "meta": {}})] * 3)
    monkeypatch.setattr(requests, "get", rec)
    OpenAlexClient(cache_dir=tmp_path).fetch_works_by_orcid(FOCAL, use_cache=False)
    assert "api_key" not in rec.calls[-1]["params"]
    OpenAlexClient(cache_dir=tmp_path, api_key=KEY).fetch_works_by_orcid(FOCAL, use_cache=False)
    assert rec.calls[-1]["params"]["api_key"] == KEY
    monkeypatch.setenv("OPENALEX_API_KEY", "from-env")
    OpenAlexClient(cache_dir=tmp_path).fetch_works_by_orcid(FOCAL, use_cache=False)
    assert rec.calls[-1]["params"]["api_key"] == "from-env"


def test_http_error_carries_openalex_message_without_key(tmp_path, monkeypatch):
    bad = _Resp(400, {"error": "Invalid query parameters", "message": "per_page must be between 1 and 100"},
                url=f"https://api.openalex.org/works?per_page=200&api_key={KEY}")
    monkeypatch.setattr(requests, "get", _Recorder([bad]))
    with pytest.raises(requests.HTTPError) as ei:
        OpenAlexClient(cache_dir=tmp_path, api_key=KEY).fetch_works_by_orcid(FOCAL, use_cache=False)
    msg = str(ei.value)
    assert "HTTP 400 on /works" in msg and "per_page must be between 1 and 100" in msg
    assert KEY not in msg


def test_debug_log_masks_key(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(requests, "get", _Recorder([_Resp(payload={"results": [], "meta": {}})]))
    with caplog.at_level(logging.DEBUG, logger="dpac.openalex"):
        OpenAlexClient(cache_dir=tmp_path, api_key=KEY).fetch_works_by_orcid(FOCAL, use_cache=False)
    assert caplog.records and KEY not in caplog.text and "***" in caplog.text


def test_redact_api_key():
    assert redact_api_key(f"https://x/works?a=1&api_key={KEY}&b=2") == "https://x/works?a=1&api_key=***&b=2"
    assert redact_api_key("no key here") == "no key here"


# ---------------------------------------------------------------------------
# Author lists capped at 100 names
# ---------------------------------------------------------------------------


def test_short_list_is_not_capped():
    w = _normalise_work(_raw(5, 2), FOCAL)
    assert w.n_authors == 5 and w.focal_position == 3 and w.authors_capped is False


def test_list_of_100_without_count_is_flagged():
    w = _normalise_work(_raw(AUTHORSHIP_CAP, 9), FOCAL)
    assert w.n_authors == 100 and w.authors_capped is True
    assert equal_share(w) == pytest.approx(1 / 100)          # an upper bound for the true share


def test_true_count_used_when_returned():
    w = _normalise_work(_raw(AUTHORSHIP_CAP, 0, authors_count=250), FOCAL)
    assert w.n_authors == 250 and w.authors_capped is False
    assert equal_share(w) == pytest.approx(1 / 250)
    h250 = sum(1 / j for j in range(1, 251))
    assert harmonic_share(w) == pytest.approx(1 / h250)
    w = _normalise_work(_raw(AUTHORSHIP_CAP, 0, authors_count=100), FOCAL)
    assert w.n_authors == 100 and w.authors_capped is False   # exactly 100 authors, list complete


def test_focal_beyond_cap_is_skipped_and_counted(tmp_path, monkeypatch, caplog):
    raws = [_raw(3, 0, wid="W1"), _raw(AUTHORSHIP_CAP, 50, wid="W2"), _raw(AUTHORSHIP_CAP, None, wid="W3")]
    monkeypatch.setattr(requests, "get", _Recorder([_Resp(payload={"results": raws, "meta": {}})]))
    with caplog.at_level(logging.WARNING, logger="dpac.openalex"):
        works = fetch_orcid_works(FOCAL, cache_dir=tmp_path, use_cache=False)
    assert [w.openalex_id.rsplit("/", 1)[-1] for w in works] == ["W1", "W2"]
    assert [w.authors_capped for w in works] == [False, True]
    assert "1 of 2 works list 100 authors" in caplog.text
    assert "1 works skipped" in caplog.text


def test_profile_reports_capped_works():
    works = [_normalise_work(_raw(3, 0, wid="W1", cites=5), FOCAL),
             _normalise_work(_raw(AUTHORSHIP_CAP, 4, wid="W2", cites=50), FOCAL)]
    r = compute_profile(orcid=FOCAL, works=works)
    assert r.n_works_capped == 1
    assert r.as_dict()["n_works_capped"] == 1
    assert "1 works list 100 authors" in r.summary()
    r2 = compute_profile(works=works[:1])
    assert r2.n_works_capped == 0 and "100 authors" not in r2.summary()


# ---------------------------------------------------------------------------
# Sampling path
# ---------------------------------------------------------------------------


def test_stratified_sampling_pages_by_100_and_sends_key(monkeypatch):
    def work(i):
        return {"id": f"W{i}", "authorships": [
            {"author": {"id": f"https://openalex.org/A{i}", "orcid": f"https://orcid.org/0000-0000-0000-{i:04d}"}}]}

    pages = [_Resp(payload={"results": [work(i) for i in range(p * 100, p * 100 + 100)]}) for p in range(3)]
    authors = _Resp(payload={"results": [
        {"id": "https://openalex.org/A1", "orcid": "https://orcid.org/0000-0000-0000-0001",
         "works_count": 10, "summary_stats": {"h_index": 7}}]})
    rec = _Recorder(pages + [authors] * 8)
    monkeypatch.setattr(requests, "get", rec)
    monkeypatch.setenv("OPENALEX_API_KEY", KEY)
    out = sample_authors_stratified(topic_id="T11250", bands=[(5, 20)], per_band=1, works_sample_size=300)
    assert len(out) == 1 and out[0]["band"] == (5, 20)
    works_calls = [c for c in rec.calls if c["url"].endswith("/works")]
    assert len(works_calls) == 3
    assert all(c["params"]["per_page"] == 100 and "per-page" not in c["params"] for c in works_calls)
    assert [c["params"].get("page") for c in works_calls] == [None, 2, 3]
    assert all(c["params"].get("api_key") == KEY for c in rec.calls)
    author_calls = [c for c in rec.calls if c["url"].endswith("/authors")]
    assert author_calls and all(c["params"]["per_page"] <= 100 for c in author_calls)


def test_version():
    assert dpac.__version__ == "1.1.0"


def test_connection_error_does_not_carry_key(tmp_path, monkeypatch):
    def down(url, params=None, headers=None, timeout=None):
        raise requests.ConnectionError(f"HTTPSConnectionPool: Max retries exceeded with url: /works?api_key={params['api_key']}")

    monkeypatch.setattr(requests, "get", down)
    with pytest.raises(requests.ConnectionError) as ei:
        OpenAlexClient(cache_dir=tmp_path, api_key=KEY).fetch_works_by_orcid(FOCAL, use_cache=False)
    assert KEY not in str(ei.value) and "api_key=***" in str(ei.value)
    assert ei.value.__suppress_context__                      # the original, unmasked error is not shown
    monkeypatch.setenv("OPENALEX_API_KEY", KEY)
    with pytest.raises(requests.ConnectionError) as ei:
        sample_authors_stratified(topic_id="T11250", bands=[(5, 20)], per_band=1, works_sample_size=10)
    assert KEY not in str(ei.value)


def test_key_echoed_by_openalex_is_masked(tmp_path, monkeypatch):
    bad = _Resp(401, {"message": f"Invalid API key: {KEY}"})
    monkeypatch.setattr(requests, "get", _Recorder([bad]))
    with pytest.raises(requests.HTTPError) as ei:
        OpenAlexClient(cache_dir=tmp_path, api_key=KEY).fetch_works_by_orcid(FOCAL, use_cache=False)
    assert KEY not in str(ei.value) and "HTTP 401" in str(ei.value)


def test_cli_verbose_keeps_urllib3_quiet(tmp_path, monkeypatch):
    from dpac import cli
    monkeypatch.setattr(requests, "get", _Recorder([_Resp(payload={"results": [_raw(3, 0)], "meta": {}})]))
    assert cli.main(["--orcid", FOCAL, "-v", "--cache-dir", str(tmp_path), "--no-cache"]) == 0
    assert logging.getLogger("urllib3").getEffectiveLevel() >= logging.INFO
