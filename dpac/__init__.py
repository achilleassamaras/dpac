"""
dpac — declared percentage-based author-contribution metrics.

A small toolkit for computing paper-level and author-level bibliometric
quantities from an OpenAlex publication record, under a chosen contribution-
share scheme. The companion software for the preprint:

    A. G. Samaras, "A declared percentage-based author-contribution system
    for weighted research metrics: a proposal." MetaArXiv preprint, 2026.

Two algorithmic imputation schemes (equal share and harmonic counting) are
implemented as stand-ins for the declared shares the proposal specifies, plus
a passthrough scheme for user-supplied declared shares.

The `dpac.selfcite` module (command line: `python -m dpac.selfcite`) splits a
researcher's citations into own, co-author, collaborator-network and
independent citations, and recomputes the metrics under seven self-citation
rules.

See README.md for usage and tool_spec.md for the design specification.
"""

from .openalex import fetch_orcid_works, OpenAlexClient
from .schemes import apply_scheme, equal_share, harmonic_share, declared_share
from .metrics import (
    paper_level_metrics,
    author_level_metrics,
    raw_h_index,
    fractional_h_index,
)
from .profile import compute_profile, ResearcherResult
from .sample import sample_authors, sample_authors_stratified, CONCEPTS, TOPICS

__version__ = "1.1.0"

__all__ = [
    "fetch_orcid_works",
    "OpenAlexClient",
    "apply_scheme",
    "equal_share",
    "harmonic_share",
    "declared_share",
    "paper_level_metrics",
    "author_level_metrics",
    "raw_h_index",
    "fractional_h_index",
    "compute_profile",
    "ResearcherResult",
    "sample_authors",
    "sample_authors_stratified",
    "CONCEPTS",
    "TOPICS",
]
