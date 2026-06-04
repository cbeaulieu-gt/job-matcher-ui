"""
Plugin template — copy this folder, rename it, and implement the three methods below.

Folder name must match the source_key in source.json.

The settings_schema() method is NOT needed here — it is auto-generated from source.json
by the plugin loader (job_sources/loader.py) when the plugin is discovered at startup.
"""
from __future__ import annotations

from job_sources.base import JobSource


class TemplateSource(JobSource):
    """Replace with your source name. One subclass per plugin.py — no more, no less.

    The loader requires exactly one JobSource subclass in this file. If your
    source needs helper classes, put them in a separate module and import them.
    """

    def __init__(self, config: dict, credentials: dict | None = None) -> None:
        """Store config and credentials for use in the three required methods.

        Args:
            config:      The full app config dict (loaded from config/config.json).
                         Useful for search parameters like ``config["what"]``,
                         ``config["where"]``, ``config["results_per_page"]``, etc.
            credentials: The ``job_sources.<source_key>`` section of
                         config/providers.json, or None if the source has no
                         required credentials (i.e. ``"fields": []`` in source.json).
        """
        self._config = config
        self._credentials = credentials or {}

    # ------------------------------------------------------------------ #
    # Required: implement these three methods                             #
    # ------------------------------------------------------------------ #

    def fetch_page(self, page: int) -> list[dict]:
        """Fetch one page of raw listings from the source API.

        Args:
            page: 1-based page index. Page 1 is the first page of results.

        Returns:
            List of raw dicts in whatever shape the source API returns.
            Return an empty list (not None) on error or when there are no
            results — the pipeline treats an empty list as "stop paginating".

        Example::

            import requests
            resp = requests.get(
                "https://api.example.com/jobs",
                params={"page": page, "q": self._config.get("what", "")},
                timeout=15,
            )
            if resp.status_code != 200:
                return []
            return resp.json().get("results", [])
        """
        raise NotImplementedError

    def total_pages(self) -> int:
        """Return the total number of pages available for the current search.

        This may make a network request on first call to learn the result count.
        Cache the value if the source's API requires a separate request to
        determine the page count (see the Adzuna plugin for an example).

        For single-page APIs (e.g. Jobicy), always return 1.

        Returns:
            Total number of pages as an integer.

        Example (single-page API)::

            return 1

        Example (API returns total count in first response)::

            if self._total_pages is None:
                self._total_pages = self._fetch_total_pages()
            return self._total_pages
        """
        raise NotImplementedError

    def _normalise(self, raw: dict) -> dict:
        """Convert one raw listing dict to the canonical schema.

        Implement this method instead of ``normalise()``.  Only include the
        keys your source has data for — the base class ``normalise()`` wrapper
        applies defaults for any optional keys you omit.

        Required keys (must always be present and non-empty):

            source          str          — source identifier, must match source_key
            source_id       str          — unique listing ID from the source
            title           str          — job title
            company         str          — employer name
            location        str          — location string as returned by source
            redirect_url    str          — URL linking to the full job listing

        Optional keys (omit if your source has no data for them; defaults are
        applied automatically — see ``job_sources/base.py``):

            salary_min      float|None   — lower salary bound (in local currency)
            salary_max      float|None   — upper salary bound (in local currency)
            salary_period   str|None     — "annual", "daily", "hourly", or None
            contract_type   str|None     — e.g. "permanent", "contract", or None
            contract_time   str|None     — e.g. "full_time", "part_time", or None
            description     str|None     — snippet or None; pipeline scrapes full JD later
            created_at      str|None     — ISO 8601 string, e.g. "2026-01-02T12:34:56Z"
            skip_scrape     bool         — True when source URL blocks scrapers
            description_is_full
                            bool         — True when source provides complete descriptions

        Args:
            raw: A single listing dict as returned by ``fetch_page()``.

        Returns:
            Dict with required keys plus any optional keys the source populates.
            Do not include optional keys your source has no data for — the base
            class will default them automatically.

        Example::

            from job_sources.utils import strip_html, parse_salary

            salary_min, salary_max = parse_salary(raw.get("salary", ""))
            return {
                "source": "mysource",
                "source_id": str(raw["id"]),
                "title": raw.get("title", ""),
                "company": raw.get("company", ""),
                "location": raw.get("location", ""),
                "redirect_url": raw.get("url", ""),
                # Include optional keys only when the source has data for them:
                "salary_min": salary_min,
                "salary_max": salary_max,
                "contract_time": raw.get("schedule"),
                "description": strip_html(raw.get("description", "")),
                "created_at": raw.get("posted_at"),
            }
        """
        raise NotImplementedError
