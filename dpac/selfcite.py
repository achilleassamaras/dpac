"""
Citation-source decomposition for a researcher's OpenAlex record.

Every citation link (citing work Q -> cited work P of the focal author A) is
placed in exactly one class:

- own          A is an author of Q.
- coauthor     A is not on Q, but another author of P is.
- network      Neither of the above, but an author of Q had co-authored with A
               (on any of A's works) in or before Q's publication year.
- independent  None of the above.

The Stanford/Elsevier top-2% list removes `own` and `coauthor` together (a
citation is a self-citation when Q and P share any author). Scopus's
"selected author" option removes `own` only. The `network` class is what
neither rule removes.

Beside the binary rules, three fractional rules weight each link by the share
of Q that is NOT held by overlapping authors (Schubert, Glanzel and Thijs,
2006, for the equal-share overlap idea; declared shares would replace the
imputed ones):

- frac_equal     1 - |authors(Q) in authors(P)| / n_Q
- frac_harmonic  1 - sum of harmonic byline shares of those authors in Q
- frac_network   1 - share of Q held by authors of P or by A's collaborators

For each rule the module reports total citations, h-index, Schreiber's
hm-index, and the dpac author-level credit under equal and harmonic shares.

OpenAlex caps the `authorships` list at the first 100 authors. When OpenAlex
returns `authors_count`, team size, equal shares and hm use the true author
count; when it does not (the 2026 API), lists of 100 names are marked as
capped (true count unknown, at least 100). Either way, links that touch a
capped list are flagged (`trunc`), because overlap beyond the 100th author
cannot be seen.

Researchers are processed in parallel (default four at a time, `--workers`).
All workers share one throttle, one request counter and one cache; when
OpenAlex reports the daily allowance used up, every worker stops at its next
request and the run writes what it has. Re-running the same command resumes:
finished work is read from the cache and costs no requests.

Command line (once dpac is installed, or from the repository root):

    python -m dpac.selfcite probe
    python -m dpac.selfcite cohort  --output authors_cohort.csv
    python -m dpac.selfcite resolve --input list_rows.csv --output authors_list.csv
    python -m dpac.selfcite run     --authors authors_cohort.csv authors_list.csv --output-dir selfcite_out
    python -m dpac.selfcite report  --output-dir selfcite_out

`resolve` reads rows of the Stanford/Elsevier list (columns `authfull`,
`inst_name`, `cc2`, `np6025`, `nc9625`) and adds OpenAlex author ids.
`run` writes `selfcite_summary.csv` (labels and metrics, no names or ids),
`selfcite_groups.csv`, `selfcite_shares.png` and `selfcite_key_PRIVATE.csv`
(labels to people: keep it private).

Set OPENALEX_API_KEY (free at openalex.org/settings/api); without a key the
daily allowance is small. DPAC_MAILTO is still passed on, though OpenAlex has
ignored `mailto` since its 2026 switch to API keys. The key is masked in every
message the module prints or writes.
DPAC_SELFCITE_CACHE overrides the cache folder (default ~/.dpac_cache/selfcite).
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import logging
import math
import os
import re
import statistics
import sys
import threading
import time
import unicodedata
import uuid
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Callable, Iterable, Optional

import requests

from .metrics import raw_h_index
from .openalex import (
    API_KEY_ENV,
    DEFAULT_CACHE_DIR,
    DEFAULT_THROTTLE_SEC,
    DEFAULT_USER_AGENT,
    OPENALEX_BASE,
    mask_request_error,
    redact_api_key,
)

logger = logging.getLogger(__name__)

DEFAULT_WORK_TYPES = ["article", "review", "book-chapter", "book"]
DEFAULT_CITE_YEARS = (1996, 2025)          # mirrors the 2026 (v9) career-long window
DEFAULT_MAX_CITATIONS = 60000              # skip very large records (time and disk)
CITES_BATCH = 100                          # work ids per `cites:` OR-filter (OpenAlex allows 100)
DEFAULT_WORKERS = 4                        # researchers processed at the same time
AUTHORSHIP_CAP = 100                       # OpenAlex lists at most the first 100 authors
PER_PAGE = 100                             # OpenAlex maximum page size (2026 API: 1-100)
CACHE_VERSION = "selfcite-v2"              # v2 adds authors_count; v1 entries are not reused

CLASSES = ("own", "coauthor", "network", "independent")

# Columns of an author CSV that identify a person. They go to the private key
# file only, never to selfcite_summary.csv.
PRIVATE_COLUMNS = frozenset({
    "authfull", "inst_name", "openalex_id", "match_name", "match_works", "match_cites", "use",
})


def _short(oid: Optional[str]) -> Optional[str]:
    """'https://openalex.org/W123' -> 'W123'."""
    if not oid:
        return None
    return str(oid).rstrip("/").rsplit("/", 1)[-1]


def _redact(text: str) -> str:
    """Hide the API key in URLs that end up in messages or output files."""
    return redact_api_key(text, os.environ.get(API_KEY_ENV))


def _describe_error(resp, path: str) -> str:
    """'HTTP 400 on /works: <OpenAlex's own message>', without the API key."""
    detail = ""
    try:
        body = resp.json() or {}
        detail = str(body.get("message") or body.get("error") or "")
    except Exception:                                                # noqa: BLE001
        detail = str(getattr(resp, "text", "") or "")[:300]
    return _redact(f"HTTP {resp.status_code} on /{path}" + (f": {detail}" if detail else ""))


# ======================================================================
# OpenAlex access (cached, throttled, retried)
# ======================================================================


class RunStopped(RuntimeError):
    """The run was told to stop (Ctrl+C); workers end at their next request."""


class QuotaExceeded(RunStopped):
    """OpenAlex refused further requests for today (daily allowance used up)."""


QUOTA_HELP = (
    "OpenAlex has stopped answering: today's request allowance is used up. Without an API key it covers "
    "roughly 1,000 list requests a day; a free key (openalex.org/settings/api) gives about ten times that. "
    "Everything fetched so far is cached. Set OPENALEX_API_KEY and run the same command again, or wait "
    "for the reset at midnight UTC."
)


