"""
Tests for the parallel fetching added to dpac.selfcite (Chat 26), and for
the handling of author lists that OpenAlex caps at 100 names.

No network access is used: HTTP is replaced by fakes.
"""

from __future__ import annotations

import csv
import threading
import time

import pytest
import requests

from dpac import selfcite
from dpac.selfcite import (
    OpenAlexSource,
    QuotaExceeded,
    RunStopped,
    analyse_author,
    author_metrics,
    classify_links,
    group_report,
    harmonic_share,
    run_parallel,
    summary_row,
)

# Same record as tests/test_selfcite.py, with the focal author's id as a parameter.
_WORKS = [
    {"id": "P1", "year": 2010, "type": "article", "cbc": 3, "authors": ["A", "B"]},
    {"id": "P2", "year": 2012, "type": "article", "cbc": 3, "authors": ["C", "A"]},
    {"id": "P3", "year": 2015, "type": "article", "cbc": 3, "authors": ["A"]},
    {"id": "P4", "year": 2018, "type": "article", "cbc": 2, "authors": ["A", "D", "E"]},
]
_CITING = [
    {"id": "Q1", "year": 2016, "authors": ["A", "X"], "refs": ["P1", "P3"]},
    {"id": "Q2", "year": 2016, "authors": ["B", "Y"], "refs": ["P1", "P2"]},
    {"id": "Q3", "year": 2014, "authors": ["D", "Z"], "refs": ["P1"]},
    {"id": "Q4", "year": 2020, "authors": ["Z", "W"], "refs": ["P2", "P3", "P4"]},
    {"id": "Q5", "year": 2020, "authors": ["C", "Z"], "refs": ["P2", "P4"]},
    {"id": "Q6", "year": 2021, "authors": [None, "Z"], "refs": ["P3"]},
]


def _record(aid: str, extra_cites: int = 0):
    """The test record with focal author `aid`; `extra_cites` adds independent citing works."""
    sub = lambda xs: [aid if x == "A" else x for x in xs]               # noqa: E731
    works = [dict(w, id=f"{aid}{w['id']}", authors=sub(w["authors"])) for w in _WORKS]
    citing = [dict(q, id=f"{aid}{q['id']}", authors=sub(q["authors"]), refs=[f"{aid}{r}" for r in q["refs"]])
              for q in _CITING]
    citing += [{"id": f"{aid}E{k}", "year": 2022, "authors": ["V"], "refs": [f"{aid}P3"]} for k in range(extra_cites)]
    return works, citing


class MultiSource:
    """Fake OpenAlexSource serving several researchers, safe to call from threads."""

    def __init__(self, records, delay=0.0, fail_on=None):
        self.records, self.delay, self.fail_on = records, delay, fail_on or {}
        self.api_key = "k"
        self.n_requests = 0
        self._lock = threading.Lock()
        self._local = threading.local()
        self.active = 0
        self.max_active = 0

    def _tick(self):
        with self._lock:
            self.n_requests += 1
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        self._local.n = getattr(self._local, "n", 0) + 1
        time.sleep(self.delay)
        with self._lock:
            self.active -= 1

    def thread_requests(self):
        return getattr(self._local, "n", 0)

    def stop(self):
        pass

    def ensure_fields(self):
        pass

    def author_works(self, aid, work_types):
        self._tick()
        if aid in self.fail_on:
            raise self.fail_on[aid]
        return self.records[aid][0]

    def citing_works(self, batch, years):
        self._tick()
        aid = batch[0][: -2]
        out = []
        for q in self.records[aid][1]:
            refs = [r for r in q["refs"] if r in batch]
            if refs and years[0] <= q["year"] <= years[1]:
                out.append({**q, "refs": refs})
        return out

    def search_authors(self, query, cc):
        self._tick()
        surname = query.split()[-1]
        return [{"id": f"https://openalex.org/{surname}", "display_name": query, "works_count": 100,
                 "cited_by_count": 2000, "last_known_institutions": []}]


# ----------------------------------------------------------------------
# run_parallel
# ----------------------------------------------------------------------


