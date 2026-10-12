"""
OpenAlex API client with on-disk caching and polite throttling.

Queries are made by ORCID; results are normalised into the internal Work record
used elsewhere in the package.

API key. OpenAlex meters usage per day and identifies users by API key (free
at openalex.org/settings/api); without one, the daily allowance is small. Set
the environment variable OPENALEX_API_KEY (or pass `api_key=` to the client).
The key is sent as the `api_key` query parameter and is never printed: it is
masked in log messages and in error messages.

mailto. OpenAlex replaced its polite pool with API keys in 2026 and now
ignores the `mailto` parameter. DPAC_MAILTO and `mailto=` are still accepted
and passed on, so existing scripts keep working.

Author lists. OpenAlex lists at most the first 100 authors of a work. When
the true count is not returned (`authors_count`), a list of exactly 100 names
is flagged as capped (`Work.authors_capped`): its true size is unknown, so the
equal and harmonic shares computed from it are approximate (upper bounds).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Optional

import requests

logger = logging.getLogger(__name__)

OPENALEX_BASE = "https://api.openalex.org"
DEFAULT_PER_PAGE = 100          # OpenAlex maximum page size (`per_page`, 1-100)
DEFAULT_THROTTLE_SEC = 0.1      # polite gap between requests
DEFAULT_CACHE_DIR = Path.home() / ".dpac_cache"
DEFAULT_USER_AGENT = "dpac/1.1 (https://github.com/achilleassamaras/dpac)"
AUTHORSHIP_CAP = 100            # OpenAlex lists at most the first 100 authors of a work
API_KEY_ENV = "OPENALEX_API_KEY"
DEFAULT_MIN_YEAR = 1980         # works dated earlier (or undated) are dropped

_KEY_RE = re.compile(r"(api_key=)[^&\s'\"]+")


def redact_api_key(text, api_key: Optional[str] = None) -> str:
    """Mask the API key in a URL or message.

    `api_key=<value>` becomes `api_key=***`; when the key itself is given,
    any other occurrence of it is masked too.
    """
    out = _KEY_RE.sub(r"\1***", str(text))
    if api_key:
        out = out.replace(api_key, "***")
    return out


def mask_request_error(exc: Exception, api_key: Optional[str] = None) -> Exception:
    """A copy of a `requests` exception with the API key masked in its message.

    Connection errors and timeouts carry the request URL, which contains the
    key; the copy keeps the exception type (so callers can still catch and
    retry it) and the response, but not the URL. Raise it `from None`.
    """
    msg = redact_api_key(str(exc), api_key or os.environ.get(API_KEY_ENV))
    try:
        return type(exc)(msg, response=getattr(exc, "response", None))
    except TypeError:
        return requests.RequestException(msg)


def _safe_params(params: dict) -> dict:
    """Request parameters as they may be logged: the API key masked."""
    return {k: ("***" if k == "api_key" else v) for k, v in params.items()}


def raise_for_status_redacted(resp, path: str, api_key: Optional[str] = None) -> None:
    """Raise requests.HTTPError for a 4xx/5xx response, without the API key.

    The message carries the status, the endpoint and OpenAlex's own error
    message (e.g. why a request was rejected), but never the request URL,
    which would contain the key.
    """
    status = getattr(resp, "status_code", 200)
    if status < 400:
        return
    detail = ""
    try:
        body = resp.json() or {}
        if isinstance(body, dict):
            detail = str(body.get("message") or body.get("error") or "")
    except Exception:                                           # noqa: BLE001
        detail = str(getattr(resp, "text", "") or "")[:300]
    msg = f"HTTP {status} on /{path.lstrip('/')}" + (f": {detail}" if detail else "")
    raise requests.HTTPError(redact_api_key(msg, api_key), response=resp)


@dataclass
class Work:
    """Normalised internal record for one publication.

    Carries only the fields that the metric machinery uses, plus the raw
    OpenAlex id for traceability.
    """

    openalex_id: str
    doi: Optional[str]
    title: str
    publication_year: int
    cited_by_count: int
    n_authors: int
    focal_position: int             # 1-indexed byline rank from authorships array
    focal_position_known: bool      # True when byline-order resolution succeeded
    issn_l: Optional[str] = None
    extra_metrics: dict = field(default_factory=dict)
    authors_capped: bool = False    # list cut at 100 names, true author count unknown

    def to_dict(self) -> dict:
        return asdict(self)


class OpenAlexClient:
    """Polite, cached OpenAlex client.

    Parameters
    ----------
    mailto : str, optional
        Contact email, passed on as `mailto` (ignored by OpenAlex since its
        2026 switch to API keys; kept for compatibility). Falls back to
        $DPAC_MAILTO.
    api_key : str, optional
        OpenAlex API key. Falls back to $OPENALEX_API_KEY. Optional, but
        without a key OpenAlex allows only a small number of requests a day.
        The key is never logged or included in error messages.
    cache_dir : str or Path, optional
        Directory for cached JSON responses. Default is ~/.dpac_cache.
    throttle_sec : float, optional
        Minimum gap (seconds) between successive HTTP requests.
    user_agent : str, optional
        User-Agent header. The default identifies the package.
    """

    def __init__(
        self,
        mailto: Optional[str] = None,
        cache_dir: Optional[Path] = None,
        throttle_sec: float = DEFAULT_THROTTLE_SEC,
        user_agent: str = DEFAULT_USER_AGENT,
        api_key: Optional[str] = None,
    ) -> None:
        self.mailto = mailto or os.environ.get("DPAC_MAILTO")
        self.api_key = api_key or os.environ.get(API_KEY_ENV) or None
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.throttle_sec = throttle_sec
        self.user_agent = user_agent
        self._last_request_t = 0.0

    # ----- caching -----

    def _cache_path(self, key: str) -> Path:
        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _cache_read(self, key: str) -> Optional[dict]:
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:                                # noqa: BLE001
            logger.warning("cache read failed for %s: %s", key, exc)
            return None

    def _cache_write(self, key: str, payload: dict) -> None:
        path = self._cache_path(key)
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    # ----- HTTP -----

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_t
        if elapsed < self.throttle_sec:
            time.sleep(self.throttle_sec - elapsed)

    def _get(self, url: str, params: dict) -> dict:
        self._throttle()
        headers = {"User-Agent": self.user_agent}
        if self.mailto:
            params = {**params, "mailto": self.mailto}
        if self.api_key:
            params = {**params, "api_key": self.api_key}
        logger.debug("GET %s params=%s", url, _safe_params(params))
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
        except requests.RequestException as exc:
            raise mask_request_error(exc, self.api_key) from None
        finally:
            self._last_request_t = time.monotonic()
        raise_for_status_redacted(resp, url.replace(OPENALEX_BASE, ""), self.api_key)
        return resp.json()

    # ----- public -----

    def fetch_works_by_orcid(
        self,
        orcid: str,
        use_cache: bool = True,
        work_types: Optional[list[str]] = None,
    ) -> list[dict]:
        """Return the raw OpenAlex works list for a given ORCID.

        Pagination is handled transparently; the full record is returned as
        a single list. The combined list is cached on disk.

        Parameters
        ----------
        orcid : str
            Canonical ORCID.
        use_cache : bool
            Read from on-disk cache if available.
        work_types : list of str, optional
            If supplied, restrict to these OpenAlex work types (e.g.
            ['article'] for journal articles only). When None, all types
            are returned. The cache key includes the work_types so that
            different filters do not collide on disk.
        """
        orcid = _normalise_orcid(orcid)
        types_tag = "all" if not work_types else "+".join(sorted(work_types))
        cache_key = f"works_by_orcid::{orcid}::types={types_tag}"
        if use_cache:
            cached = self._cache_read(cache_key)
            if cached is not None:
                logger.info("cache hit for %s (%d works)", orcid, len(cached))
                return cached

        # Build filter expression.
        filter_parts = [f"author.orcid:{orcid}"]
        if work_types:
            filter_parts.append(f"type:{'|'.join(work_types)}")
        filter_expr = ",".join(filter_parts)

        all_results: list[dict] = []
        cursor = "*"
        while cursor:
            params = {
                "filter": filter_expr,
                "per_page": DEFAULT_PER_PAGE,
                "cursor": cursor,
            }
            payload = self._get(f"{OPENALEX_BASE}/works", params)
            all_results.extend(payload.get("results", []))
            cursor = payload.get("meta", {}).get("next_cursor")
            if not cursor:
                break

        self._cache_write(cache_key, all_results)
        logger.info("fetched %d works for %s", len(all_results), orcid)
        return all_results


def _normalise_orcid(orcid: str) -> str:
    """Strip URL prefix and whitespace; return canonical NNNN-NNNN-NNNN-NNNN."""
    s = orcid.strip()
    for prefix in ("https://orcid.org/", "http://orcid.org/", "orcid.org/"):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    return s


def fetch_orcid_works(
    orcid: str,
    mailto: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    use_cache: bool = True,
    work_types: Optional[list[str]] = None,
    api_key: Optional[str] = None,
) -> list[Work]:
    """Return a list of normalised Work records for the given ORCID.

    Convenience wrapper around OpenAlexClient. Use the class directly for
    finer control over caching and throttling.

    Pass `work_types=['article']` to restrict to journal articles.

    Works whose author list OpenAlex cut at 100 names, with the true count
    unknown, are kept and flagged (`authors_capped`); a warning gives their
    number. Works on which the focal author is not among the listed names
    cannot be matched by ORCID and are skipped; when that happens on a cut
    list, a warning gives the number too.
    """
    client = OpenAlexClient(mailto=mailto, cache_dir=cache_dir, api_key=api_key)
    raw_works = client.fetch_works_by_orcid(
        orcid, use_cache=use_cache, work_types=work_types
    )
    works: list[Work] = []
    n_beyond_cap = 0
    for rw in raw_works:
        w = _normalise_work(rw, orcid)
        if w is not None:
            works.append(w)
        elif _list_cut(rw) and int(rw.get("publication_year") or 0) >= DEFAULT_MIN_YEAR:
            n_beyond_cap += 1
    n_capped = sum(1 for w in works if w.authors_capped)
    if n_capped:
        logger.warning(
            "%d of %d works list %d authors, the most OpenAlex returns: their true "
            "author count is unknown, so equal and harmonic shares on them are "
            "approximate (upper bounds).", n_capped, len(works), AUTHORSHIP_CAP,
        )
    if n_beyond_cap:
        logger.warning(
            "%d works skipped: the focal author is not among the %d authors that "
            "OpenAlex lists for them.", n_beyond_cap, AUTHORSHIP_CAP,
        )
    return works


def _authors_count(raw: dict) -> Optional[int]:
    """The true author count when OpenAlex returns it (`authors_count`), else None."""
    count = raw.get("authors_count")
    if isinstance(count, int) and not isinstance(count, bool):
        return count
    return None


def _list_cut(raw: dict) -> bool:
    """True when OpenAlex cut the work's author list at AUTHORSHIP_CAP names.

    With `authors_count` in the record, the list is cut when the count
    exceeds the listed names. Without it (the 2026 API no longer returns
    it), a list of exactly AUTHORSHIP_CAP names is treated as cut.
    """
    listed = len(raw.get("authorships") or [])
    count = _authors_count(raw)
    if count is not None:
        return count > listed
    return listed >= AUTHORSHIP_CAP


def _normalise_work(raw: dict, focal_orcid: str,
                    min_year: int = DEFAULT_MIN_YEAR) -> Optional[Work]:
    """Project a raw OpenAlex Work into the package's internal Work record.

    The focal author is matched against authorships[].author.orcid; works
    where the ORCID is not present on the author list are skipped. Works
    with `publication_year < min_year` are also skipped, to drop records
    with missing or implausibly early publication years (a common data-
    quality issue on older indexed material in OpenAlex).

    Position mapping. The focal author's byline rank is read directly from
    the order of the `authorships` array on the OpenAlex Work record: the
    first matching entry is rank 1, the second is rank 2, and so on.
    OpenAlex preserves the published byline order in this array. The
    categorical `author_position` field (`first`/`middle`/`last`) is read
    as a consistency check only and does not enter the numerical share
    computation. `focal_position_known` is True under this resolution.

    Author count. OpenAlex lists at most the first AUTHORSHIP_CAP (100)
    authors. When the record carries `authors_count`, `n_authors` is the
    true count. When it does not and exactly 100 names are listed, the true
    count is unknown: `n_authors` is 100 (a lower bound) and
    `authors_capped` is True, so the equal and harmonic shares on that work
    are upper bounds.
    """
    focal_orcid = _normalise_orcid(focal_orcid)
    authorships = raw.get("authorships", []) or []
    n_listed = len(authorships)
    if n_listed == 0:
        return None
    count = _authors_count(raw)
    # True author count when OpenAlex gives it; otherwise the listed names,
    # which is a lower bound for a list cut at AUTHORSHIP_CAP (flagged below).
    n_authors = count if (count is not None and count > n_listed) else n_listed
    capped = count is None and n_listed >= AUTHORSHIP_CAP

    pub_year = int(raw.get("publication_year") or 0)
    if pub_year < min_year:
        return None

    focal_idx = None
    focal_position_value = None
    for idx, ap in enumerate(authorships):
        author_block = ap.get("author") or {}
        orcid_url = author_block.get("orcid") or ""
        if _normalise_orcid(orcid_url) == focal_orcid:
            focal_idx = idx
            focal_position_value = ap.get("author_position")
            break

    if focal_idx is None:
        return None

    focal_position, focal_known = _position_to_index(
        focal_position_value, focal_idx, n_listed
    )

    host_venue = raw.get("primary_location", {}) or {}
    source = host_venue.get("source") or {}
    issn_l = source.get("issn_l")

    return Work(
        openalex_id=raw.get("id", ""),
        doi=raw.get("doi"),
        title=raw.get("title") or raw.get("display_name") or "",
        publication_year=pub_year,
        cited_by_count=int(raw.get("cited_by_count") or 0),
        n_authors=n_authors,
        focal_position=focal_position,
        focal_position_known=focal_known,
        issn_l=issn_l,
        authors_capped=capped,
    )


def _position_to_index(
    position_value: Optional[str], focal_idx: int, n_authors: int
) -> tuple[int, bool]:
    """Map the focal author's byline rank from the `authorships` array index.

    The byline rank is `focal_idx + 1`, since `focal_idx` is the 0-indexed
    position of the focal author in the OpenAlex `authorships` array and
    OpenAlex preserves the published byline order in that array.

    The categorical `author_position` field is read only as a light
    consistency check: when it disagrees with the array-derived rank
    (`first` not at index 0, or `last` not at index n-1), a debug log
    entry is emitted and the array-derived rank is used regardless.

    Returns (position, known). `known` is True for every successful code
    path; an out-of-range index degrades to False.
    """
    if focal_idx < 0 or focal_idx >= n_authors:
        # Defensive: an out-of-range index should not occur after the
        # authorships enumeration, but degrade gracefully if it does.
        return max(1, n_authors), False

    position = focal_idx + 1

    # Consistency check against the categorical field.
    if position_value == "first" and focal_idx != 0:
        logger.debug(
            "byline-order mismatch: author_position='first' but "
            "authorships index=%d (n_authors=%d); using array-derived "
            "rank %d.", focal_idx, n_authors, position,
        )
    elif position_value == "last" and focal_idx != n_authors - 1:
        logger.debug(
            "byline-order mismatch: author_position='last' but "
            "authorships index=%d (n_authors=%d); using array-derived "
            "rank %d.", focal_idx, n_authors, position,
        )

    return position, True
