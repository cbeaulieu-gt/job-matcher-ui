"""
job_sources/base.py — Abstract base class for job source providers.

All concrete job sources must implement ``fetch_page()``, ``total_pages()``,
and ``_normalise()`` so that the ingestion pipeline can work with any source
without source-specific branching.

Canonical listing schema
------------------------
``normalise()`` (the public method on this base class) calls ``_normalise()``
then applies schema defaults so that every key in the canonical schema is
always present in the returned dict.  Plugins only need to return the keys
they have data for.

Required keys — must always be present with a meaningful value:

    source          str          — source identifier, e.g. "adzuna"
    source_id       str          — source-specific listing ID
    title           str
    company         str
    location        str
    redirect_url    str

Optional keys — populated by plugins that have data for them; absent keys are
defaulted automatically by ``_apply_defaults()`` before the dict reaches the
ingestion pipeline:

    salary_min      float|None   — default None
    salary_max      float|None   — default None
    salary_period   str|None     — "annual", "daily", "hourly", or None
                                   default None
    contract_type   str|None     — default None
    contract_time   str|None     — default None
    description     str|None     — snippet or None; full JD scraped later
                                   default None
    created_at      str|None     — ISO 8601 string, e.g. "2026-01-02T12:34:56Z"
                                   default None
    skip_scrape     bool         — set True when the source URL is known to
                                   block scrapers (e.g. Jooble /jdp/ pages
                                   return 403).  The pipeline skips the HTTP
                                   scrape step and uses the API description
                                   directly.  Default False.
    description_is_full
                    bool         — set True alongside skip_scrape when the
                                   source API provides complete job descriptions
                                   (not just snippets).  Listings with this
                                   flag and descriptions >= 100 chars are
                                   classified as "full" in the main feed.
                                   Default False.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterator

# Optional keys and their defaults, applied by ``_apply_defaults()`` whenever
# a plugin's ``_normalise()`` does not explicitly set them.
_OPTIONAL_DEFAULTS: dict = {
    "salary_min": None,
    "salary_max": None,
    "salary_period": None,
    "contract_type": None,
    "contract_time": None,
    "description": None,
    "created_at": None,
    "skip_scrape": False,
    "description_is_full": False,
}


class JobSource(ABC):
    """Interface that every job source backend must satisfy.

    Concrete sub-classes encapsulate source-specific API calls, pagination,
    and field normalisation so that ``ingest.py`` remains source-agnostic.

    Class Attributes:
        REQUIRED_SEARCH_FIELDS: Tuple of ``config["search"]`` key names that
            must be present, non-empty, and non-zero for this source to run.
            Defaults to ``()`` — sources that do not read ``config["search"]``
            leave this empty so they are never flagged by the search-config
            validator.  Populate on subclasses that depend on search params
            (e.g. Adzuna needs ``country``, ``what``, ``results_per_page``,
            and ``max_pages``).
    """

    REQUIRED_SEARCH_FIELDS: tuple[str, ...] = ()

    @abstractmethod
    def fetch_page(self, page: int) -> list[dict]:
        """Fetch a single page of raw listings from the source.

        Args:
            page: 1-based page number.

        Returns:
            List of raw listing dicts as returned by the source API.
            Returns an empty list when no results are available or on error.
        """
        ...

    @abstractmethod
    def total_pages(self) -> int:
        """Return the number of pages available for the current search.

        Returns:
            Integer page count. Implementations may return a configured
            maximum rather than querying the API for the true total.
        """
        ...

    @abstractmethod
    def _normalise(self, raw: dict) -> dict:
        """Convert a source-specific raw listing dict to the canonical schema.

        Plugins implement this method instead of ``normalise()``.  Only the
        keys the source actually has data for need to be returned — the public
        ``normalise()`` method fills in optional-key defaults via
        ``_apply_defaults()`` before returning to callers.

        Args:
            raw: A single raw listing dict as returned by ``fetch_page()``.

        Returns:
            Dict containing at minimum all required canonical keys plus any
            optional keys the source populates.  Unknown source fields are
            silently dropped.
        """
        ...

    # ------------------------------------------------------------------
    # Concrete helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_defaults(listing: dict) -> dict:
        """Fill in optional canonical keys that the plugin did not set.

        Applies ``_OPTIONAL_DEFAULTS`` for every key absent from *listing*
        without overwriting keys the plugin explicitly set (including falsy
        values like ``None``, ``0``, or ``""``, which are intentional).

        Args:
            listing: Partial canonical listing dict from ``_normalise()``.

        Returns:
            The same dict with missing optional keys populated from
            ``_OPTIONAL_DEFAULTS``.
        """
        for key, default in _OPTIONAL_DEFAULTS.items():
            if key not in listing:
                listing[key] = default
        return listing

    def normalise(self, raw: dict) -> dict:
        """Convert a raw listing dict to the canonical schema with defaults.

        Calls ``_normalise(raw)`` then applies optional-key defaults so that
        every key in the canonical schema is always present.  Callers should
        use this method; plugins should implement ``_normalise()``.

        Args:
            raw: A single raw listing dict as returned by ``fetch_page()``.

        Returns:
            Dict conforming to the canonical listing schema with all optional
            keys present (defaulted if not set by the plugin).
        """
        listing = self._normalise(raw)
        return self._apply_defaults(listing)

    def pages(self) -> Iterator[list[dict]]:
        """Yield normalised listing lists, one per page.

        Default implementation iterates from page 1 up to ``total_pages()``
        (inclusive) using ``fetch_page()`` and stops early when a page returns
        zero results.  Subclasses may override this to apply source-specific
        logic (e.g. 0-based page numbering, caching).

        Yields:
            Lists of normalised listing dicts (one list per page).
        """
        import logging as _logging
        _log = _logging.getLogger(__name__)
        for page in range(1, self.total_pages() + 1):
            results = self.fetch_page(page)
            if not results:
                _log.info("Page %d returned 0 results; stopping early", page)
                return
            yield results