def test_parallel_results_equal_serial():
    ids = [f"R{i}" for i in range(8)]
    src = MultiSource({a: _record(a, extra_cites=i) for i, a in enumerate(ids)}, delay=0.005)
    fn = lambda a: analyse_author(src, a, None, (1996, 2025), 10_000, batch_size=2)[0]   # noqa: E731
    seen = []
    par, stop = run_parallel(ids, fn, workers=4, on_result=lambda i, v: seen.append(i))
    ser, _ = run_parallel(ids, fn, workers=1)
    assert stop is None and sorted(seen) == list(range(8))
    assert par == ser
    assert [par[i]["n_links"] for i in range(8)] == [11 + i for i in range(8)]
    assert 1 < src.max_active <= 4                                    # really concurrent, never above 4


def test_parallel_stops_on_daily_limit():
    def fn(i):
        if i == 2:
            raise QuotaExceeded("Daily budget exceeded")
        time.sleep(0.02)
        return i

    res, stop = run_parallel(list(range(10)), fn, workers=2)
    assert isinstance(stop, QuotaExceeded)
    assert {0, 1} <= set(res) <= {0, 1, 3}                          # nothing new starts after the stop


def test_parallel_keeps_other_errors_per_item():
    def fn(i):
        if i == 1:
            raise ValueError("bad record")
        return i * 10

    res, stop = run_parallel([0, 1, 2], fn, workers=3)
    assert stop is None and res[0] == 0 and res[2] == 20 and isinstance(res[1], ValueError)


# ----------------------------------------------------------------------
# OpenAlexSource shared between threads
# ----------------------------------------------------------------------


class _Resp:
    def __init__(self, status, payload, headers=None):
        self.status_code, self._p, self.headers = status, payload, headers or {}

    def json(self):
        return self._p

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


