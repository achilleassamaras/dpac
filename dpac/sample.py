"""
Random sampling of authors from OpenAlex with field and activity filters.

Used by the demonstration notebook to draw an anonymised cohort of authors
for empirical exercise of the two-tier metric computation, without manual
ORCID selection.

Strategy. OpenAlex deprecated x_concepts on the /authors endpoint, and the
replacement topics filter is not available there either. The working path
is to sample WORKS in a chosen topic, harvest the authors of those works
who have an ORCID, and then look those authors up on the /authors endpoint
to apply the activity thresholds. The two-stage path is slightly slower
than a single /authors query but is the documented way to constrain a
sample by research field as of 2026.

The sampling pool is constrained by:

- a topic id (field constraint, applied at the /works stage)
- has_orcid: true at the /works stage and at the /authors stage
- works_count > a configurable minimum (applied at the /authors stage)
- optionally, an h-index minimum (applied at the /authors stage)

Requests use OpenAlex's maximum page size of 100 and send the API key from
$OPENALEX_API_KEY (or `api_key=`) when one is set; the key never appears in
log or error messages.
"""

from __future__ import annotations

import logging
import math
import os
from typing import Optional

import requests

from .openalex import (
    API_KEY_ENV,
    DEFAULT_PER_PAGE,
    DEFAULT_THROTTLE_SEC,
    DEFAULT_USER_AGENT,
    OPENALEX_BASE,
    _normalise_orcid,
    _safe_params,
    mask_request_error,
    raise_for_status_redacted,
)

logger = logging.getLogger(__name__)


# Manually-curated OpenAlex TOPIC ids relevant to the project. Topics
# replace the deprecated concepts taxonomy. New topics can be looked up at
# https://api.openalex.org/topics?search=<term>.

TOPICS = {
    # Verified against OpenAlex /topics endpoint, May 2026.
    # Lookup: https://api.openalex.org/topics?search=<term>
    "ocean_waves":               "T11061",   # Ocean Waves and Remote Sensing (63,887 works)
    "coastal_engineering":       "T11061",   # alias — closest match for the AGS domain
    "wave_energy":               "T11250",   # Wave and Wind Energy Systems (42,658 works)
    "ocean_engineering":         "T11250",   # alias
    "hydraulic_engineering":     "T12022",   # Hydraulic flow and structures (56,013 works)
    "oceanography":              "T10255",   # Oceanographic and Atmospheric Processes (243,548 works)
    "underwater_vehicles":       "T11192",   # Underwater Vehicles and Communication Systems
}


def _resolve_topic(topic: Optional[str]) -> Optional[str]:
    """Map a friendly key to a topic id, or pass through a raw T... id."""
    if topic is None:
        return None
    if topic in TOPICS:
        return TOPICS[topic]
    if topic.startswith("T") and topic[1:].isdigit():
        return topic
    raise ValueError(
        f"Unknown topic {topic!r}. Use a key from dpac.TOPICS "
        f"({sorted(TOPICS)}) or pass a raw OpenAlex topic id like 'T10171'. "
        f"Look up topic ids at https://api.openalex.org/topics?search=<term>."
    )


def _request_json(url: str, params: dict, mailto: Optional[str],
                  user_agent: str, api_key: Optional[str] = None) -> dict:
    if mailto or os.environ.get("DPAC_MAILTO"):
        params = {**params, "mailto": mailto or os.environ.get("DPAC_MAILTO")}
    key = api_key or os.environ.get(API_KEY_ENV)
    if key:
        params = {**params, "api_key": key}
    headers = {"User-Agent": user_agent}
    logger.debug("GET %s params=%s", url, _safe_params(params))
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=30)
    except requests.RequestException as exc:
        raise mask_request_error(exc, key) from None
    raise_for_status_redacted(resp, url.replace(OPENALEX_BASE, ""), key)
    return resp.json()


