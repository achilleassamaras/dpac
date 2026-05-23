"""
Imputation schemes producing per-paper, per-author contribution shares.

Each scheme produces a share c_i,p in [0, 1] satisfying sum_i c_i,p = 1
across the author list of paper p. For a focal author, the package only
needs the focal author's own share; the schemes below return that single
scalar given the paper's author count `n_authors` and the focal author's
1-indexed byline rank `focal_position`.

Three schemes are implemented:

- equal_share: 1/n. Independent of byline position.
- harmonic_share: (1/k) / H_n with H_n the n-th harmonic number;
  the Hodge & Greenberg (1981) / Hagen (2008, 2010) scheme. The
  byline rank k is read from the order of the `authorships` array on
  the OpenAlex Work record (see `openalex._normalise_work`), i.e.
  true byline order.
- declared_share: passthrough for user-supplied declared shares.

The harmonic scheme presumes a contribution-ordered byline convention:
authors are listed in decreasing order of contribution. That convention
holds in much of chemistry, biology, medicine, psychology, and the
engineering disciplines; it does not hold in fields that use
alphabetical or otherwise non-contribution-ordered listings
(mathematics, parts of economics, high-energy physics consortia). The
field-byline match is the user's to apply when interpreting results.
"""

from __future__ import annotations

from typing import Optional

from .openalex import Work


# ----- individual schemes -----


def equal_share(work: Work) -> float:
    """Return 1/n for the paper, irrespective of byline position."""
    if work.n_authors <= 0:
        return 0.0
    return 1.0 / work.n_authors


def harmonic_share(work: Work) -> float:
    """Return the harmonic-counting share for the focal author.

    c_k = (1/k) / H_n with H_n = 1 + 1/2 + ... + 1/n and k the focal
    author's 1-indexed byline rank on the paper (read from the
    `authorships` array index; see `openalex._normalise_work`).
    """
    n = work.n_authors
    k = work.focal_position
    if n <= 0 or k <= 0 or k > n:
        return 0.0
    h_n = sum(1.0 / j for j in range(1, n + 1))
    return (1.0 / k) / h_n


def declared_share(work: Work, declared: dict) -> float:
    """Return a user-supplied declared share for the focal author.

    Parameters
    ----------
    work : Work
        The publication record.
    declared : dict
        Mapping from OpenAlex work id (or DOI) to the focal author's
        declared share for that paper, as a float in [0, 1].

    Returns
    -------
    float
        The declared share when present; 0.0 when no entry is found for the
        work. A KeyError is not raised because partial declared-share
        coverage is the expected case during transition.
    """
    if work.openalex_id and work.openalex_id in declared:
        return float(declared[work.openalex_id])
    if work.doi and work.doi in declared:
        return float(declared[work.doi])
    return 0.0


# ----- dispatcher -----


_REGISTRY = {
    "equal": equal_share,
    "harmonic": harmonic_share,
}


def apply_scheme(
    works: list[Work],
    scheme: str,
    declared: Optional[dict] = None,
) -> list[float]:
    """Apply a named scheme across a list of works.

    Parameters
    ----------
    works : list of Work
        The works to score.
    scheme : str
        One of `equal`, `harmonic`, or `declared`.
    declared : dict, optional
        Required when scheme=`declared`. Mapping from work id or DOI to the
        focal author's declared share.

    Returns
    -------
    list of float
        One share value per input work, in input order.
    """
    if scheme == "declared":
        if declared is None:
            raise ValueError("scheme='declared' requires a `declared` mapping")
        return [declared_share(w, declared) for w in works]

    if scheme not in _REGISTRY:
        raise ValueError(
            f"unknown scheme: {scheme!r}. "
            f"Known schemes: {sorted(_REGISTRY)} and 'declared'."
        )

    fn = _REGISTRY[scheme]
    return [fn(w) for w in works]