def test_throttle_slots_are_shared_and_spaced(tmp_path):
    src = OpenAlexSource(cache_dir=tmp_path, throttle_sec=0.1)
    assert [round(src._reserve_slot(100.0), 6) for _ in range(3)] == [0.0, 0.1, 0.2]
    src = OpenAlexSource(cache_dir=tmp_path, throttle_sec=0.1)
    waits, lock = [], threading.Lock()

    def worker():
        for _ in range(25):
            w = src._reserve_slot(100.0)
            with lock:
                waits.append(round(w, 6))

    ts = [threading.Thread(target=worker) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(waits) == [round(0.1 * k, 6) for k in range(100)]   # every slot used once
    assert src.n_requests == 100


def test_threads_count_requests_and_use_own_sessions(tmp_path, monkeypatch):
    monkeypatch.setattr(selfcite.time, "sleep", lambda s: None)
    sessions, lock = [], threading.Lock()

    def fake_get(self, url, params=None, timeout=None):
        with lock:
            if not any(s is self for s in sessions):          # keep the objects, so ids cannot be reused
                sessions.append(self)
        return _Resp(200, {"results": [], "meta": {}})

    monkeypatch.setattr(requests.Session, "get", fake_get)
    src = OpenAlexSource(cache_dir=tmp_path, throttle_sec=0.0)
    per_thread = []

    def worker():
        for _ in range(5):
            src._get("works", {})
        per_thread.append(src.thread_requests())

    ts = [threading.Thread(target=worker) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert src.n_requests == 20 and per_thread == [5, 5, 5, 5]
    assert len(sessions) == 4 and not any(s is src._session for s in sessions)


def test_daily_limit_in_one_thread_stops_all(tmp_path, monkeypatch):
    monkeypatch.setattr(selfcite.time, "sleep", lambda s: None)
    calls = []

    def fake_get(self, url, params=None, timeout=None):
        calls.append(1)
        return _Resp(429, {"message": "Daily budget exceeded"}, {"X-RateLimit-Remaining": "0"})

    monkeypatch.setattr(requests.Session, "get", fake_get)
    src = OpenAlexSource(cache_dir=tmp_path, throttle_sec=0.0)
    with pytest.raises(QuotaExceeded):
        src._get("works", {})
    errors = []

    def worker():
        try:
            src._get("works", {})
        except QuotaExceeded as exc:
            errors.append(exc)

    ts = [threading.Thread(target=worker) for _ in range(3)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(errors) == 3 and len(calls) == 1 and src.quota_hit       # no further request reached OpenAlex
    src2 = OpenAlexSource(cache_dir=tmp_path)
    src2.stop()
    with pytest.raises(RunStopped):
        src2._get("works", {})


def test_concurrent_cache_writes_same_key(tmp_path):
    src = OpenAlexSource(cache_dir=tmp_path)
    ts = [threading.Thread(target=src._write, args=("k", {"v": i})) for i in range(8)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert src._read("k")["v"] in range(8)
    assert list(tmp_path.glob("*.tmp")) == []


def test_authors_count_parsed_only_when_list_is_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(selfcite.time, "sleep", lambda s: None)
    listed = [{"author": {"id": f"https://openalex.org/X{i}"}} for i in range(100)]
    page = {"meta": {"next_cursor": None}, "results": [
        {"id": "W1", "publication_year": 2020, "type": "article", "cited_by_count": 1, "authors_count": 150,
         "authorships": listed},
        {"id": "W2", "publication_year": 2021, "type": "article", "cited_by_count": 1, "authors_count": 1,
         "authorships": [{"author": {"id": "https://openalex.org/A1"}}]}]}
    seen = []

    def fake_get(url, params=None, timeout=None):
        seen.append(params["select"])
        return _Resp(200, page)

    src = OpenAlexSource(cache_dir=tmp_path)
    monkeypatch.setattr(src._session, "get", fake_get)
    w = src.author_works("A1", None)
    assert w[0]["n"] == 150 and len(w[0]["authors"]) == 100 and "n" not in w[1]
    assert seen[0].endswith(",authors_count")
    src2 = OpenAlexSource(cache_dir=tmp_path / "b", authors_count=False)
    monkeypatch.setattr(src2._session, "get", fake_get)
    src2.author_works("A1", None)
    assert "authors_count" not in seen[-1]


# ----------------------------------------------------------------------
# Capped author lists and rejected batches
# ----------------------------------------------------------------------


def test_capped_author_lists():
    p1 = {"id": "P1", "year": 2015, "type": "article", "cbc": 1, "authors": [f"X{i}" for i in range(100)], "n": 150}
    p2 = {"id": "P2", "year": 2016, "type": "article", "cbc": 2, "authors": ["A", "B"]}
    citing = [
        {"id": "Q1", "year": 2020, "authors": ["X0", "Z"], "refs": ["P1"]},                     # co-author via P1
        {"id": "Q2", "year": 2020, "authors": [f"Y{i}" for i in range(100)], "n": 200, "refs": ["P2"]},
        {"id": "Q3", "year": 2021, "authors": ["B", "A"], "refs": ["P2"]},                      # own
    ]
    links = {(l["citing"], l["cited"]): l for l in classify_links("A", [p1, p2], citing)}
    assert links[("Q1", "P1")]["cls"] == "coauthor" and links[("Q1", "P1")]["trunc"]
    assert links[("Q2", "P2")]["cls"] == "independent" and links[("Q2", "P2")]["trunc"]
    assert links[("Q3", "P2")]["trunc"] is False and links[("Q3", "P2")]["w_equal"] == pytest.approx(0.0)
    m = author_metrics("A", [p1, p2], list(links.values()))
    assert m["n_works_over_100_authors"] == 1
    assert m["share_links_trunc"] == pytest.approx(2 / 3)
    assert m["median_team_size"] == pytest.approx(76)
    assert m["all_credit_equal"] == pytest.approx(1 / 150 + 2 / 2)
    share_p1 = harmonic_share(None, 150, 100)
    assert share_p1 == pytest.approx(sum((1 / k) for k in range(101, 151)) / 50 / sum(1 / k for k in range(1, 151)))
    assert m["all_credit_harmonic"] == pytest.approx(1 * share_p1 + 2 * (1 / 1.5))
    assert harmonic_share(None, 3, 3) == 0.0 and harmonic_share(2, 2) == pytest.approx(0.5 / 1.5)


def test_rejected_batch_is_split():
    works, citing = _record("A")
    src = MultiSource({"A": (works, citing)})
    sizes = []
    orig = src.citing_works

    def picky(batch, years):
        sizes.append(len(batch))
        if len(batch) > 1:
            raise requests.HTTPError("HTTP 400", response=_Resp(400, {}))
        return orig(batch, years)

    src.citing_works = picky
    m, _ = analyse_author(src, "A", None, (1996, 2025), 10_000, batch_size=4)
    assert m["n_links"] == 11 and sizes == [4, 2, 1, 1, 2, 1, 1]


# ----------------------------------------------------------------------
# Outputs
# ----------------------------------------------------------------------


def test_summary_row_drops_identifying_columns():
    a = {"label": "TST-S-001", "group": "S", "authfull": "Doe, J.", "inst_name": "Somewhere", "openalex_id": "A1",
         "match_name": "J. Doe", "use": "Y", "field": "Engineering", "np6025": "120", "match_flag": "high"}
    row = summary_row(a, "TST-S-001", "S", {"status": "ok", "n_links": 5, "share_own": 0.1234567891})
    for k in ("authfull", "inst_name", "openalex_id", "match_name", "use"):
        assert k not in row
    assert row["field"] == "Engineering" and row["np6025"] == "120" and row["share_own"] == 0.123457
    assert list(row)[:2] == ["label", "group"]


def test_group_report_by_field():
    base = {"status": "ok", "share_own": 0.1, "share_coauthor": 0.1, "share_network": 0.1, "share_independent": 0.7,
            "self_rate_list_rule": 0.2, "coauthor_share_of_self": 0.5, "median_team_size": 4, "share_links_trunc": 0}
    for d in ("all", "excl_own", "excl_shared", "excl_network", "frac_equal", "frac_harmonic", "frac_network"):
        base.update({f"{d}_cites": 10, f"{d}_h": 5, f"{d}_hm": 2, f"{d}_cites_per_citing": 1.1})
    rows = [dict(base, field="Engineering", group="S"), dict(base, field="Engineering", group="S"),
            dict(base, field="Physics & Astronomy", group="S"), dict(base, field="Engineering", group="C", status="error")]
    rep = group_report(rows)
    assert [(r["field"], r["group"], r["n_researchers"]) for r in rep] == [("Engineering", "S", 2),
                                                                         ("Physics & Astronomy", "S", 1)]
    assert "field" not in group_report([dict(base, group="S")])[0]


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_run_command_end_to_end(tmp_path, monkeypatch):
    ids = [f"R{i}" for i in range(6)]
    src = MultiSource({a: _record(a, extra_cites=i) for i, a in enumerate(ids)}, delay=0.003)
    monkeypatch.setattr(selfcite, "_source", lambda args: src)
    rows = [{"label": f"ENG-S-{i + 1:03d}", "group": "Self-citation-only entrants", "field": "Engineering",
             "authfull": f"Person, {i}", "inst_name": "Inst", "openalex_id": a, "use": "Y"} for i, a in enumerate(ids)]
    rows.append(dict(rows[0], label="ENG-S-099"))                     # same OpenAlex id twice: kept once
    rows.append(dict(rows[1], label="ENG-S-100", use=""))             # not approved: skipped
    _write(tmp_path / "authors.csv", rows)
    out = tmp_path / "out"
    assert selfcite.main(["run", "--authors", str(tmp_path / "authors.csv"), "--output-dir", str(out),
                          "--workers", "3"]) == 0
    with open(out / "selfcite_summary.csv", encoding="utf-8") as f:
        summ = list(csv.DictReader(f))
    with open(out / "selfcite_key_PRIVATE.csv", encoding="utf-8") as f:
        key = list(csv.DictReader(f))
    assert [r["label"] for r in summ] == [f"ENG-S-{i:03d}" for i in range(1, 7)]
    assert [int(r["n_links"]) for r in summ] == [11 + i for i in range(6)]
    assert "authfull" not in summ[0] and "openalex_id" not in summ[0] and summ[0]["field"] == "Engineering"
    assert key[0]["name"] == "Person, 0" and key[0]["openalex_id"] == "R0"
    assert (out / "selfcite_groups.csv").exists()


def test_run_command_stops_cleanly_on_daily_limit(tmp_path, monkeypatch):
    ids = [f"R{i}" for i in range(5)]
    src = MultiSource({a: _record(a) for a in ids}, delay=0.01, fail_on={"R1": QuotaExceeded("Daily budget exceeded")})
    monkeypatch.setattr(selfcite, "_source", lambda args: src)
    _write(tmp_path / "a.csv", [{"label": f"L{i}", "group": "C", "openalex_id": a} for i, a in enumerate(ids)])
    rc = selfcite.main(["run", "--authors", str(tmp_path / "a.csv"), "--output-dir", str(tmp_path / "o"),
                        "--workers", "1"])
    with open(tmp_path / "o" / "selfcite_summary.csv", encoding="utf-8") as f:
        assert [r["label"] for r in csv.DictReader(f)] == ["L0"]
    assert rc == 2


def test_resolve_command_parallel_keeps_order(tmp_path, monkeypatch):
    src = MultiSource({}, delay=0.003)
    monkeypatch.setattr(selfcite, "_source", lambda args: src)
    rows = [{"label": f"TST-C-{i:03d}", "group_code": "C", "authfull": f"Surname{i}, Given", "inst_name": "",
             "cc2": "", "np6025": "100", "nc9625": "2000"} for i in range(1, 9)]
    _write(tmp_path / "in.csv", rows)
    assert selfcite.main(["resolve", "--input", str(tmp_path / "in.csv"), "--output", str(tmp_path / "out.csv"),
                          "--workers", "4"]) == 0
    with open(tmp_path / "out.csv", encoding="utf-8") as f:
        out = list(csv.DictReader(f))
    assert [r["label"] for r in out] == [r["label"] for r in rows]
    assert [r["openalex_id"] for r in out] == [f"Surname{i}" for i in range(1, 9)]


def test_probe_reports_page_size_field_and_allowance(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(selfcite.time, "sleep", lambda s: None)
    src = OpenAlexSource(cache_dir=tmp_path, api_key="SECRETKEY")
    hdr = {"X-RateLimit-Limit": "10000", "X-RateLimit-Remaining": "9998", "X-RateLimit-Reset": "7200"}
    seen = []

    def fake_get(url, params=None, timeout=None):
        seen.append(dict(params))
        if "authors_count:>500" in params["filter"]:
            return _Resp(200, {"results": [{"id": "W9", "authors_count": 2900,
                                            "authorships": [{"author": {"id": "A"}}] * 100}]}, hdr)
        if "authors_count" in params["select"]:
            return _Resp(200, {"results": [{"id": "W1", "authors_count": 3}]}, hdr)
        return _Resp(200, {"results": [{"id": f"W{i}"} for i in range(100)]}, hdr)

    monkeypatch.setattr(src._session, "get", fake_get)
    monkeypatch.setattr(selfcite, "_source", lambda args: src)
    assert selfcite.main(["probe"]) == 0
    out = capsys.readouterr().out
    assert "asked 100, got 100" in out and "authors_count: available" in out and "[100], true counts [2900]" in out
    assert "9998 left of 10000" in out and "2.0 h" in out and "SECRETKEY" not in out
    assert all("per-page" not in p for p in seen) and seen[0]["per_page"] == 100


def test_probe_without_authors_count_still_ok(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(selfcite.time, "sleep", lambda s: None)
    src = OpenAlexSource(cache_dir=tmp_path, api_key="SECRETKEY")

    def fake_get(url, params=None, timeout=None):
        if "authors_count" in params.get("select", ""):
            return _Resp(400, {"error": "Invalid query parameters", "message": "authors_count is not a valid select field"})
        return _Resp(200, {"results": [{"id": "W1"}]})

    monkeypatch.setattr(src._session, "get", fake_get)
    monkeypatch.setattr(selfcite, "_source", lambda args: src)
    assert selfcite.main(["probe"]) == 0
    out = capsys.readouterr().out
    assert "authors_count: not available" in out and "Probe OK." in out


def test_http_errors_carry_openalex_message_without_key(tmp_path, monkeypatch):
    monkeypatch.setattr(selfcite.time, "sleep", lambda s: None)
    src = OpenAlexSource(cache_dir=tmp_path, api_key="SECRETKEY")
    monkeypatch.setattr(src._session, "get", lambda url, params=None, timeout=None: _Resp(
        400, {"error": "Invalid query parameters", "message": "per_page must be between 1 and 100"}))
    with pytest.raises(requests.HTTPError) as ei:
        src._get("works", {"filter": "x"})
    assert "per_page must be between 1 and 100" in str(ei.value) and "SECRETKEY" not in str(ei.value)
    assert selfcite._redact("GET /works?filter=a&api_key=SECRETKEY&mailto=x") == "GET /works?filter=a&api_key=***&mailto=x"


def test_missing_authors_count_falls_back_to_capped_flag(tmp_path, monkeypatch):
    monkeypatch.setattr(selfcite.time, "sleep", lambda s: None)
    listed = [{"author": {"id": f"https://openalex.org/X{i}"}} for i in range(100)]
    page = {"meta": {"next_cursor": None}, "results": [
        {"id": "W1", "publication_year": 2020, "type": "article", "cited_by_count": 1, "authorships": listed},
        {"id": "W2", "publication_year": 2021, "type": "article", "cited_by_count": 1,
         "authorships": [{"author": {"id": "https://openalex.org/A1"}}]}]}
    selects = []

    def fake_get(url, params=None, timeout=None):
        selects.append(params["select"])
        if "authors_count" in params["select"]:
            return _Resp(400, {"message": "authors_count is not a valid select field"})
        return _Resp(200, page)

    src = OpenAlexSource(cache_dir=tmp_path)
    monkeypatch.setattr(src._session, "get", fake_get)
    src.ensure_fields()
    assert src.authors_count is False
    w = src.author_works("A1", None)
    assert selects[-1] == "id,publication_year,type,cited_by_count,authorships"
    assert w[0].get("capped") is True and "capped" not in w[1]
    assert selfcite.is_truncated(w[0]) and not selfcite.is_truncated(w[1])
    assert selfcite.n_authors(w[0]) == 100


def test_error_in_result_handler_stops_workers():
    started = []

    def fn(i):
        started.append(i)
        time.sleep(0.01)
        return i

    def handler(i, v):
        raise PermissionError("selfcite_summary.csv is open in Excel")

    with pytest.raises(PermissionError):
        run_parallel(list(range(20)), fn, workers=2, on_result=handler)
    assert len(started) < 20                                          # the queue was cancelled


def test_capped_citing_paper_without_count_is_flagged():
    """A citing paper with a 100-name list and no `authors_count` touches a capped list."""
    p1 = {"id": "P1", "year": 2015, "type": "article", "cbc": 1, "authors": ["A", "B"]}
    citing = [
        {"id": "Q1", "year": 2020, "authors": [f"Y{i}" for i in range(100)], "capped": True, "refs": ["P1"]},
        {"id": "Q2", "year": 2020, "authors": ["Z"], "refs": ["P1"]},
    ]
    links = {l["citing"]: l for l in classify_links("A", [p1], citing)}
    assert links["Q1"]["trunc"] is True and links["Q2"]["trunc"] is False
    assert author_metrics("A", [p1], list(links.values()))["share_links_trunc"] == pytest.approx(0.5)


def test_connection_errors_do_not_carry_key(tmp_path, monkeypatch):
    monkeypatch.setattr(selfcite.time, "sleep", lambda s: None)
    src = OpenAlexSource(cache_dir=tmp_path, api_key="SECRETKEY", max_retries=2)

    def down(url, params=None, timeout=None):
        raise requests.ConnectionError(f"Max retries exceeded with url: /works?filter=x&api_key={params['api_key']}")

    monkeypatch.setattr(src._session, "get", down)
    with pytest.raises(requests.ConnectionError) as ei:
        src._get("works", {"filter": "x"})
    assert "SECRETKEY" not in str(ei.value) and "api_key=***" in str(ei.value)
    assert ei.value.__suppress_context__
