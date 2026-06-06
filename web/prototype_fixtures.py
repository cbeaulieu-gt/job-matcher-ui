"""web/prototype_fixtures.py — Hardcoded fixture data for the Shell-B prototype.

All shapes follow ``docs/design/data-model.md §A`` exactly.  Slices 2–8
will replace these hardcoded dicts/lists with real service/DB output; the
field shapes here are the data contract those slices must satisfy.

No Flask imports, no DB access — pure Python dicts/lists so the module is
independently importable and testable.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Candidate (singleton)  — data-model.md §A.2
# ---------------------------------------------------------------------------

CANDIDATE: dict[str, Any] = {
    "name": "Alex Reyes",
    "email": "alex.reyes@example.com",
    "current_role": "Senior Software Engineer",
    "current_location": {
        "label": "Austin, TX",
        "lat": 30.2672,
        "lng": -97.7431,
    },
    "country": "US",
    "base_salary": {
        "amount": 175_000,
        "currency": "USD",
        "period": "year",
    },
    "defaults": {
        "seniority": "Senior",
        "preferred_industries": [
            "Cloud Infrastructure",
            "Developer Tools",
            "FinTech",
        ],
    },
    "education": [
        {
            "degree_type": "B.S.",
            "degree_field": "Computer Science",
            "school": "UT Austin",
            "graduation_year": 2014,
        }
    ],
    "anti_preferences": [
        "enterprise-only sales tooling",
        "manual QA roles",
    ],
    "primary_skills": [
        {"id": "py", "name": "Python", "years": 10},
        {"id": "go", "name": "Go", "years": 5},
        {"id": "k8s", "name": "Kubernetes", "years": 4},
        {"id": "aws", "name": "AWS", "years": 7},
        {"id": "tf", "name": "Terraform", "years": 4},
        {"id": "sql", "name": "PostgreSQL", "years": 8},
        {"id": "spark", "name": "Apache Spark", "years": 3},
        {"id": "kafka", "name": "Kafka", "years": 2},
        {"id": "dbt", "name": "dbt", "years": 2},
        {"id": "ts", "name": "TypeScript", "years": 3},
        {"id": "react", "name": "React", "years": 2},
    ],
}

# ---------------------------------------------------------------------------
# Roles  — data-model.md §A.4
# ---------------------------------------------------------------------------

ROLES: list[dict[str, Any]] = [
    {
        "id": "swe",
        "name": "Software Engineer",
        "color": "#f5a623",
        "active": True,
        "search_what": "senior software engineer backend platform",
        "prefilter": {
            "title_include": ["engineer", "developer", "swe"],
            "title_exclude": ["qa", "test", "intern"],
        },
        "threshold": 7.0,
        "scoring_notes": [
            "Weigh Kubernetes and Terraform heavily — infra experience is key",
            "Go experience is a strong positive signal",
            "Prefer companies with open-source culture",
        ],
        "target_salary": 200_000,
        "applicable_skills": [
            "py", "go", "k8s", "aws", "tf", "sql", "ts",
        ],
        "default_resume_id": "resume-swe-v2",
        "overrides": {},
        "match_count": 14,
    },
    {
        "id": "data",
        "name": "Data Engineer",
        "color": "#4dd2f5",
        "active": True,
        "search_what": "senior data engineer pipeline infrastructure",
        "prefilter": {
            "title_include": ["data engineer", "data platform", "analytics eng"],
            "title_exclude": ["analyst", "scientist", "intern"],
        },
        "threshold": 6.5,
        "scoring_notes": [
            "Spark, Kafka, and dbt are strong signals",
            "Prefer modern data stack (not legacy ETL)",
        ],
        "target_salary": 195_000,
        "applicable_skills": [
            "py", "spark", "kafka", "dbt", "sql", "aws", "k8s",
        ],
        "default_resume_id": "resume-data-v1",
        "overrides": {
            "preferred_industries": [
                "FinTech",
                "Data Infrastructure",
                "ML Platforms",
            ],
        },
        "match_count": 9,
    },
    {
        "id": "platform",
        "name": "Platform Engineer",
        "color": "#b58cf5",
        "active": False,
        "search_what": "platform engineer devops sre infrastructure",
        "prefilter": {
            "title_include": [
                "platform", "devops", "sre", "reliability",
            ],
            "title_exclude": ["intern", "junior"],
        },
        "threshold": 7.5,
        "scoring_notes": [
            "Kubernetes and Terraform are table stakes",
            "AWS expertise required; multi-cloud is a plus",
        ],
        "target_salary": 205_000,
        "applicable_skills": [
            "k8s", "aws", "tf", "go", "py",
        ],
        "default_resume_id": None,
        "overrides": {},
        "match_count": 7,
    },
]

# ---------------------------------------------------------------------------
# JobPreferences (singleton)  — data-model.md §A.5
# ---------------------------------------------------------------------------

JOB_PREFERENCES: dict[str, Any] = {
    "locations": [
        {"label": "Austin, TX", "lat": 30.2672, "lng": -97.7431},
        {"label": "Remote (US)", "lat": None, "lng": None},
        {"label": "San Francisco, CA", "lat": 37.7749, "lng": -122.4194},
    ],
    "radius_km": 80,
    "work_arrangement": ["remote", "hybrid"],
    "job_types": ["full_time", "contract_to_hire"],
    "max_days_old": 14,
}

# ---------------------------------------------------------------------------
# Resumes  — data-model.md §A.6
# ---------------------------------------------------------------------------

RESUMES: list[dict[str, Any]] = [
    {
        "id": "resume-swe-v2",
        "label": "SWE — backend / infra focus v2",
        "role_id": "swe",
        "source": "edited",
        "created": "2026-05-01T10:00:00Z",
        "updated": "2026-05-28T14:22:00Z",
    },
    {
        "id": "resume-data-v1",
        "label": "Data Eng — Spark / dbt focus v1",
        "role_id": "data",
        "source": "uploaded",
        "created": "2026-04-15T09:00:00Z",
        "updated": "2026-04-15T09:00:00Z",
    },
    {
        "id": "resume-base",
        "label": "General / base resume",
        "role_id": None,
        "source": "uploaded",
        "created": "2026-01-10T08:00:00Z",
        "updated": "2026-03-12T16:40:00Z",
    },
]

# ---------------------------------------------------------------------------
# Jobs / feed listings  — data-model.md §A.8
# ---------------------------------------------------------------------------

JOBS: list[dict[str, Any]] = [
    {
        "id": "job-001",
        "title": "Senior Software Engineer — Platform",
        "company": "Temporal Technologies",
        "location": {"label": "Remote (US)"},
        "remote_type": "remote",
        "contract_type": "full_time",
        "salary": {"min": 190_000, "max": 230_000, "currency": "USD", "period": "year"},
        "source": "Greenhouse",
        "posted_at": "2026-06-04T09:00:00Z",
        "ingested_at": "2026-06-04T10:15:00Z",
        "state": "scored",
        "user_state": "new",
        "applied_resume_id": None,
        "matches": [
            {
                "role_id": "swe",
                "score": 9.2,
                "matched_skills": ["py", "go", "k8s", "aws"],
                "missing_skills": ["tf"],
                "verdict": (
                    "Strong fit. Temporal's workflow engine work aligns well "
                    "with distributed-systems experience. Go + Kubernetes "
                    "prominent in the JD."
                ),
                "overridden_via": [],
            }
        ],
        # derived — computed from candidate.base_salary
        "salary_delta_pct": 14,   # midpoint 210k vs 175k base → +20%
    },
    {
        "id": "job-002",
        "title": "Staff Data Engineer — ML Infrastructure",
        "company": "Stripe",
        "location": {"label": "San Francisco, CA / Remote"},
        "remote_type": "hybrid",
        "contract_type": "full_time",
        "salary": {"min": 210_000, "max": 260_000, "currency": "USD", "period": "year"},
        "source": "Lever",
        "posted_at": "2026-06-03T14:30:00Z",
        "ingested_at": "2026-06-03T15:00:00Z",
        "state": "scored",
        "user_state": "bookmarked",
        "applied_resume_id": None,
        "matches": [
            {
                "role_id": "data",
                "score": 8.7,
                "matched_skills": ["py", "spark", "kafka", "sql", "aws"],
                "missing_skills": ["dbt"],
                "verdict": (
                    "Excellent match. Stripe's data infra team uses Spark + "
                    "Kafka heavily. Staff-level ownership of ML feature "
                    "pipelines is a direct mapping to past work."
                ),
                "overridden_via": [],
            },
            {
                "role_id": "swe",
                "score": 6.1,
                "matched_skills": ["py", "aws", "sql"],
                "missing_skills": ["go", "k8s", "tf"],
                "verdict": "Partial fit from SWE angle — data engineering focus.",
                "overridden_via": [],
            },
        ],
        "salary_delta_pct": 34,   # midpoint 235k vs 175k → +34%
    },
    {
        "id": "job-003",
        "title": "Backend Engineer — Developer Experience",
        "company": "Hashicorp",
        "location": {"label": "Remote (US)"},
        "remote_type": "remote",
        "contract_type": "full_time",
        "salary": {"min": 175_000, "max": 205_000, "currency": "USD", "period": "year"},
        "source": "LinkedIn",
        "posted_at": "2026-06-02T11:00:00Z",
        "ingested_at": "2026-06-02T11:45:00Z",
        "state": "scored",
        "user_state": "new",
        "applied_resume_id": None,
        "matches": [
            {
                "role_id": "swe",
                "score": 8.4,
                "matched_skills": ["go", "tf", "aws", "k8s"],
                "missing_skills": ["ts"],
                "verdict": (
                    "Strong fit. Terraform is core to this role — "
                    "Hashicorp's tooling culture is a perfect environment."
                ),
                "overridden_via": [],
            }
        ],
        "salary_delta_pct": 6,    # midpoint 190k vs 175k → +8%
    },
    {
        "id": "job-004",
        "title": "Data Platform Engineer",
        "company": "Figma",
        "location": {"label": "New York, NY"},
        "remote_type": "hybrid",
        "contract_type": "full_time",
        "salary": None,  # no salary extracted — red flag
        "source": "Indeed",
        "posted_at": "2026-06-01T08:30:00Z",
        "ingested_at": "2026-06-01T09:00:00Z",
        "state": "scored",
        "user_state": "new",
        "applied_resume_id": None,
        "matches": [
            {
                "role_id": "data",
                "score": 7.3,
                "matched_skills": ["py", "dbt", "sql", "spark"],
                "missing_skills": ["kafka"],
                "verdict": (
                    "Good fit. Figma's data platform is modern-stack. "
                    "No salary listed — verify comp expectations."
                ),
                "overridden_via": [],
            }
        ],
        "salary_delta_pct": None,  # null → render no-salary flag
    },
    {
        "id": "job-005",
        "title": "Junior DevOps Engineer",
        "company": "Acme Corp",
        "location": {"label": "Austin, TX"},
        "remote_type": "onsite",
        "contract_type": "full_time",
        "salary": {"min": 95_000, "max": 110_000, "currency": "USD", "period": "year"},
        "source": "Indeed",
        "posted_at": "2026-06-05T07:00:00Z",
        "ingested_at": "2026-06-05T07:30:00Z",
        "state": "scored",
        "user_state": "dismissed",
        "applied_resume_id": None,
        "matches": [
            {
                "role_id": "platform",
                "score": 3.8,
                "matched_skills": ["aws"],
                "missing_skills": ["k8s", "tf", "go"],
                "verdict": "Low fit — junior level mismatch.",
                "overridden_via": [],
            }
        ],
        "salary_delta_pct": -40,   # midpoint 102.5k vs 175k → -41%
    },
    {
        "id": "job-006",
        "title": "Platform Infrastructure Engineer",
        "company": "Datadog",
        "location": {"label": "Remote (US)"},
        "remote_type": "remote",
        "contract_type": "full_time",
        "salary": {"min": 220_000, "max": 270_000, "currency": "USD", "period": "year"},
        "source": "Greenhouse",
        "posted_at": "2026-06-05T12:00:00Z",
        "ingested_at": "2026-06-05T12:30:00Z",
        "state": "snippet",  # not yet LLM-scored
        "user_state": "new",
        "applied_resume_id": None,
        "matches": [],
        "salary_delta_pct": 40,
    },
]

# ---------------------------------------------------------------------------
# Admin stats  — for the Admin → Stats panel
# ---------------------------------------------------------------------------

ADMIN_STATS: dict[str, Any] = {
    "kpis": {
        "ingested": 312,
        "scored": 287,
        "high_match": 31,
        "applied": 4,
        "apply_rate": "1.4%",
        "avg_score": 6.2,
    },
    "per_target": [
        {
            "role": "Software Engineer",
            "color": "#f5a623",
            "matched": 14,
            "applied": 2,
        },
        {
            "role": "Data Engineer",
            "color": "#4dd2f5",
            "matched": 9,
            "applied": 2,
        },
        {
            "role": "Platform Engineer",
            "color": "#b58cf5",
            "matched": 7,
            "applied": 0,
        },
    ],
    "job_sources": [
        {
            "name": "Greenhouse",
            "enabled": True,
            "last_run": "2026-06-05T12:30:00Z",
            "volume": 88,
            "dupes": 12,
            "status": "ok",
        },
        {
            "name": "LinkedIn",
            "enabled": True,
            "last_run": "2026-06-05T11:00:00Z",
            "volume": 142,
            "dupes": 31,
            "status": "ok",
        },
        {
            "name": "Lever",
            "enabled": True,
            "last_run": "2026-06-05T10:45:00Z",
            "volume": 56,
            "dupes": 9,
            "status": "ok",
        },
        {
            "name": "Indeed",
            "enabled": True,
            "last_run": "2026-06-04T22:00:00Z",
            "volume": 21,
            "dupes": 4,
            "status": "warn",
        },
        {
            "name": "HN Who's Hiring",
            "enabled": False,
            "last_run": None,
            "volume": 0,
            "dupes": 0,
            "status": "off",
        },
        {
            "name": "Wellfound",
            "enabled": False,
            "last_run": None,
            "volume": 0,
            "dupes": 0,
            "status": "off",
        },
    ],
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def get_active_roles() -> list[dict[str, Any]]:
    """Return only active (non-paused) roles from ROLES.

    Returns:
        List of role dicts where ``active`` is True.
    """
    return [r for r in ROLES if r["active"]]


def get_role_by_id(role_id: str) -> dict[str, Any] | None:
    """Look up a role dict by its id.

    Args:
        role_id: The role's ``id`` field.

    Returns:
        The matching role dict, or ``None`` if not found.
    """
    for role in ROLES:
        if role["id"] == role_id:
            return role
    return None


def get_jobs_for_role(role_id: str) -> list[dict[str, Any]]:
    """Return jobs that have a Match entry for the given role.

    Args:
        role_id: The role id to filter by.

    Returns:
        Jobs whose ``matches`` list contains an entry with
        ``role_id == role_id``.
    """
    return [
        j for j in JOBS
        if any(m["role_id"] == role_id for m in j.get("matches", []))
    ]


def get_skill_map() -> dict[str, dict[str, Any]]:
    """Return candidate skills keyed by skill id.

    Returns:
        Mapping of ``skill_id -> skill_dict`` for all of
        ``CANDIDATE['primary_skills']``.
    """
    return {s["id"]: s for s in CANDIDATE["primary_skills"]}


def score_tier(score: float | None) -> str:
    """Map a numeric score to its tier string.

    Args:
        score: A 0–10 score, or ``None`` for unscored (snippet) jobs.

    Returns:
        One of ``"high"``, ``"mid"``, ``"low"``, or ``"null"``.
    """
    if score is None:
        return "null"
    if score >= 8:
        return "high"
    if score >= 5:
        return "mid"
    return "low"
