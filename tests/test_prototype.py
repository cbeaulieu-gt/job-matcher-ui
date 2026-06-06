"""tests/test_prototype.py — Route smoke tests for the Shell-B prototype.

Each test verifies that a /prototype/... route returns HTTP 200 and
renders the expected page region markers (``data-od-id`` attributes
from the Shell-B layout spec) without touching the database.  The
prototype blueprint serves hardcoded fixture data, so these tests run
in any environment where the project dependencies are installed.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Shared fixture — one Flask test client per test session
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Return a Flask test client with the full app (prototype registered).

    The conftest.py database patches are already active by the time this
    fixture runs, so no live Postgres connection is required.
    """
    from web import create_app

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# /prototype  (redirect to feed)
# ---------------------------------------------------------------------------

class TestPrototypeIndex:
    """The /prototype root redirects to the feed view."""

    def test_prototype_index_redirects(self, client) -> None:
        """GET /prototype must return a redirect to /prototype/feed."""
        response = client.get("/prototype")

        assert response.status_code in (301, 302, 308)

    def test_prototype_index_or_feed_returns_200(self, client) -> None:
        """GET /prototype/ or the redirect target must eventually 200."""
        response = client.get("/prototype/", follow_redirects=True)

        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /prototype/feed
# ---------------------------------------------------------------------------