def _harvest_orcid_authors_from_topic(
    topic: str,
    works_sample_size: int,
    seed: int,
    mailto: Optional[str],
    user_agent: str,
    api_key: Optional[str] = None,
) -> dict[str, str]:
    """Sample works in a topic; harvest unique ORCID-bearing authors.

    Returns dict: {author_openalex_id -> orcid_canonical}. Used as the
    common candidate-pool builder for both flat and stratified sampling.
    """
    per_page = min(works_sample_size, DEFAULT_PER_PAGE)   # OpenAlex maximum: 100
    works_params = {
        "filter": f"topics.id:{topic},has_orcid:true",
        "sample": works_sample_size,
        "seed": seed,
        "select": "id,authorships",
        "per_page": per_page,
    }
    logger.info("Sampling %d works in topic %s ...", works_sample_size, topic)
    payload = _request_json(
        f"{OPENALEX_BASE}/works", works_params, mailto, user_agent, api_key
    )
    works = payload.get("results", [])
    if not works:
        logger.warning("No works returned for topic %s", topic)
        return {}

    # If the sample is larger than one page, fetch subsequent pages.
    # OpenAlex `sample` returns up to `sample` items, paginated via `page`.
    max_pages = math.ceil(works_sample_size / per_page)
    page = 2
    while len(works) < works_sample_size and page <= max_pages:
        more_params = {**works_params, "page": page}
        more = _request_json(
            f"{OPENALEX_BASE}/works", more_params, mailto, user_agent, api_key
        )
        batch = more.get("results", [])
        if not batch:
            break
        works.extend(batch)
        page += 1

    seen: dict[str, str] = {}
    for w in works:
        for ap in (w.get("authorships") or []):
            author = ap.get("author") or {}
            aid = author.get("id")
            orcid_url = author.get("orcid")
            if not aid or not orcid_url:
                continue
            if aid not in seen:
                seen[aid] = _normalise_orcid(orcid_url)
    return seen


def _lookup_author_records(
    author_ids: list[str],
    min_works: int,
    min_h_index: int,
    mailto: Optional[str],
    user_agent: str,
    batch_size: int = 40,
    api_key: Optional[str] = None,
) -> list[dict]:
    """Look up a list of author OpenAlex IDs on /authors.

    Returns a list of dicts with keys `orcid`, `openalex_id`, `works_count`,
    `h_index`. Authors missing an ORCID or below the activity floors are
    dropped. The per-author order matches the input order within each batch
    (OpenAlex preserves input order for ID-list filters).
    """
    out: list[dict] = []
    for start in range(0, len(author_ids), batch_size):
        batch = author_ids[start: start + batch_size]
        id_filter = "|".join(a.replace("https://openalex.org/", "")
                             for a in batch)
        a_filter_parts = [f"openalex:{id_filter}",
                          f"works_count:>{min_works}"]
        if min_h_index > 0:
            a_filter_parts.append(f"summary_stats.h_index:>{min_h_index}")
        params = {
            "filter": ",".join(a_filter_parts),
            "select": "id,orcid,works_count,summary_stats",
            "per_page": batch_size,
        }
        payload = _request_json(
            f"{OPENALEX_BASE}/authors", params, mailto, user_agent, api_key
        )
        for r in payload.get("results", []):
            orcid_url = r.get("orcid")
            if not orcid_url:
                continue
            out.append({
                "orcid": _normalise_orcid(orcid_url),
                "openalex_id": r.get("id", ""),
                "works_count": int(r.get("works_count") or 0),
                "h_index": int(
                    (r.get("summary_stats") or {}).get("h_index") or 0
                ),
            })
    return out


def sample_authors(
    topic_id: Optional[str] = None,
    concept_id: Optional[str] = None,
    n: int = 10,
    min_works: int = 20,
    min_h_index: int = 5,
    seed: int = 20260522,
    mailto: Optional[str] = None,
    user_agent: str = DEFAULT_USER_AGENT,
    throttle_sec: float = DEFAULT_THROTTLE_SEC,
    works_sample_size: int = 200,
    api_key: Optional[str] = None,
) -> list[dict]:
    """Return a list of randomly sampled authors meeting the given filters.

    Procedure:
      1. Sample `works_sample_size` works within the chosen topic, with the
         filter has_orcid:true.
      2. Harvest every ORCID-bearing author from those works into a pool.
      3. Look those authors up on /authors with the activity filters.
      4. Return the first `n` authors that pass.

    Notes
    -----
    Because the pool is built from sampled works, prolific authors are
    over-represented (they appear on more works in any random sample). For
    a cohort that spans the activity spectrum, prefer
    `sample_authors_stratified`.
    """
    if topic_id is None and concept_id is not None:
        topic_id = concept_id
    topic = _resolve_topic(topic_id)
    if topic is None:
        raise ValueError(
            "A topic_id is required. Pass a key from dpac.TOPICS "
            f"({sorted(TOPICS)}) or a raw OpenAlex topic id like 'T10171'."
        )

    seen = _harvest_orcid_authors_from_topic(
        topic, works_sample_size, seed, mailto, user_agent, api_key
    )
    if not seen:
        return []

    candidates = _lookup_author_records(
        list(seen), min_works, min_h_index, mailto, user_agent,
        api_key=api_key,
    )
    if len(candidates) < n:
        logger.warning(
            "Requested %d authors but only %d passed the activity filters. "
            "Try lowering min_works/min_h_index, or increase works_sample_size.",
            n, len(candidates)
        )
    return candidates[:n]