class OpenAlexSource:
    """Fetches only what the decomposition needs, and caches it compactly.

    Responses are reduced to ids, years and author-id lists before caching,
    so the cache stays small even for records with tens of thousands of
    citing works. Re-runs read from the cache and make no requests.

    One instance can be shared by several worker threads: requests are
    spaced by a common throttle, counted under a lock, and sent through one
    HTTP session per thread. After a daily-limit refusal (or `stop()`),
    every later request raises at once instead of reaching OpenAlex.
    """

    def __init__(
        self,
        mailto: Optional[str] = None,
        api_key: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        throttle_sec: float = DEFAULT_THROTTLE_SEC,
        max_retries: int = 6,
        authors_count: bool = True,
    ) -> None:
        self.mailto = mailto or os.environ.get("DPAC_MAILTO")
        self.api_key = api_key or os.environ.get("OPENALEX_API_KEY")
        env_cache = os.environ.get("DPAC_SELFCITE_CACHE")
        self.cache_dir = Path(cache_dir) if cache_dir else (Path(env_cache) if env_cache else DEFAULT_CACHE_DIR / "selfcite")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.throttle_sec = throttle_sec
        self.max_retries = max_retries
        self.authors_count = authors_count
        self.n_requests = 0
        self._lock = threading.Lock()
        self._next_slot = 0.0
        self._quota = threading.Event()
        self._quota_msg = ""
        self._halt = threading.Event()
        self._local = threading.local()
        self._owner = threading.current_thread()
        self._session = requests.Session()
        self._session.headers["User-Agent"] = DEFAULT_USER_AGENT
        self.last_headers: dict = {}

    # ----- threads -----

    def _thread_session(self) -> requests.Session:
        """The creating thread uses `_session`; each worker thread gets its own."""
        if threading.current_thread() is self._owner:
            return self._session
        s = getattr(self._local, "session", None)
        if s is None:
            s = requests.Session()
            s.headers.update(self._session.headers)
            self._local.session = s
        return s

    def _reserve_slot(self, now: float) -> float:
        """Book the next request start time; return how long to wait for it."""
        with self._lock:
            start = max(now, self._next_slot)
            self._next_slot = start + self.throttle_sec
            self.n_requests += 1
        self._local.n = getattr(self._local, "n", 0) + 1
        return start - now

    def thread_requests(self) -> int:
        """Requests made so far by the calling thread (for per-researcher counts)."""
        return getattr(self._local, "n", 0)

    def stop(self) -> None:
        """Make every later request raise RunStopped (used on Ctrl+C)."""
        self._halt.set()

    @property
    def quota_hit(self) -> bool:
        return self._quota.is_set()

    # ----- cache -----

    def _path(self, key: str) -> Path:
        return self.cache_dir / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json.gz")

    def _read(self, key: str):
        p = self._path(key)
        if not p.exists():
            return None
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:                                   # noqa: BLE001
            logger.warning("cache read failed (%s); refetching", exc)
            return None

    def _write(self, key: str, payload) -> None:
        p = self._path(key)
        tmp = p.with_name(f"{p.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
        for attempt in range(5):
            try:
                tmp.replace(p)
                return
            except PermissionError:                                # Windows: target open in another thread
                time.sleep(0.2 * (attempt + 1))
        logger.warning("could not update cache file %s; continuing without it", p.name)
        try:
            tmp.unlink()
        except OSError:
            pass

    # ----- HTTP -----

    def _get(self, path: str, params: dict) -> dict:
        params = dict(params)
        if self.mailto:
            params["mailto"] = self.mailto
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{OPENALEX_BASE}/{path}"
        for attempt in range(self.max_retries):
            if self._quota.is_set():
                raise QuotaExceeded(self._quota_msg or "daily allowance used up")
            if self._halt.is_set():
                raise RunStopped("stopped")
            wait = self._reserve_slot(time.monotonic())
            if wait > 0:
                time.sleep(wait)
            try:
                resp = self._thread_session().get(url, params=params, timeout=60)
                self.last_headers = dict(getattr(resp, "headers", None) or {})
                if resp.status_code == 429:
                    headers = getattr(resp, "headers", None) or {}
                    remaining = str(headers.get("X-RateLimit-Remaining", "")).strip()
                    try:
                        msg = str((resp.json() or {}).get("message", ""))
                    except Exception:                                    # noqa: BLE001
                        msg = ""
                    daily = remaining in ("0", "0.0") or any(w in msg.lower() for w in ("daily", "budget", "credit"))
                    if daily or attempt == self.max_retries - 1:
                        reset = headers.get("X-RateLimit-Reset", "")
                        self._quota_msg = " ".join(x for x in (msg, f"(reset: {reset})" if reset else "") if x) or "HTTP 429"
                        self._quota.set()
                        raise QuotaExceeded(self._quota_msg)
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
                if resp.status_code >= 400:
                    raise requests.HTTPError(_describe_error(resp, path), response=resp)
                return resp.json()
            except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                retryable = status in (None, 429, 500, 502, 503, 504)
                if not retryable or attempt == self.max_retries - 1:
                    raise mask_request_error(exc, self.api_key) from None
                wait = min(60, 2 ** attempt)
                logger.warning("OpenAlex %s; retrying in %ss", status or type(exc).__name__, wait)
                time.sleep(wait)
        raise RuntimeError("unreachable")

    def _paged(self, path: str, params: dict) -> Iterable[dict]:
        cursor = "*"
        while cursor:
            payload = self._get(path, {**params, "per_page": PER_PAGE, "cursor": cursor})
            yield from payload.get("results", [])
            cursor = (payload.get("meta") or {}).get("next_cursor")

    def _select(self, fields: str) -> str:
        return fields + (",authors_count" if self.authors_count else "")

    @staticmethod
    def _authors(r: dict) -> list:
        return [_short((ap.get("author") or {}).get("id")) for ap in (r.get("authorships") or [])]

    @staticmethod
    def _add_count(rec: dict, r: dict) -> dict:
        """Keep the true author count only when the listed authors fall short of it.

        Without `authors_count`, a list of exactly 100 authors is marked as
        capped (true count unknown, at least 100).
        """
        n = r.get("authors_count")
        if isinstance(n, int):
            if n > len(rec["authors"]):
                rec["n"] = n
        elif len(rec["authors"]) >= AUTHORSHIP_CAP:
            rec["capped"] = True
        return rec

    def ensure_fields(self) -> None:
        """Check once that OpenAlex returns `authors_count`; if it refuses it, carry on without it."""
        if not self.authors_count:
            return
        try:
            self._get("works", {"filter": "publication_year:2020", "select": "id,authors_count", "per_page": 1})
        except requests.HTTPError as exc:
            if getattr(getattr(exc, "response", None), "status_code", None) != 400:
                raise
            self.authors_count = False
            print("Note: OpenAlex does not return authors_count; author lists of 100 names are flagged as capped "
                  "instead (true team size unknown for those papers).", flush=True)

    # ----- public -----

    def author_works(self, author_id: str, work_types: Optional[list[str]]) -> list[dict]:
        aid = _short(author_id)
        types_tag = "+".join(sorted(work_types)) if work_types else "all"
        key = f"{CACHE_VERSION}::works::{aid}::{types_tag}"
        hit = self._read(key)
        if hit is not None:
            return hit
        filt = f"author.id:{aid}"
        if work_types:
            filt += f",type:{'|'.join(work_types)}"
        out = []
        for r in self._paged("works", {"filter": filt, "select": self._select("id,publication_year,type,cited_by_count,authorships")}):
            out.append(self._add_count({
                "id": _short(r.get("id")),
                "year": int(r.get("publication_year") or 0),
                "type": r.get("type"),
                "cbc": int(r.get("cited_by_count") or 0),
                "authors": self._authors(r),
            }, r))
        self._write(key, out)
        return out

    def citing_works(self, cited_ids: list[str], years: tuple[int, int]) -> list[dict]:
        ids = sorted(_short(i) for i in cited_ids)
        key = f"{CACHE_VERSION}::citing::{years[0]}-{years[1]}::" + "|".join(ids)
        hit = self._read(key)
        if hit is not None:
            return hit
        wanted = set(ids)
        filt = f"cites:{'|'.join(ids)},publication_year:{years[0]}-{years[1]}"
        out = []
        for r in self._paged("works", {"filter": filt, "select": self._select("id,publication_year,authorships,referenced_works")}):
            refs = [x for x in (_short(u) for u in (r.get("referenced_works") or [])) if x in wanted]
            out.append(self._add_count({
                "id": _short(r.get("id")),
                "year": int(r.get("publication_year") or 0),
                "authors": self._authors(r),
                "refs": refs,
            }, r))
        self._write(key, out)
        return out

    def search_authors(self, query: str, country_code: Optional[str]) -> list[dict]:
        params = {
            "search": query,
            "select": "id,display_name,display_name_alternatives,works_count,cited_by_count,last_known_institutions,summary_stats",
            "per_page": 25,
        }
        if country_code:
            params["filter"] = f"last_known_institutions.country_code:{country_code.upper()}"
        key = "selfcite-v1::authors::" + json.dumps(params, sort_keys=True)   # unchanged format; v1 entries reused
        hit = self._read(key)
        if hit is not None:
            return hit
        res = self._get("authors", params).get("results", [])
        self._write(key, res)
        return res


# ======================================================================
# Core computation (pure functions; unit-tested)
# ======================================================================


def first_collaboration_years(focal: str, works: list[dict]) -> dict[str, int]:
    """Earliest year each co-author shares a work with the focal author."""
    first: dict[str, int] = {}
    for w in works:
        y = w.get("year") or 0
        for a in w["authors"]:
            if a and a != focal and (a not in first or y < first[a]):
                first[a] = y
    return first


def _harmonic_number(n: int) -> float:
    return sum(1.0 / j for j in range(1, n + 1)) if n > 0 else 1.0


def n_authors(rec: dict) -> int:
    """True author count: `n` when OpenAlex capped the list, else the list length."""
    return int(rec.get("n") or len(rec["authors"]))


def is_truncated(rec: dict) -> bool:
    return bool(rec.get("capped")) or n_authors(rec) > len(rec["authors"])


def harmonic_share(pos: Optional[int], n: int, n_listed: Optional[int] = None) -> float:
    """Harmonic byline share of position `pos` among `n` authors.

    When the focal author is missing from a list that OpenAlex capped
    (`n_listed` < `n`), the position lies somewhere after the listed authors;
    the mean share of those positions is used.
    """
    h_n = _harmonic_number(n)
    if pos:
        return (1.0 / pos) / h_n
    listed = n if n_listed is None else n_listed
    if listed < n:
        return (h_n - _harmonic_number(listed)) / ((n - listed) * h_n)
    return 0.0


def classify_links(focal: str, works: list[dict], citing: list[dict]) -> list[dict]:
    """Return one record per distinct (citing, cited) pair, classified.

    `works` and `citing` use the compact records produced by OpenAlexSource.
    The same citing work may arrive from several `cites:` batches; pairs are
    de-duplicated.
    """
    focal = _short(focal)
    wmap = {w["id"]: w for w in works}
    first = first_collaboration_years(focal, works)
    seen: set[tuple[str, str]] = set()
    links: list[dict] = []
    for q in citing:
        qa = q["authors"]
        n_q = n_authors(q)
        q_trunc = is_truncated(q)
        qset = {a for a in qa if a}
        q_year = q.get("year") or 9999

        def is_prior(a: str) -> bool:
            y = first.get(a)
            return y is not None and y <= q_year

        h_q = _harmonic_number(n_q)
        for p_id in q.get("refs", []):
            if p_id not in wmap or p_id == q["id"] or (q["id"], p_id) in seen:
                continue
            seen.add((q["id"], p_id))
            pset = {a for a in wmap[p_id]["authors"] if a}
            own = focal in qset
            co = bool((qset & pset) - {focal})
            others = qset - pset
            in_net_prior = any(is_prior(a) for a in others)
            in_net_any = any(a in first for a in others)
            if own:
                cls = "own"
            elif co:
                cls = "coauthor"
            elif in_net_prior:
                cls = "network"
            else:
                cls = "independent"
            if n_q:
                ov_eq = sum(1 for a in qa if a and a in pset) / n_q
                ov_h = sum((1.0 / (i + 1)) / h_q for i, a in enumerate(qa) if a and a in pset)
                ov_net = sum(1 for a in qa if a and (a in pset or is_prior(a))) / n_q
            else:
                ov_eq = ov_h = ov_net = 0.0
            links.append({
                "citing": q["id"],
                "cited": p_id,
                "year": q.get("year") or 0,
                "cls": cls,
                "network_any_only": (cls == "independent" and in_net_any),
                "w_equal": 1.0 - ov_eq,
                "w_harmonic": 1.0 - ov_h,
                "w_network": 1.0 - ov_net,
                "trunc": q_trunc or is_truncated(wmap[p_id]),
            })
    return links


def hm_index(items: Iterable[tuple[float, int]]) -> float:
    """Schreiber (2008) hm-index from (citations, n_authors) pairs.

    Papers are ranked by citations; each paper advances the effective rank
    by 1/n_authors; hm is the largest effective rank r_eff at which the
    paper's citations are still >= r_eff.
    """
    r_eff = 0.0
    hm = 0.0
    for c, n in sorted(items, key=lambda t: t[0], reverse=True):
        r_eff += 1.0 / max(1, n)
        if c >= r_eff:
            hm = r_eff
        else:
            break
    return hm


DEFINITIONS: dict[str, Callable[[dict], float]] = {
    "all": lambda l: 1.0,
    "excl_own": lambda l: 0.0 if l["cls"] == "own" else 1.0,
    "excl_shared": lambda l: 1.0 if l["cls"] in ("network", "independent") else 0.0,
    "excl_network": lambda l: 1.0 if l["cls"] == "independent" else 0.0,
    "frac_equal": lambda l: l["w_equal"],
    "frac_harmonic": lambda l: l["w_harmonic"],
    "frac_network": lambda l: l["w_network"],
}
BINARY = ("all", "excl_own", "excl_shared", "excl_network")


def author_metrics(focal: str, works: list[dict], links: list[dict]) -> dict:
    """Class counts and metrics under every definition for one researcher."""
    focal = _short(focal)
    out: dict = {}
    n = len(links)
    counts = {c: 0 for c in CLASSES}
    for l in links:
        counts[l["cls"]] += 1
    out["n_works"] = len(works)
    out["n_links"] = n
    for c in CLASSES:
        out[f"n_{c}"] = counts[c]
        out[f"share_{c}"] = counts[c] / n if n else float("nan")
    out["n_network_any_only"] = sum(1 for l in links if l["network_any_only"])
    out["self_rate_list_rule"] = (counts["own"] + counts["coauthor"]) / n if n else float("nan")
    self_total = counts["own"] + counts["coauthor"]
    out["coauthor_share_of_self"] = counts["coauthor"] / self_total if self_total else float("nan")
    sizes = [n_authors(w) for w in works if w["authors"]]
    out["median_team_size"] = statistics.median(sizes) if sizes else float("nan")
    out["n_works_over_100_authors"] = sum(1 for w in works if is_truncated(w))
    out["share_links_trunc"] = (sum(1 for l in links if l.get("trunc")) / n) if n else float("nan")

    nauth = {w["id"]: max(1, n_authors(w)) for w in works}
    harm = {}
    for w in works:
        k = next((i + 1 for i, a in enumerate(w["authors"]) if a == focal), None)
        harm[w["id"]] = harmonic_share(k, nauth[w["id"]], len(w["authors"]))

    for name, wfn in DEFINITIONS.items():
        per_paper = {w["id"]: 0.0 for w in works}
        citing_ids = set()
        for l in links:
            v = wfn(l)
            if v > 0:
                per_paper[l["cited"]] += v
                citing_ids.add(l["citing"])
        cites = list(per_paper.values())
        out[f"{name}_cites"] = sum(cites)
        out[f"{name}_h"] = raw_h_index(cites)
        out[f"{name}_hm"] = hm_index((per_paper[i], nauth[i]) for i in per_paper)
        out[f"{name}_credit_equal"] = sum(per_paper[i] / nauth[i] for i in per_paper)
        out[f"{name}_credit_harmonic"] = sum(per_paper[i] * harm[i] for i in per_paper)
        if name in BINARY:
            out[f"{name}_citing_papers"] = len(citing_ids)
            out[f"{name}_cites_per_citing"] = (sum(cites) / len(citing_ids)) if citing_ids else float("nan")
    return out


def _citing_split(source, batch: list[str], years: tuple[int, int]) -> list[dict]:
    """Fetch citing works for a batch; halve the batch if OpenAlex rejects it as too long."""
    try:
        return source.citing_works(batch, years)
    except requests.HTTPError as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status not in (400, 414) or len(batch) < 2:
            raise
        mid = len(batch) // 2
        logger.warning("OpenAlex refused a %d-id cites: filter (HTTP %s); splitting it", len(batch), status)
        return _citing_split(source, batch[:mid], years) + _citing_split(source, batch[mid:], years)


def analyse_author(
    source,
    author_id: str,
    work_types: Optional[list[str]] = None,
    cite_years: tuple[int, int] = DEFAULT_CITE_YEARS,
    max_citations: int = DEFAULT_MAX_CITATIONS,
    batch_size: int = CITES_BATCH,
) -> tuple[dict, list[dict]]:
    """Fetch, classify and measure one researcher. Returns (metrics, links)."""
    aid = _short(author_id)
    works = source.author_works(aid, work_types)
    total = sum(w["cbc"] for w in works)
    if not works:
        return {"status": "no_works"}, []
    if total > max_citations:
        return {"status": f"skipped_over_{max_citations}_citations", "n_works": len(works), "cited_by_total": total}, []
    cited = [w["id"] for w in works if w["cbc"] > 0]
    citing: list[dict] = []
    for i in range(0, len(cited), batch_size):
        citing.extend(_citing_split(source, cited[i:i + batch_size], cite_years))
    links = classify_links(aid, works, citing)
    m = author_metrics(aid, works, links)
    m["status"] = "ok"
    m["cited_by_total"] = total
    return m, links


# ======================================================================
# Parallel execution
# ======================================================================


_NOT_STARTED = object()


def run_parallel(
    items: list,
    fn: Callable,
    workers: int = DEFAULT_WORKERS,
    on_result: Optional[Callable[[int, object], None]] = None,
    source: Optional[OpenAlexSource] = None,
    poll_sec: float = 1.0,
) -> tuple[dict, Optional[RunStopped]]:
    """Apply `fn` to every item, up to `workers` at a time.

    `on_result(index, value)` is called in the main thread as each item
    finishes. Once `fn` raises RunStopped (OpenAlex daily limit, or Ctrl+C),
    no new item is started and the items that were stopped are left out.
    Returns ({index: value}, the RunStopped that ended the run or None).
    Any other exception raised by `fn` is returned as that item's value.
    """
    stop = threading.Event()
    results: dict = {}
    stop_exc: Optional[RunStopped] = None

    def task(i, item):
        if stop.is_set():
            return i, _NOT_STARTED
        try:
            return i, fn(item)
        except RunStopped as exc:
            stop.set()
            return i, exc
        except Exception as exc:                                     # noqa: BLE001
            logger.error("item %d failed: %s", i, _redact(exc))
            logger.debug("traceback", exc_info=True)
            return i, exc

    ex = ThreadPoolExecutor(max_workers=max(1, int(workers)), thread_name_prefix="selfcite")
    try:
        pending = {ex.submit(task, i, it) for i, it in enumerate(items)}
        while pending:
            # Timed wait, so Ctrl+C is noticed promptly (also on Windows).
            done, pending = wait(pending, timeout=poll_sec, return_when=FIRST_COMPLETED)
            for f in done:
                i, val = f.result()
                if val is _NOT_STARTED:
                    continue
                if isinstance(val, RunStopped):
                    if stop_exc is None or (isinstance(val, QuotaExceeded) and not isinstance(stop_exc, QuotaExceeded)):
                        stop_exc = val
                    continue
                results[i] = val
                if on_result:
                    on_result(i, val)
    except KeyboardInterrupt:
        stop.set()
        if source is not None:
            source.stop()
        stop_exc = RunStopped("interrupted by the user")
        print("\nStopping: waiting for the requests in flight to end ...", flush=True)
    except BaseException:
        # e.g. an output file locked by Excel: stop the workers, then report the error
        stop.set()
        if source is not None:
            source.stop()
        raise
    finally:
        ex.shutdown(wait=True, cancel_futures=True)
    return results, stop_exc


# ======================================================================
# Name resolution (2026 list rows -> OpenAlex author ids)
# ======================================================================


def _norm_tokens(s: str) -> list[str]:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return [t for t in re.split(r"[^a-z]+", s) if t]


_STOP = {"of", "the", "and", "de", "la", "di", "del", "des", "university", "universidad", "universita",
         "universite", "universitat", "institute", "institut", "college", "school", "national", "technical"}


def score_candidate(cand: dict, surname: str, given: str, inst: str, n_papers: int, n_cites: int) -> float:
    names = [cand.get("display_name") or ""] + list(cand.get("display_name_alternatives") or [])
    sur = _norm_tokens(surname)
    giv = _norm_tokens(given)
    best_name = 0.0
    for nm in names:
        toks = _norm_tokens(nm)
        if not sur or not all(t in toks for t in sur):
            continue
        sc = 3.0
        rest = [t for t in toks if t not in sur]
        if giv and rest:
            if giv[0] in rest:
                sc += 2.0
            elif any(t[0] == giv[0][0] for t in rest):
                sc += 1.0
        best_name = max(best_name, sc)
    if best_name == 0.0:
        return 0.0
    score = best_name
    inst_t = {t for t in _norm_tokens(inst) if t not in _STOP and len(t) > 2}
    if inst_t:
        for ins in cand.get("last_known_institutions") or []:
            ct = {t for t in _norm_tokens(ins.get("display_name") or "") if t not in _STOP and len(t) > 2}
            if ct and len(inst_t & ct) / len(inst_t) >= 0.5:
                score += 2.0
                break
    wc = cand.get("works_count") or 0
    if n_papers > 0 and wc > 0:
        r = wc / n_papers
        score += 1.5 if 0.5 <= r <= 2 else (0.5 if 0.33 <= r <= 3 else -1.0)
    cc = cand.get("cited_by_count") or 0
    if n_cites > 0 and cc > 0:
        r = cc / n_cites
        score += 1.0 if 0.5 <= r <= 3 else (0.0 if 0.25 <= r <= 5 else -1.0)
    return score


def resolve_row(source, row: dict) -> dict:
    authfull = row.get("authfull", "")
    surname, _, given = authfull.partition(",")
    query = f"{given.strip()} {surname.strip()}".strip()
    cc2 = (row.get("cc2") or "").strip() or None
    n_papers = int(float(row.get("np6025") or 0))
    n_cites = int(float(row.get("nc9625") or 0))
    try:
        cands = source.search_authors(query, cc2)
    except requests.HTTPError:
        cands = []
    if not cands and cc2:
        cands = source.search_authors(query, None)
    scored = sorted(
        ((score_candidate(c, surname, given, row.get("inst_name", ""), n_papers, n_cites), c) for c in cands),
        key=lambda t: t[0], reverse=True,
    )
    scored = [t for t in scored if t[0] > 0]
    out = dict(row)
    if not scored:
        out.update(openalex_id="", match_name="", match_score=0, runner_up_score=0, match_flag="none", use="")
        return out
    best_s, best = scored[0]
    second_s = scored[1][0] if len(scored) > 1 else 0.0
    flag = "high" if best_s >= 6.5 and best_s - second_s >= 1.5 else "check"
    out.update(
        openalex_id=_short(best.get("id")),
        match_name=best.get("display_name", ""),
        match_works=best.get("works_count", ""),
        match_cites=best.get("cited_by_count", ""),
        match_score=round(best_s, 2),
        runner_up_score=round(second_s, 2),
        match_flag=flag,
        use="Y" if flag == "high" else "",
    )
    return out


# ======================================================================
# Group report
# ======================================================================


REPORT_FIELDS = [
    ("share_own", "Own"), ("share_coauthor", "Co-author"), ("share_network", "Network"),
    ("share_independent", "Independent"), ("self_rate_list_rule", "Self-citation rate, list rule"),
    ("coauthor_share_of_self", "Co-author share of self-citations"),
    ("median_team_size", "Median team size"), ("share_links_trunc", "Links touching a capped author list"),
]


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _median(vals):
    v = [x for x in vals if isinstance(x, (int, float)) and not math.isnan(x)]
    return statistics.median(v) if v else float("nan")


def _group_key(r: dict) -> tuple[str, str]:
    return (r.get("field") or "", r.get("group") or "")


GROUP_ORDER = ("Self-citation-only entrants", "High bundled citations", "Comparison group", "Random reference")


def _ordered(values: Iterable[str], preferred: tuple = ()) -> list[str]:
    """Distinct values: preferred ones first in that order, the rest by first appearance."""
    seen = list(dict.fromkeys(values))
    return [v for v in preferred if v in seen] + [v for v in seen if v not in preferred]


def group_report(rows: list[dict]) -> list[dict]:
    """Medians per group (per field and group, when a `field` column is present)."""
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        if r.get("status") == "ok":
            groups.setdefault(_group_key(r), []).append(r)
    with_field = any(k[0] for k in groups)
    f_rank = {f: i for i, f in enumerate(_ordered(k[0] for k in groups))}
    g_rank = {g: i for i, g in enumerate(_ordered((k[1] for k in groups), GROUP_ORDER))}
    out = []
    for (fld, g), rs in sorted(groups.items(), key=lambda kv: (f_rank[kv[0][0]], g_rank[kv[0][1]])):
        rec = ({"field": fld} if with_field else {}) | {"group": g, "n_researchers": len(rs)}
        for key, _ in REPORT_FIELDS:
            rec[f"median_{key}"] = _median([_f(r.get(key)) for r in rs])
        for metric in ("cites", "h", "hm"):
            for d in ("excl_own", "excl_shared", "excl_network", "frac_equal", "frac_harmonic", "frac_network"):
                rec[f"median_{d}_{metric}_vs_all"] = _median(
                    [_f(r[f"{d}_{metric}"]) / _f(r[f"all_{metric}"]) for r in rs if _f(r[f"all_{metric}"]) > 0]
                )
        for d in ("all", "excl_shared", "excl_network"):
            rec[f"median_{d}_cites_per_citing"] = _median([_f(r.get(f"{d}_cites_per_citing")) for r in rs])
        out.append(rec)
    return out


def plot_shares(rows: list[dict], path: Path) -> Optional[Path]:
    """Stacked horizontal bars of the four classes per researcher, one panel per group
    (a grid of fields by groups when a `field` column is present)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:                                                # noqa: BLE001
        logger.warning("matplotlib not available; skipping figure")
        return None
    ok = [r for r in rows if r.get("status") == "ok" and int(_f(r.get("n_links")) or 0) > 0]
    if not ok:
        return None
    fields = _ordered(r.get("field") or "" for r in ok)
    groups = _ordered((r.get("group") or "" for r in ok), GROUP_ORDER)
    colours = {"own": "#B5523B", "coauthor": "#E0A458", "network": "#5B8DB8", "independent": "#D9DDE3"}
    names = {"own": "Own", "coauthor": "Co-author", "network": "Collaborator network", "independent": "Independent"}
    nr, nc = len(fields), len(groups)
    fig, axes = plt.subplots(nr, nc, figsize=(3.6 * nc, 2.6 + 3.0 * nr if nr > 1 else 7),
                             squeeze=False, sharex=True)
    for ri, fld in enumerate(fields):
        for ci, g in enumerate(groups):
            ax = axes[ri][ci]
            rs = sorted([r for r in ok if (r.get("field") or "") == fld and (r.get("group") or "") == g],
                        key=lambda r: _f(r["share_independent"]))
            left = [0.0] * len(rs)
            for c in CLASSES:
                vals = [100 * _f(r[f"share_{c}"]) for r in rs]
                ax.barh(range(len(rs)), vals, left=left, color=colours[c], height=0.85, label=names[c])
                left = [a + b for a, b in zip(left, vals)]
            title = f"{g} (n={len(rs)})" if not fld else f"{fld}\n{g} (n={len(rs)})"
            ax.set_title(title, fontsize=9)
            ax.set_yticks([])
            ax.set_xlim(0, 100)
            if ri == nr - 1:
                ax.set_xlabel("% of citation links")
            for s in ("top", "right"):
                ax.spines[s].set_visible(False)
    handles, labels = axes[0][0].get_legend_handles_labels()
    height = fig.get_size_inches()[1]
    fig.suptitle("Where each researcher's citations come from", fontsize=11, y=1 - 0.15 / height, va="top")
    fig.legend(handles, labels, loc="upper center", ncol=4, fontsize=9, frameon=False,
               bbox_to_anchor=(0.5, 1 - 0.45 / height))
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.85 / height))
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


# ======================================================================
# CLI
# ======================================================================


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict], fields: Optional[list[str]] = None) -> None:
    if not rows:
        return
    if fields is None:
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    for attempt in range(5):
        try:
            tmp.replace(path)
            return
        except PermissionError:                      # Windows: the CSV is open in Excel
            time.sleep(1.0)
    raise PermissionError(f"Cannot write {path}: close it in Excel (or any other program) and run again.")


def _source(args) -> OpenAlexSource:
    return OpenAlexSource(mailto=args.mailto, cache_dir=args.cache_dir,
                          authors_count=not getattr(args, "no_authors_count", False))


def summary_row(author: dict, label: str, group: str, metrics: dict) -> dict:
    """One output row: label, group, the author's non-identifying columns, then the metrics."""
    row = {"label": label, "group": group}
    for k, v in author.items():
        if k and k not in PRIVATE_COLUMNS and k not in row:
            row[k] = v
    row.update({k: (round(v, 6) if isinstance(v, float) else v) for k, v in metrics.items()})
    return row


def _cmd_cohort(args) -> int:
    from .sample import sample_authors_stratified
    sampled = sample_authors_stratified(
        topic_id=args.topic,
        bands=[(5, 20), (21, 50), (51, 75), (76, 100), (101, 1000)],
        per_band=args.per_band,
        min_h_index=5,
        seed=args.seed,
        works_sample_size=500,
        mailto=args.mailto or os.environ.get("DPAC_MAILTO"),
    )
    rows = [{"label": f"OE-{i:03d}", "group": "Ocean-engineering cohort", "openalex_id": _short(a["openalex_id"]), "use": "Y"}
            for i, a in enumerate(sampled, 1)]
    _write_csv(Path(args.output), rows)
    print(f"Wrote {len(rows)} authors to {args.output}")
    return 0


def _cmd_resolve(args) -> int:
    src = _source(args)
    rows = _read_csv(Path(args.input))
    if args.limit:
        rows = rows[: args.limit]
    out: dict[int, dict] = {}
    t0 = time.monotonic()

    def one(r):
        return resolve_row(src, r)

    def done(i, res):
        if isinstance(res, Exception):
            res = dict(rows[i], openalex_id="", match_name="", match_score=0, runner_up_score=0,
                       match_flag=f"error: {_redact(res)}", use="")
        res.setdefault("label", f"{(rows[i].get('group_code') or 'C')}-{i + 1:03d}")
        out[i] = res
        print(f"[{len(out)}/{len(rows)}] {res['label']}: {res['match_flag']} (score {res['match_score']}) "
              f"| requests {src.n_requests} | {(time.monotonic() - t0) / 60:.1f} min", flush=True)

    _, stop_exc = run_parallel(rows, one, workers=args.workers, on_result=done, source=src)
    ordered = [out[i] for i in sorted(out)]
    _write_csv(Path(args.output), ordered)
    if isinstance(stop_exc, QuotaExceeded):
        print(f"\nStopped with {len(ordered)} of {len(rows)} rows resolved.\n{QUOTA_HELP}\nOpenAlex said: {stop_exc}")
    elif stop_exc is not None:
        print(f"\nStopped with {len(ordered)} of {len(rows)} rows resolved. Run the same command again to finish.")
    n_high = sum(1 for r in ordered if r["match_flag"] == "high")
    cells: dict[str, list[int]] = {}
    for r in ordered:
        cell = " ".join(x for x in (r.get("field_code"), r.get("group_code")) if x)
        if cell:
            c = cells.setdefault(cell, [0, 0])
            c[0] += r["match_flag"] == "high"
            c[1] += 1
    if len(cells) > 1:
        print("\nHigh-confidence matches per cell: " + ", ".join(f"{k} {v[0]}/{v[1]}" for k, v in cells.items()))
    print(f"\nResolved {n_high} of {len(ordered)} with high confidence (use=Y). "
          f"Rows marked 'check' are skipped unless you set use=Y after checking them. "
          f"Requests made: {src.n_requests} (name searches are billed at ten list requests each).")
    return 0 if stop_exc is None else 2


def _cmd_run(args) -> int:
    src = _source(args)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    authors: list[dict] = []
    seen_ids: dict[str, str] = {}
    for p in args.authors:
        for r in _read_csv(Path(p)):
            use = (r.get("use") if "use" in r else "Y") or ""
            oid = _short((r.get("openalex_id") or "").strip())
            if not oid or use.strip().upper() not in ("Y", "YES", "1", "TRUE"):
                continue
            if oid in seen_ids:
                print(f"Note: {r.get('label')} has the same OpenAlex id as {seen_ids[oid]}; kept only {seen_ids[oid]}.")
                continue
            seen_ids[oid] = r.get("label") or oid
            authors.append(dict(r, openalex_id=oid))
    if args.limit:
        authors = authors[: args.limit]
    years = tuple(int(x) for x in args.cite_years.split("-"))
    work_types = None if args.work_types == "all" else args.work_types.split(",")
    if not src.api_key:
        print("Note: no OPENALEX_API_KEY set; OpenAlex allows roughly 1,000 list requests a day without one.")
    print(f"{len(authors)} researchers, {args.workers} at a time.", flush=True)
    try:
        src.ensure_fields()
    except RunStopped as exc:
        print(f"\n{QUOTA_HELP}\nOpenAlex said: {exc}")
        return 2
    labels = [a.get("label") or f"R-{i:03d}" for i, a in enumerate(authors, 1)]
    done_rows: dict[int, tuple[dict, dict]] = {}
    t0 = time.monotonic()

    def one(i_a):
        i, a = i_a
        t, req0 = time.monotonic(), src.thread_requests()
        try:
            m, links = analyse_author(src, a["openalex_id"], work_types, years, args.max_citations)
        except RunStopped:
            raise
        except Exception as exc:                                     # noqa: BLE001
            logger.error("failed for %s: %s", labels[i], _redact(exc))
            logger.debug("traceback", exc_info=True)
            m, links = {"status": f"error: {_redact(exc)}"}, []
        return m, links, src.thread_requests() - req0, time.monotonic() - t

    def done(k, val):
        i, a = k, authors[k]
        m, links, nreq, secs = val
        label, group = labels[i], a.get("group") or ""
        done_rows[i] = (summary_row(a, label, group, m),
                        {"label": label, "group": group, "openalex_id": a["openalex_id"], "name": a.get("authfull", "")})
        if args.save_links and links:
            with gzip.open(outdir / f"links_{label}.csv.gz", "wt", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=list(links[0].keys()))
                w.writeheader()
                w.writerows(links)
        order = sorted(done_rows)
        _write_csv(outdir / "selfcite_summary.csv", [done_rows[j][0] for j in order])
        _write_csv(outdir / "selfcite_key_PRIVATE.csv", [done_rows[j][1] for j in order])
        where = " | ".join(x for x in (a.get("field"), group) if x)
        print(f"[{len(done_rows)}/{len(authors)}] {label} ({where}): {m.get('status')} | links {m.get('n_links', '-')} | "
              f"own {m.get('share_own', float('nan')):.0%} co {m.get('share_coauthor', float('nan')):.0%} "
              f"net {m.get('share_network', float('nan')):.0%} | {nreq} requests, {secs:.0f}s "
              f"(all: {src.n_requests} requests, {(time.monotonic() - t0) / 60:.1f} min)", flush=True)

    _, stop_exc = run_parallel(list(enumerate(authors)), one, workers=args.workers, on_result=done, source=src)
    n_done = len(done_rows)
    if isinstance(stop_exc, QuotaExceeded):
        print(f"\nStopped with {n_done} of {len(authors)} researchers done.\n{QUOTA_HELP}\nOpenAlex said: {stop_exc}")
    elif stop_exc is not None:
        print(f"\nStopped with {n_done} of {len(authors)} researchers done. Run the same command again to continue "
              f"(finished work is read from the cache).")
    _report(outdir, [done_rows[j][0] for j in sorted(done_rows)])
    return 0 if stop_exc is None else 2


def _report(outdir: Path, rows: list[dict]) -> None:
    rep = group_report(rows)
    if rep:
        _write_csv(outdir / "selfcite_groups.csv", [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rep])
    fig = plot_shares(rows, outdir / "selfcite_shares.png")
    n_ok = sum(1 for r in rows if r.get("status") == "ok")
    n_skip = sum(1 for r in rows if str(r.get("status", "")).startswith("skipped"))
    n_err = sum(1 for r in rows if str(r.get("status", "")).startswith("error"))
    print(f"\n{n_ok} completed, {n_skip} skipped as too large, {n_err} failed (a re-run retries failures).")
    print("\nGroup medians:")
    for r in rep:
        name = " | ".join(x for x in (r.get("field"), r["group"]) if x)
        print(f"  {name} (n={r['n_researchers']}): own {r['median_share_own']:.1%}, "
              f"co-author {r['median_share_coauthor']:.1%}, network {r['median_share_network']:.1%}, "
              f"independent {r['median_share_independent']:.1%}; h kept under list rule "
              f"{r['median_excl_shared_h_vs_all']:.0%}, also excluding network {r['median_excl_network_h_vs_all']:.0%}")
    print(f"\nOutputs in {outdir}: selfcite_summary.csv, selfcite_groups.csv"
          f"{', selfcite_shares.png' if fig else ''} (selfcite_key_PRIVATE.csv maps labels to people; do not share it).")


def _cmd_report(args) -> int:
    outdir = Path(args.output_dir)
    _report(outdir, _read_csv(outdir / "selfcite_summary.csv"))
    return 0


def _cmd_probe(args) -> int:
    """A few cheap list requests: key, page size, authors_count, today's allowance."""
    src = _source(args)
    src.max_retries = 2
    print(f"API key: {'set' if src.api_key else 'NOT set'} | mailto: {src.mailto or 'not set'} | cache: {src.cache_dir}")
    try:
        p = src._get("works", {"filter": "publication_year:2020,type:article", "select": "id", "per_page": PER_PAGE})
        print(f"page size: asked {PER_PAGE}, got {len(p.get('results') or [])}")
    except RunStopped as exc:
        print(f"OpenAlex refused the request: {exc}\n{QUOTA_HELP}")
        return 2
    except requests.HTTPError as exc:
        print(f"OpenAlex rejected the basic test request ({exc}). Keep this message and stop here.")
        return 1
    except (requests.ConnectionError, requests.Timeout) as exc:
        print(f"Cannot reach api.openalex.org ({type(exc).__name__}). Check the internet connection and try again.")
        return 1
    if src.authors_count:
        try:
            src._get("works", {"filter": "publication_year:2020", "select": "id,authors_count", "per_page": 1})
            line = "authors_count: available"
            try:
                p = src._get("works", {"filter": "authors_count:>500,publication_year:2020",
                                       "select": "id,authors_count,authorships", "per_page": 3})
                res = p.get("results") or []
                line += (f" | large-team example: listed authors {[len(r.get('authorships') or []) for r in res]}, "
                         f"true counts {[r.get('authors_count') for r in res]}")
            except requests.HTTPError:
                pass
            print(line)
        except requests.HTTPError:
            print("authors_count: not available. No action needed: the run flags 100-name author lists as capped instead.")
    h = {k.lower(): v for k, v in src.last_headers.items()}
    lim, rem, reset = h.get("x-ratelimit-limit"), h.get("x-ratelimit-remaining"), h.get("x-ratelimit-reset")
    if lim or rem:
        try:
            when = f"{float(reset) / 3600:.1f} h"
        except (TypeError, ValueError):
            when = str(reset)
        print(f"daily allowance: {rem} left of {lim} (resets in {when})")
    else:
        print("daily allowance: not reported in the response headers")
    print("Probe OK.")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m dpac.selfcite", description=__doc__.split("\n\n")[0])
    p.add_argument("--mailto", help="Contact email passed on as mailto (default: $DPAC_MAILTO; ignored by OpenAlex since 2026).")
    p.add_argument("--cache-dir", help="Cache directory (default: $DPAC_SELFCITE_CACHE or ~/.dpac_cache/selfcite).")
    p.add_argument("--no-authors-count", action="store_true",
                   help="Do not request authors_count (normally detected automatically).")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("probe", help="Check the API key, today's allowance and the fields the run needs.")
    pr.set_defaults(fn=_cmd_probe)

    c = sub.add_parser("cohort", help="Re-draw the ocean-engineering cohort of the preprint (section 5.2).")
    c.add_argument("--output", default="authors_cohort.csv")
    c.add_argument("--topic", default="ocean_engineering")
    c.add_argument("--per-band", type=int, default=20)
    c.add_argument("--seed", type=int, default=20260522)
    c.set_defaults(fn=_cmd_cohort)

    r = sub.add_parser("resolve", help="Match rows of the 2026 list to OpenAlex author ids.")
    r.add_argument("--input", required=True)
    r.add_argument("--output", default="authors_contrast.csv")
    r.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Rows resolved at the same time (default 4).")
    r.add_argument("--limit", type=int, default=0, help="Only the first N rows (for a quick test).")
    r.set_defaults(fn=_cmd_resolve)

    u = sub.add_parser("run", help="Decompose citations for every author in one or more author CSVs.")
    u.add_argument("--authors", nargs="+", required=True)
    u.add_argument("--output-dir", default="selfcite_out")
    u.add_argument("--cite-years", default=f"{DEFAULT_CITE_YEARS[0]}-{DEFAULT_CITE_YEARS[1]}")
    u.add_argument("--work-types", default=",".join(DEFAULT_WORK_TYPES), help="Comma list, or 'all'.")
    u.add_argument("--max-citations", type=int, default=DEFAULT_MAX_CITATIONS)
    u.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Researchers processed at the same time (default 4).")
    u.add_argument("--limit", type=int, default=0, help="Only the first N authors (for a quick test).")
    u.add_argument("--save-links", action="store_true", help="Also write every classified link (large).")
    u.set_defaults(fn=_cmd_run)

    g = sub.add_parser("report", help="Rebuild the group table and figure from an existing run.")
    g.add_argument("--output-dir", default="selfcite_out")
    g.set_defaults(fn=_cmd_report)

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")
    logging.getLogger("urllib3").setLevel(logging.INFO)      # its DEBUG lines carry full URLs, with the key
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
