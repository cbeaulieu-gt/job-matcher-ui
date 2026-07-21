"""web/prototype.py — Shell-B static UI prototype blueprint.

Registers a ``/prototype/...`` route tree that serves Jinja templates fed
with hardcoded fixture data (``web/prototype_fixtures.py``).  No database
access, no service calls.  Slices 2–8 replace the fixture context with
real service/DB output; the route handlers and templates stay.

Blueprint: ``prototype_bp`` — url_prefix ``"/prototype"``
Routes:
    GET /prototype            → redirect to /prototype/feed
    GET /prototype/feed       → feed view (default role from query param)
    GET /prototype/profile    → Candidate Profile view
    GET /prototype/roles      → Roles master–detail editor view
    GET /prototype/preferences → Job Preferences view
    GET /prototype/admin      → Admin view

Registered in ``web/__init__.py::create_app()`` alongside existing
blueprints.
"""

from __future__ import annotations

from flask import Blueprint, redirect, render_template, request, url_for

from web.prototype_fixtures import (
    ADMIN_STATS,
    CANDIDATE,
    JOB_PREFERENCES,
    JOBS,
    RESUMES,
    ROLES,
    get_active_roles,
    get_role_by_id,
    get_skill_map,
    score_tier,
)

prototype_bp = Blueprint("prototype_bp", __name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MANAGEMENT_VIEWS = {"profile", "roles", "preferences", "admin"}

_VIEW_HEADS: dict[str, dict[str, str]] = {
    "profile": {
        "title": "Candidate Profile",
        "icon": "◉",
        "desc": "Identity, education, base salary, and shared skill bucket",
    },
    "roles": {
        "title": "Roles",
        "icon": "⟡",
        "desc": "Target roles — criteria, skills, linked resume",
    },
    "preferences": {
        "title": "Job Preferences",
        "icon": "⊞",
        "desc": "Global locations, work models, and job types",
    },
    "admin": {
        "title": "Administration",
        "icon": "⚙",
        "desc": "Stats, sources, LLM settings, system",
    },
}


def _shell_ctx(
    view: str,
    active_role_id: str | None = None,
) -> dict:
    """Build the common template context for the Shell-B layout.

    Args:
        view: The active view name (``"feed"``, ``"profile"``, etc.).
        active_role_id: The currently selected role id (feed views only).

    Returns:
        A dict of template variables shared by all prototype templates.
    """
    active_role_id = active_role_id or (
        ROLES[0]["id"] if ROLES else None
    )
    active_role = get_role_by_id(active_role_id) if active_role_id else None
    is_feed = view == "feed"
    return {
        "view": view,
        "is_feed": is_feed,
        "is_management": view in _MANAGEMENT_VIEWS,
        "view_head": _VIEW_HEADS.get(view),
        "candidate": CANDIDATE,
        "roles": ROLES,
        "active_roles": get_active_roles(),
        "active_role": active_role,
        "active_role_id": active_role_id,
        "skill_map": get_skill_map(),
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@prototype_bp.route("")
@prototype_bp.route("/")
def prototype_index():
    """Redirect / and '' to the feed view.

    Returns:
        A Flask redirect to ``/prototype/feed``.
    """
    return redirect(url_for("prototype_bp.prototype_feed"), code=302)


@prototype_bp.route("/feed")
def prototype_feed():
    """Render the Shell-B feed view with fixture job listings.

    Query params:
        role (str): Active role id; defaults to the first active role.

    Returns:
        Rendered ``prototype/feed.html`` template with fixture data.
    """
    role_id = request.args.get("role") or (
        ROLES[0]["id"] if ROLES else None
    )
    ctx = _shell_ctx("feed", role_id)

    # Determine which jobs to show for the active role or combined view
    if role_id == "combined":
        jobs = JOBS
    else:
        jobs = [
            j for j in JOBS
            if any(m["role_id"] == role_id for m in j.get("matches", []))
        ]

    # Annotate each job with the active-role match for easier template use.
    # For the combined view there is no single role_id to key on, so select
    # the highest-scoring match as the representative (None when no matches).
    annotated = []
    for job in jobs:
        if role_id == "combined":
            matches = job.get("matches", [])
            match = (
                max(matches, key=lambda m: m["score"])
                if matches
                else None
            )
        else:
            match = next(
                (
                    m for m in job.get("matches", [])
                    if m["role_id"] == role_id
                ),
                None,
            )
        annotated.append(
            {
                **job,
                "_active_match": match,
                "_tier": score_tier(
                    match["score"] if match else None
                ),
            }
        )

    ctx["jobs"] = annotated
    ctx["total_jobs"] = len(annotated)
    return render_template("prototype/feed.html", **ctx)


@prototype_bp.route("/profile")
def prototype_profile():
    """Render the Candidate Profile management view.

    Returns:
        Rendered ``prototype/profile.html`` template with fixture data.
    """
    ctx = _shell_ctx("profile")
    ctx["resumes"] = RESUMES
    return render_template("prototype/profile.html", **ctx)


@prototype_bp.route("/roles")
def prototype_roles():
    """Render the Roles master–detail editor view.

    Query params:
        role (str): Selected role id in the detail pane; defaults to
            the first role.

    Returns:
        Rendered ``prototype/roles.html`` template with fixture data.
    """
    selected_id = request.args.get("role") or (
        ROLES[0]["id"] if ROLES else None
    )
    ctx = _shell_ctx("roles")
    ctx["selected_role"] = get_role_by_id(selected_id)
    ctx["selected_role_id"] = selected_id
    ctx["resumes"] = RESUMES
    return render_template("prototype/roles.html", **ctx)


@prototype_bp.route("/preferences")
def prototype_preferences():
    """Render the Job Preferences global settings view.

    Returns:
        Rendered ``prototype/preferences.html`` template with fixture
        data.
    """
    ctx = _shell_ctx("preferences")
    ctx["preferences"] = JOB_PREFERENCES
    return render_template("prototype/preferences.html", **ctx)


@prototype_bp.route("/admin")
def prototype_admin():
    """Render the Admin operational view.

    Returns:
        Rendered ``prototype/admin.html`` template with fixture data.
    """
    ctx = _shell_ctx("admin")
    ctx["stats"] = ADMIN_STATS
    return render_template("prototype/admin.html", **ctx)