def sample_authors_stratified(
    topic_id: Optional[str] = None,
    bands: Optional[list[tuple[int, int]]] = None,
    per_band: int = 20,
    min_h_index: int = 5,
    seed: int = 20260522,
    mailto: Optional[str] = None,
    user_agent: str = DEFAULT_USER_AGENT,
    works_sample_size: int = 500,
    api_key: Optional[str] = None,
) -> list[dict]:
    """Stratified random sample of authors across activity bands.

    The author pool is built by the same topic-via-works path as
    `sample_authors`; the difference is that authors are then slotted into
    `works_count` bands, and `per_band` authors are drawn from each band.
    The result is a cohort that spans the activity spectrum rather than
    being dominated by prolific authors (who appear on more sampled works
    by construction).

    Default configuration reproduces the empirical cohort of the preprint:
    five contiguous works_count bands spanning 5 to 1000, 20 authors per
    band (100 total), and an h-index floor of 5. The bands are
    inclusive-inclusive `[lo, hi]` and contiguous: 5--20, 21--50, 51--75,
    76--100, 101--1000. Every integer works_count in the covered range
    lands in exactly one band.

    Parameters
    ----------
    topic_id : str
        OpenAlex topic id or a key from `TOPICS`.
    bands : list of (lo, hi) tuples, optional
        Inclusive-inclusive works_count bands. Default:
        [(5, 20), (21, 50), (51, 75), (76, 100), (101, 1000)].
    per_band : int
        Number of authors to draw from each band. Total cohort size is
        `per_band * len(bands)`. Defaults to 20, giving a 100-researcher
        cohort across the five default bands.
    min_h_index : int
        h-index floor applied at the /authors lookup step. The OpenAlex
        filter is strict (`summary_stats.h_index:>{min_h_index}`), so the
        default of 5 selects authors with h-index of 6 or above.
    seed : int
        Reproducibility seed.
    mailto, user_agent : str, optional
        Passed to the underlying API calls.
    api_key : str, optional
        OpenAlex API key; defaults to $OPENALEX_API_KEY.
    works_sample_size : int
        Pool size at the works stage. Default 500. Larger values give a
        better chance of filling every band; smaller values are faster.

    Returns
    -------
    list of dict
        One dict per author, in band order. Empty bands produce nothing
        (with a warning). Keys: `orcid`, `openalex_id`, `works_count`,
        `h_index`, `band` (the (lo, hi) tuple the author was slotted into).
    """
    topic = _resolve_topic(topic_id)
    if topic is None:
        raise ValueError("A topic_id is required.")
    if bands is None:
        bands = [(5, 20), (21, 50), (51, 75), (76, 100), (101, 1000)]

    seen = _harvest_orcid_authors_from_topic(
        topic, works_sample_size, seed, mailto, user_agent, api_key
    )
    if not seen:
        return []
    logger.info("Harvested %d unique ORCID-bearing authors.", len(seen))

    # Look up the entire harvested pool with a low works floor (so we can
    # see authors across all bands, including the low end).
    band_floor = min(b[0] for b in bands)
    candidates = _lookup_author_records(
        list(seen), band_floor - 1, min_h_index, mailto, user_agent,
        api_key=api_key,
    )

    # Slot candidates into bands.
    import random
    rng = random.Random(seed)
    by_band: dict[tuple[int, int], list[dict]] = {b: [] for b in bands}
    for c in candidates:
        wc = c["works_count"]
        for band in bands:
            lo, hi = band
            if lo <= wc <= hi:
                by_band[band].append(c)
                break

    # Draw per_band from each, randomly within the band.
    out: list[dict] = []
    for band in bands:
        pool = by_band[band]
        if len(pool) < per_band:
            logger.warning(
                "Band %s has only %d candidates (asked for %d). "
                "Returning all %d; consider increasing works_sample_size.",
                band, len(pool), per_band, len(pool),
            )
            chosen = pool
        else:
            chosen = rng.sample(pool, per_band)
        for c in chosen:
            c["band"] = band
            out.append(c)

    return out


# Backward compatibility for older notebooks.
CONCEPTS = TOPICS
