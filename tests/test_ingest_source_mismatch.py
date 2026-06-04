"""
tests/test_ingest_source_mismatch.py — Tests for ingest._warn_source_mismatch().

Verifies that the startup diagnostic logs a warning when a source is enabled
in providers.json but its plugin is not present in the loaded source registry,
and that no warning is emitted when everything is consistent.
"""

from __future__ import annotations

import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import ingest  # noqa: E402


class TestWarnSourceMismatch:
    """Unit tests for ingest._warn_source_mismatch()."""

    def test_no_warning_when_all_enabled_sources_are_loaded(
        self, monkeypatch, caplog
    ):
        """No warning when every enabled source key is in the plugin registry."""
        monkeypatch.setattr(
            "ingest.get_sources",
            lambda: {"adzuna": object(), "remotive": object()},
        )
        providers = {
            "job_sources": {
                "adzuna": {"enabled": True},
                "remotive": {"enabled": True},
            }
        }
        with caplog.at_level(logging.WARNING, logger="ingest"):
            ingest._warn_source_mismatch(providers)

        assert caplog.records == []

    def test_warning_emitted_for_enabled_source_not_in_registry(
        self, monkeypatch, caplog
    ):
        """A warning is logged when an enabled source is absent from the registry."""
        monkeypatch.setattr(
            "ingest.get_sources",
            lambda: {},  # registry has no plugins loaded
        )
        providers = {
            "job_sources": {
                "ghost_source": {"enabled": True},
            }
        }
        with caplog.at_level(logging.WARNING, logger="ingest"):
            ingest._warn_source_mismatch(providers)

        assert len(caplog.records) == 1
        assert "ghost_source" in caplog.records[0].message
        assert "not loaded" in caplog.records[0].message

    def test_no_warning_for_disabled_source_not_in_registry(
        self, monkeypatch, caplog
    ):
        """Disabled sources that are absent from the registry do not warn."""
        monkeypatch.setattr(
            "ingest.get_sources",
            lambda: {},
        )
        providers = {
            "job_sources": {
                "ghost_source": {"enabled": False},
            }
        }
        with caplog.at_level(logging.WARNING, logger="ingest"):
            ingest._warn_source_mismatch(providers)

        assert caplog.records == []

    def test_no_warning_when_job_sources_key_absent(
        self, monkeypatch, caplog
    ):
        """An empty or missing job_sources section produces no warning."""
        monkeypatch.setattr(
            "ingest.get_sources",
            lambda: {},
        )
        with caplog.at_level(logging.WARNING, logger="ingest"):
            ingest._warn_source_mismatch({})

        assert caplog.records == []

    def test_multiple_missing_sources_each_warn(
        self, monkeypatch, caplog
    ):
        """Each enabled-but-missing source emits its own warning."""
        monkeypatch.setattr(
            "ingest.get_sources",
            lambda: {},
        )
        providers = {
            "job_sources": {
                "alpha": {"enabled": True},
                "beta": {"enabled": True},
            }
        }
        with caplog.at_level(logging.WARNING, logger="ingest"):
            ingest._warn_source_mismatch(providers)

        messages = [r.message for r in caplog.records]
        assert any("alpha" in m for m in messages)
        assert any("beta" in m for m in messages)

    def test_source_present_in_registry_but_disabled_does_not_warn(
        self, monkeypatch, caplog
    ):
        """A loaded source that is disabled does not produce a warning."""
        monkeypatch.setattr(
            "ingest.get_sources",
            lambda: {"adzuna": object()},
        )
        providers = {
            "job_sources": {
                "adzuna": {"enabled": False},
            }
        }
        with caplog.at_level(logging.WARNING, logger="ingest"):
            ingest._warn_source_mismatch(providers)

        assert caplog.records == []

    def test_warning_message_mentions_plugin_path(
        self, monkeypatch, caplog
    ):
        """The warning message includes the expected plugin directory path hint."""
        monkeypatch.setattr(
            "ingest.get_sources",
            lambda: {},
        )
        providers = {
            "job_sources": {
                "my_plugin": {"enabled": True},
            }
        }
        with caplog.at_level(logging.WARNING, logger="ingest"):
            ingest._warn_source_mismatch(providers)

        assert len(caplog.records) == 1
        msg = caplog.records[0].message
        assert "my_plugin" in msg
        assert "plugins/sources/my_plugin" in msg
