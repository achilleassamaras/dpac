"""
OpenAlex API client with on-disk caching and polite throttling.

Queries are made by ORCID; results are normalised into the internal Work record
used elsewhere in the package.

The OpenAlex polite-pool convention asks API users to identify themselves by
mailto. Set the environment variable DPAC_MAILTO (or pass `mailto=` to the
client) to participate. Requests without a mailto fall back to the public pool.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable, Optional

import requests

logger = logging.getLogger(__name__)

OPENALEX_BASE = "https://api.openalex.org"
DEFAULT_PER_PAGE = 200          # OpenAlex max
DEFAULT_THROTTLE_SEC = 0.1      # polite gap between requests
DEFAULT_CACHE_DIR = Path.home() / ".dpac_cache"
DEFAULT_USER_AGENT = "dpac/1.0 (https://github.com/achilleassamaras/dpac)"


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

    def to_dict(self) -> dict:
        return asdict(self)


class OpenAlexClient:
    """Polite, cached OpenAlex client.

    Parameters
    ----------
    mailto : str, optional
        Contact email for the OpenAlex polite pool. Falls back to
        $DPAC_MAILTO; if neither is set the public pool is used.
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
    ) -> None:
        self.mailto = mailto or os.environ.get("DPAC_MAILTO")
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
        logger.debug("GET %s params=%s", url, params)
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        self._last_request_t = time.monotonic()
        resp.raise_for_status()
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
                "per-page": DEFAULT_PER_PAGE,
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
) -> list[Work]:
    """Return a list of normalised Work records for the given ORCID.

    Convenience wrapper around OpenAlexClient. Use the class directly for
    finer control over caching and throttling.

    Pass `work_types=['article']` to restrict to journal articles.
    """
    client = OpenAlexClient(mailto=mailto, cache_dir=cache_dir)
    raw_works = client.fetch_works_by_orcid(
        orcid, use_cache=use_cache, work_types=work_types
    )
    return [w for w in (_normalise_work(rw, orcid) for rw in raw_works) if w is not None]


def _normalise_work(raw: dict, focal_orcid: str,
                    min_year: int = 1980) -> Optional[Work]:
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
    """
    focal_orcid = _normalise_orcid(focal_orcid)
    authorships = raw.get("authorships", []) or []
    n_authors = len(authorships)
    if n_authors == 0:
        return None

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
        focal_position_value, focal_idx, n_authors
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