class TestPrototypeFeed:
    """Shell-B feed view renders the three-region shell."""

    def test_feed_returns_200(self, client) -> None:
        """GET /prototype/feed must return HTTP 200."""
        response = client.get("/prototype/feed")

        assert response.status_code == 200

    def test_feed_has_shell_region(self, client) -> None:
        """Feed response must include data-od-id='shell'."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        assert 'data-od-id="shell"' in body

    def test_feed_has_rail_region(self, client) -> None:
        """Feed response must include data-od-id='rail'."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        assert 'data-od-id="rail"' in body

    def test_feed_has_main_region(self, client) -> None:
        """Feed response must include data-od-id='main'."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        assert 'data-od-id="main"' in body

    def test_feed_has_context_bar(self, client) -> None:
        """Feed response must include data-od-id='context'."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        assert 'data-od-id="context"' in body

    def test_feed_has_subbar(self, client) -> None:
        """Feed response must include data-od-id='filters'."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        assert 'data-od-id="filters"' in body

    def test_feed_has_feed_region(self, client) -> None:
        """Feed response must include data-od-id='feed'."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        assert 'data-od-id="feed"' in body

    def test_feed_has_inspector_region(self, client) -> None:
        """Feed response must include data-od-id='inspector'."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        assert 'data-od-id="inspector"' in body

    def test_feed_renders_job_cards(self, client) -> None:
        """Feed response must contain at least one job card title."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        # Fixture jobs are present; at minimum one score badge renders
        assert "score-badge" in body

    def test_feed_renders_salary_delta(self, client) -> None:
        """Feed cards must show a salary delta (vs base) or no-salary flag."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        # Either a delta like "+20% vs base" or a "no salary" flag
        assert "vs base" in body or "no-salary" in body

    def test_feed_renders_role_switcher(self, client) -> None:
        """Rail must contain a role quick-switcher."""
        response = client.get("/prototype/feed")
        body = response.data.decode("utf-8")

        assert 'data-od-id="rail-roles"' in body


# ---------------------------------------------------------------------------
# /prototype/profile
# ---------------------------------------------------------------------------

class TestPrototypeProfile:
    """Candidate profile view."""

    def test_profile_returns_200(self, client) -> None:
        """GET /prototype/profile must return HTTP 200."""
        response = client.get("/prototype/profile")

        assert response.status_code == 200

    def test_profile_has_no_subbar(self, client) -> None:
        """Profile view must NOT render the feed-only subbar."""
        response = client.get("/prototype/profile")
        body = response.data.decode("utf-8")

        assert 'data-od-id="filters"' not in body

    def test_profile_context_bar_shows_management_mode(
        self, client
    ) -> None:
        """Profile context bar must not show feed criteria chips."""
        response = client.get("/prototype/profile")
        body = response.data.decode("utf-8")

        # Management mode: no match-count chip
        assert 'data-od-id="ctx-match-count"' not in body

    def test_profile_renders_skills_section(self, client) -> None:
        """Profile view must render a skills section."""
        response = client.get("/prototype/profile")
        body = response.data.decode("utf-8")

        assert "skills" in body.lower()


# ---------------------------------------------------------------------------
# /prototype/roles
# ---------------------------------------------------------------------------

class TestPrototypeRoles:
    """Roles master-detail editor view."""

    def test_roles_returns_200(self, client) -> None:
        """GET /prototype/roles must return HTTP 200."""
        response = client.get("/prototype/roles")

        assert response.status_code == 200

    def test_roles_has_master_list(self, client) -> None:
        """Roles view must include the role master list panel."""
        response = client.get("/prototype/roles")
        body = response.data.decode("utf-8")

        assert 'data-od-id="roles-list"' in body

    def test_roles_has_detail_pane(self, client) -> None:
        """Roles view must include the role detail editor pane."""
        response = client.get("/prototype/roles")
        body = response.data.decode("utf-8")

        assert 'data-od-id="roles-detail"' in body

    def test_roles_renders_tier_bands(self, client) -> None:
        """Role detail pane must show the three tier band labels."""
        response = client.get("/prototype/roles")
        body = response.data.decode("utf-8")

        body_lower = body.lower()
        # Three labeled bands from the spec
        assert "target-defined" in body_lower or "target defined" in body_lower
        assert "shared" in body_lower
        assert "skills applicable" in body_lower or "applicable" in body_lower

    def test_roles_no_subbar(self, client) -> None:
        """Roles management view must NOT render the feed-only subbar."""
        response = client.get("/prototype/roles")
        body = response.data.decode("utf-8")

        assert 'data-od-id="filters"' not in body


# ---------------------------------------------------------------------------
# /prototype/preferences
# ---------------------------------------------------------------------------

class TestPrototypePreferences:
    """Job Preferences global settings view."""

    def test_preferences_returns_200(self, client) -> None:
        """GET /prototype/preferences must return HTTP 200."""
        response = client.get("/prototype/preferences")

        assert response.status_code == 200

    def test_preferences_no_subbar(self, client) -> None:
        """Job Preferences view must NOT render the feed-only subbar."""
        response = client.get("/prototype/preferences")
        body = response.data.decode("utf-8")

        assert 'data-od-id="filters"' not in body

    def test_preferences_renders_locations(self, client) -> None:
        """Preferences view must render the Locations section."""
        response = client.get("/prototype/preferences")
        body = response.data.decode("utf-8")

        assert "location" in body.lower()

    def test_preferences_renders_work_models(self, client) -> None:
        """Preferences view must render Work Models section."""
        response = client.get("/prototype/preferences")
        body = response.data.decode("utf-8")

        assert "remote" in body.lower() or "work model" in body.lower()


# ---------------------------------------------------------------------------
# /prototype/admin
# ---------------------------------------------------------------------------

class TestPrototypeAdmin:
    """Admin operational view."""

    def test_admin_returns_200(self, client) -> None:
        """GET /prototype/admin must return HTTP 200."""
        response = client.get("/prototype/admin")

        assert response.status_code == 200

    def test_admin_no_subbar(self, client) -> None:
        """Admin view must NOT render the feed-only subbar."""
        response = client.get("/prototype/admin")
        body = response.data.decode("utf-8")

        assert 'data-od-id="filters"' not in body

    def test_admin_renders_stats_section(self, client) -> None:
        """Admin view must render stats KPIs."""
        response = client.get("/prototype/admin")
        body = response.data.decode("utf-8")

        assert "stat" in body.lower()
