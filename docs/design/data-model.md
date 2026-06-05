# job-matcher — data model & schema (Candidate · Roles · Job Preferences)

> **Purpose.** The canonical data model for the job-matcher redesign — every entity, field, and
> relation in one place — plus the dated decision log that explains *how* the model got here.
> UI work codes against **§A (normative model)**; the sections below it are the rationale and the
> capture of the *current* codebase that the redesign extends.
>
> Renamed from `role-schema.md` → `data-model.md` (2026-05-29) once it outgrew its original
> "role schema" scope: it now defines the whole three-category model (Candidate · Roles · Job
> Preferences) plus the Skill, Resume, Application, and Job entities. `roles-editor-rebuild.md`
> references are updated to point here.
>
> **Source of truth (read-only reference repo):** `I:\career\job-matcher`
> Captured: 2026-05-29. The `file:line` anchors in §2 are real references into that repo. Entities
> in §A are tagged **[captured]** (verified against the repo) or **[designed]** (new redesign work,
> not yet in the repo) so provenance stays honest — per the project's "cite sources" discipline,
> **no `file:line` anchor is invented** for `[designed]` entities; they carry a "verify at build" note.

---

## 0. Top-level information architecture — DECISION (2026-05-29)

The model divides into **three top-level categories**. This is the organizing frame; the tier
model (§3) describes *how fields behave* within and across these categories, but the categories
are what the user sees and navigates. User's words: *"divide into three separate high level
categories which goes beyond just the role schema."*

| Category | Holds | Nature |
|---|---|---|
| **Candidate Profile** | Name, email, **current location**, **current role**, education, **skills** (the shared bucket), **base salary** | Who the candidate *is* — one source of truth |
| **Roles** | Specific target roles, each with **target salary**, **selected skills** (visibility set), and **a matching resume** | What the candidate is *aiming for* — multiple, switchable |
| **Job Preferences** | **Locations** (willing-to-work set), **Work Models** (onsite/hybrid/remote), **Job Types** (Contract / Contract-to-Hire / Full-Time / …) | *Where & how* the candidate will work — global, search-wide |

### How this maps to the tier model (§3)

- **Candidate Profile** ≈ **Tier 3 (shared-only)** + identity. Contains `primary_skills` (shared
  bucket), `education`, `anti_preferences`, `country`, contact fields, plus three fields elevated
  here: **current location**, **current role**, and **base salary** (see "New / moved fields" below).
- **Roles** ≈ **Tier 1 (target-defined)** + per-role attributes. Each role owns `search.what`,
  prefilter title gates, `scoring.threshold`, `scoring_notes`, its **selected-skills visibility set**,
  its **target salary**, and its **linked resume**.
- **Job Preferences** ≈ the **Global search-preferences layer** (§3). `locations[]`,
  `work_arrangement`, `job_types` — not per-role, not overridable.

### New / moved fields this introduces

- **Current location** → Candidate Profile (identity). The candidate's home/base — and the
  distance-scoring origin, *not* the first entry of the willing-to-work `locations[]`. The two are
  cleanly separated: *current location* = where you are; *Locations* (Job Preferences) = where you'd
  take a job.
- **Current role** → Candidate Profile. A **new field** (e.g. "Senior Software Engineer") describing
  what the candidate does *today* — distinct from the target **Roles** they're searching for.
- **Base salary** → Candidate Profile. A **new field** — the candidate's current/reference total
  compensation. It does **two jobs** (DECIDED 2026-05-29): (a) the **comparison anchor** for the
  feed — a posting renders as e.g. *"+20% vs your base"*; and (b) the **seed** for a new role's
  `target_salary` (then editable per role). User's words: *"this information should also be used to
  help display comparisons in the actual job search, so you could visually see Job A is +20% your
  base"* and *"[a candidate-level default salary should] seed a new role (editable per role)."*
- **Target salary → per-role (Roles).** `salary_min` was Tier 2 (shared default w/ override); it is
  now a **per-role attribute** (`role.target_salary`), seeded from `candidate.base_salary`.
- **Resumes → under Roles.** Each role links a default "matching resume"; per-application resumes
  are modeled by the **Application** entity (§A). Previously a standalone management surface.

### Navigation impact (rail)

The earlier plan was **Profile › Roles · Skills · Resumes**. This IA replaces that with **three
top-level config destinations**:

1. **Candidate Profile** (absorbs the standalone *Skills* surface — skills are part of the candidate)
2. **Roles** (absorbs *Resumes* — each role links its matching resume)
3. **Job Preferences** (new — the global locations / work-model / job-type surface)

The rail's **Roles quick-switcher** (active-target selector for browsing the feed) is unaffected —
that's a runtime view control, separate from these three config destinations.

---

## A. Canonical data model (NORMATIVE) — this is what UI codes against

> Pseudo-schema, not a specific serialization. Types are indicative. `?` = optional/nullable.
> Tags: **[captured]** = exists in the live repo today (anchors in §2); **[designed]** = new
> redesign work (verify field-for-field against the repo when UI/persistence work begins).

### A.1 Entity–relationship overview

```
                         ┌──────────────────────────────┐
                         │  Candidate (singleton)        │
                         │  identity · base_salary ·     │
                         │  defaults · primary_skills[]  │
                         └───────────────┬──────────────┘
            owns bucket  │               │ owns                 owns (1)
        ┌────────────────┘               │                        │
        ▼                                ▼                         ▼
   ┌─────────┐  applicable_skills   ┌─────────┐  default_resume  ┌──────────────────────┐
   │ Skill   │◀───────(*..*)────────│ Role    │────(0..1)───────▶│ JobPreferences       │
   │ id·name │   (binary refs)      │ target_ │                  │ (singleton, global)  │
   │ ·years  │                      │ salary· │                  │ locations[]·         │
   └─────────┘                      │ tier-1· │                  │ work_arrangement·    │
                                     │ overrides│                 │ job_types            │
                                     └────┬────┘                  └──────────┬───────────┘
                                          │ tailored-for (0..1)              │ filters
                                          ▼                                  │ ingestion
   ┌──────────────┐                                          applied_resume_id  ┌──────────────────┐
   │ Resume       │◀──────────────────(0..1)─────────────────────────────────────│ Job (posting)    │
   │ id·label·    │   default_resume_id (from Role, above)                        │ salary·source·   │
   │ role_id?     │                                                              │ matches[] (per   │
   └──────────────┘   (Application join entity DEFERRED — A.7)                    │ role)·user_state │
                                                                                  └──────────────────┘
        candidate.base_salary ───────────(comparison anchor)──────────▶ Job.salary  (derived %)
```

### A.2 `Candidate` — singleton  **[captured + designed]**

```
Candidate {
  // identity (Tier 3 — captured, except current_role/base_salary which are designed)
  name:             str
  email:            str
  current_location: { label: str, lat?: num, lng?: num }   // home/base = distance origin
  current_role:     str            // [designed] what they do today, e.g. "Senior SWE"
  education:        Education[]     // [captured]
  anti_preferences: str[]          // [captured]
  country:          str            // [captured]

  // shared skill bucket (Tier 3) — defined ONCE, referenced by roles
  primary_skills:   Skill[]        // [captured-shape, simplified] see A.3

  // compensation anchor (Tier 3) — [designed], DECIDED 2026-05-29
  base_salary: {
    amount:   num
    currency: str           // e.g. "USD"
    period:   "year" | "hour"
  }
  // base_salary = the candidate's CURRENT/REFERENCE comp (DECIDED 2026-05-29) — an anchor,
  // NOT a desired floor. Roles A) seed target_salary from it; B) the feed shows each posting's
  // delta vs it ("+20% vs base").

  // shared Tier-2 defaults a role may override (sparse override on the role side)
  defaults: {
    seniority:            str       // [captured]
    preferred_industries: str[]     // [captured]
  }
}

Education { degree_type: str, degree_field: str, school: str, graduation_year: int }   // [captured]
```

### A.3 `Skill` — member of `Candidate.primary_skills`  **[captured-shape, simplified 2026-05-29]**

```
Skill {
  id:    str     // [designed] STABLE id — required so roles can reference it; text key too fragile
  name:  str     // was `description`
  years: int     // was `years_active`
}
// `active` boolean from the legacy shape is DROPPED. No per-skill weight anywhere.
```

Referenced by `Role.applicable_skills` (binary on/off, see A.4).

### A.4 `Role` — one per target (SWE, Data Engineer, Platform, …)  **[designed]**

```
Role {
  id:     str
  name:   str
  color:  str            // identity color used across the shell
  active: bool           // false = paused (stops ingesting; not deleted)

  // ── Tier 1 — target-defined (no shared base) ──
  search_what:   str               // the core query — this *is* the role
  prefilter: {
    title_include: str[]
    title_exclude: str[]
  }
  threshold:     num               // 0–10, min score to surface
  scoring_notes: str[]             // prose to the LLM — where "weigh Spark higher" lives

  // ── per-role attributes ──
  target_salary:     num           // seeded from candidate.base_salary, then editable
  applicable_skills: str[]         // BINARY refs into candidate.primary_skills[].id
  default_resume_id: str?          // the role's linked "matching resume" (→ Resume.id)

  // ── Tier 2 — shared default w/ override (SPARSE: present key = override; absent = inherit) ──
  overrides: {
    seniority?:            str
    preferred_industries?: str[]
  }
}
```

`location` / `distance` / `work_arrangement` / `job_types` are deliberately **absent** — they are
global (A.5), not per-role.

### A.5 `JobPreferences` — singleton, global  **[designed]**

```
JobPreferences {
  locations: Location[]                       // multiple willing-to-work places
  radius_km: num                              // SINGLE global radius applied to every location (DECIDED 2026-05-29)
  work_arrangement: ("onsite"|"hybrid"|"remote")[]    // multi-select HARD PULL FILTER
  job_types: ("contract"|"contract_to_hire"|"full_time"|"part_time"|"internship")[]   // multi-select HARD PULL FILTER
  max_days_old: int?                          // [captured legacy `search.max_days_old`] global freshness gate (DECIDED 2026-05-29: global)
}

Location { label: str, lat?: num, lng?: num }  // NO per-location radius — radius is global (above)
```

These apply to **every** role's search equally and **cannot be overridden** by a role.
`work_arrangement` and `job_types` are **hard pull filters** (DECIDED 2026-05-29) — they exclude
non-matching postings *at ingestion / before LLM scoring*, mapping to legacy `require_contract_time`
/ `require_contract_type`. Not soft scorer signals.

### A.6 `Resume`  **[designed]** — new "Resume Management" functionality

```
Resume {
  id:          str
  label:       str            // e.g. "SWE — backend focus v3"
  role_id:     str?           // tailored for which Role (null = generic / base resume)
  source:      "uploaded" | "generated" | "edited"
  content_ref: str            // pointer to stored file/blob
  created:     datetime
  updated:     datetime
}
```

A `Role.default_resume_id` points to the resume attached by default when applying under that role.
The specific resume *used for a given application* lives on the **Application** (A.7), so one role
can still send different resumes to different postings.

### A.7 Per-application resume — LINK ONLY, for now  **[designed]** (DECIDED 2026-05-29)

**Decision:** do **not** build a full `Application` join entity yet. Model the per-application resume
as a simple **`applied_resume_id` reference on the Job** (alongside its existing applied state). User's
words: *"For now link to a resume id."*

```
// On Job (A.8): when user_state === "applied"
applied_resume_id: str?     // → Resume.id — the resume used for THIS posting (null = none chosen)
```

This satisfies *"create and store per-job-application resumes"* at the lightest weight: a job pursued
under a role can carry the specific resume it was sent with, without a separate entity. A richer
`Application` record (status pipeline: interviewing / rejected / offer / withdrawn, applied_at, notes)
is the **natural upgrade** when application *tracking* becomes a feature — captured here as the
deferred path, not built now.

```
// DEFERRED — promote to this when application tracking is scoped:
Application { id, job_id, role_id, resume_id, status, applied_at, notes }
```

### A.8 `Job` — a scraped posting (a "snippet" before it's scored)  **[captured-shape]**

```
Job {
  id:            str
  title:         str
  company:       str
  location:      { label: str }
  remote_type:   "onsite" | "hybrid" | "remote" | null
  contract_type: str | null
  salary:        { min?: num, max?: num, currency: str, period: "year"|"hour" } | null
  source:        str          // LinkedIn, Indeed, Greenhouse, Lever, HN, Wellfound, …
  posted_at:     datetime
  ingested_at:   datetime
  state:         "snippet" | "scored"   // snippet = discovered, not yet LLM-scored

  // per-role scoring — a job can match multiple roles (drives Combined view)
  matches: Match[]

  user_state:    "new" | "bookmarked" | "applied" | "dismissed"
  applied_resume_id: str?     // → Resume.id, set when applied (per-application resume, A.7)
}

Match {                       // [captured: score/skills/verdict are the live card's data]
  role_id:        str
  score:          num         // 0–10, tier: hi 8+, mid 5–7, lo <5
  matched_skills: str[]       // skill ids (or names) present in the posting
  missing_skills: str[]
  verdict:        str
  overridden_via: str[]       // which Tier-2 overrides applied — combined-view marker (§6 rebuild)
}
```

Job field shapes should be **verified against the live ingest/scoring code** when persistence work
begins — the card UI confirms `score / matched / missing / verdict / source / snippet-state`, but
the exact `salary` shape (needed for the comparison feature) must be checked, not assumed.

### A.9 Relations (summary)

| From | → To | Cardinality | Mechanism |
|---|---|---|---|
| Candidate | Skill | 1 → * | owns `primary_skills[]` |
| Role | Skill | * ↔ * | `applicable_skills[]` (binary id refs) |
| Candidate | Role | 1 → * | owns roles |
| Candidate | Resume | 1 → * | owns resumes |
| Resume | Role | * → 0..1 | `role_id` (tailored-for) |
| Role | Resume | 1 → 0..1 | `default_resume_id` (linked default) |
| Job | Resume | * → 0..1 | `applied_resume_id` (resume used for this application — A.7 link-only) |
| ~~Application~~ | ~~Job / Role / Resume~~ | *deferred* | join entity not built yet (A.7) |
| Job | Match | 1 → * | per-role scoring |
| JobPreferences | Job | 1 → * | global filter on ingestion |
| Candidate.base_salary | Job.salary | derived | comparison % (A.10) |

### A.10 Derived / computed values (not stored)

1. **Effective Tier-2 value:** `effective(role, field) = role.overrides[field] ?? candidate.defaults[field]`.
2. **Effective skill set for a role:** `candidate.primary_skills.filter(s => role.applicable_skills.includes(s.id))`.
3. **Combined view:** union of every `active` role's matched Jobs, de-duped by `job.id`, each tagged
   with the role(s) whose `Match` surfaced it; overridden matches carry the `overridden_via` marker.
4. **Salary delta vs base (NEW):**
   `delta = (jobSalaryPoint − candidate.base_salary.amount) / candidate.base_salary.amount`,
   rendered as e.g. `+20% vs base`. Requires currency/period normalization; ranges use the midpoint.
   Anchor = `candidate.base_salary`; an optional secondary comparison vs `role.target_salary` is
   possible but not the default.
   **No-salary postings (DECIDED 2026-05-29): a missing/unextracted salary is a "RED FLAG," NOT a
   hard filter.** The posting still surfaces in the feed, visibly flagged (e.g. a red "no salary"
   marker in place of the delta) rather than dropped. The UI **may offer an opt-in filter** to hide
   jobs without an extracted salary, but that is a user-toggled view filter — never automatic
   exclusion at ingestion.

---

## 1. The structural reality today

- **There is exactly one profile.** No "target" or "role" concept exists yet — multi-target is
  genuinely new work, not a refactor of an existing list.
- **A profile's definition is split across two files**, and the `/profile` form fuses them in the UI:

  | File | Owns | Nature |
  |---|---|---|
  | `config/profile.json` | Who the candidate *is* (skills, education, seniority, location) | Candidate identity |
  | `config/config.json` | What jobs to *find & score* (search, prefilter, threshold) | Search / match criteria |

- The `/profile` form (`web/profile.py`) deep-merges only the **candidate-facing subset** of
  `config.json` and leaves technical keys (`results_per_page`, `max_pages`, etc.) untouched.
- A **PDF resume import** path (`/profile/import-pdf`) LLM-extracts `primary_skills`, `education`,
  `seniority`, `preferred_industries`, and `location_center` to pre-fill the form.

---

## 2. Full field inventory (current codebase — [captured])

### From `profile.json` — candidate identity  (anchor: `web/profile.py:163-177`)

| Field | Shape | Notes |
|---|---|---|
| `primary_skills` | `[{description, years_active:int, active:bool}]` | 3-column skills table — **not** flat strings. `active` = currently using it. *(Redesign simplifies → `{id, name, years}`; see A.3.)* |
| `anti_preferences` | `[str]` | Things to avoid (repeating rows). |
| `education` | `[{degree_type, degree_field, school, graduation_year}]` | Structured; legacy free-text auto-migrated on load. |
| `seniority` | `str` | Free text / select. |
| `preferred_industries` | `[str]` | Repeating rows. |
| `location` | `{center, radius_km:float, geocode_fallback, notes}` | `geocode_fallback` defaults to `"pass"`. *(Redesign splits → current_location (identity) + global locations[].)* |
| `scoring_notes` | `[str]` | Free-form instructions fed to the LLM scorer. |

### From `config.json` — candidate-facing subset  (anchors: `config.example.json`, `web/profile.py:179-289`)

| Block | Fields | Notes |
|---|---|---|
| `search` | `country, what, where, distance (km), salary_min, max_days_old` | `what` / `where` are the core query. Technical keys `results_per_page`, `max_pages` are left untouched by the form. |
| `scoring` | `threshold` (0–10) | Minimum score to appear in the feed. |
| `prefilter` | `title_include[], title_exclude[], require_contract_time, require_contract_type` | Case-insensitive title substring gates applied *before* LLM scoring to save cost. |

---

## 3. The multi-target model — DECISION (2026-05-29)

**Tier model: shared core with per-role override, plus inherently per-role fields.**
Confirmed by user: *"a split, with the Core items being shared with the option of an override."*

Three role tiers, **plus a global layer that sits outside the role model entirely.** The global
search preferences below are not per-role and **cannot be overridden by a role** — they apply to
every role's search equally.

### Global search preferences (outside the role tiers; not per-role, not overridable) — DECIDED 2026-05-29

User's words: *"Location and Job Type should be two more fields that are completely separate from
the Roles. They are search preference parameters that should be configurable but not linked to
specific Roles."* These describe **where** and **how** the candidate is willing to work — true of
the person's job search as a whole, not of any one target. Normative shape: see **A.5**.

- **`locations[]` — multiple acceptable locations.** Replaces the legacy single `location.center` +
  `radius_km`. (e.g. *"fine moving to California or Seattle, or staying where I am"*.)
- **`work_arrangement` — multi-select over {onsite, hybrid, remote}.**
- **`job_types` — multi-select over {Contract, Contract-to-Hire, Full-Time, …}.** Maps to the legacy
  prefilter `require_contract_time` / `require_contract_type`, lifted to a global preference.

**This supersedes two earlier placements** (both moved here, both no longer per-role):
- `location` (center/notes) and `search.distance` / `location.radius_km` were **Tier 2** — now global,
  **not role-overridable**. The earlier "a remote-only role may override location" rationale is
  replaced by the global `work_arrangement` toggle.
- `require_contract_time` / `require_contract_type` were implied per-role prefilter gates — now global.

### Tier 1 — Target-defined (always per-role; no shared base)
- `search.what` — the core query; this *is* the role.
- `prefilter.title_include[]` / `title_exclude[]` — role-specific title gates.
- `scoring.threshold` — each role can demand a different match bar.
- `scoring_notes[]` — role-specific scoring guidance to the LLM.

### Tier 2 — Shared with override (candidate default, role may override)
Defaults live on the shared candidate base; a role can override the value for itself. The UI shows
the inherited value with an explicit "override for this role" affordance + a way to revert.

- `seniority`
- `preferred_industries[]`
- *Skill applicability (per-role visibility set)* — **DECIDED 2026-05-29.** The candidate's
  `primary_skills` are a single shared bucket (Tier 3). Each role carries a **visibility set**: refs
  to shared skill IDs "turned on" for that role. Defined once, reused — never duplicated — each role
  exposes only its tailored subset (SWE → {X, Z}; Data → {Y, Z}). Per-role membership is **binary**
  (`applicable: true|false`); **no per-role numeric weighting** — emphasis goes through `scoring_notes`
  prose. User's words: *"shared bucket where you turn on the visibility of a skill to a role type…"*
  and *"No weighting per role… instruct the LLM to weigh relevant skills higher."*

> **Moved out of Tier 2 (do not treat as overridable):**
> - ~~`salary_min`~~ → **per-role `target_salary`** (Roles), seeded from `candidate.base_salary` (§0, A.4).
> - ~~`search.distance` / `location.radius_km`~~ and ~~`location` (center/notes)~~ → **Global** (A.5).

### Tier 3 — Shared only (candidate identity; never per-role)
- `primary_skills[]` — simplified to **`{id, name, years}`** (A.3); `active` dropped.
- `education[]`
- `anti_preferences[]`
- `country`
- **`base_salary`** (new — comparison anchor + role-salary seed, §0/A.2)
- Contact / identity fields (incl. **current_location**, **current_role**)

---

## 4. Gaps in the current prototype Roles screen (to fix when UI work resumes)

The prototype's Roles editor invented a thin field set and **missed or misrepresented** real schema:

- **Missing:** `anti_preferences`, `education`, `scoring_notes`, prefilter `title_include`/`title_exclude`,
  `seniority`, `preferred_industries`.
- **Misrepresented skills:** the editor duplicates a skill set *into* each role with invented
  must-have/weighted/nice-to-have tiers. Real model = **one shared `primary_skills` bucket**
  (`{id, name, years}`), each role holding only a **binary visibility set** of references (A.4). The
  editor must **select-from-shared**, not re-author skills per role.
- **Ignores the tier model:** treats every field as flatly per-role; no shared-default/override
  distinction.
- **Wrongly per-role: location.** `locations[]`, `work_arrangement`, `job_types` are **global**
  (Job Preferences surface), not role fields.
- **Salary unmodeled correctly:** the prototype's per-role salary is fine *as a per-role field*, but
  it must be **seeded from `candidate.base_salary`** and the feed must show the **delta-vs-base**
  comparison (A.10) — neither exists yet.
- **No Resume / Application model:** the linked "matching resume" (`Role.default_resume_id`) and
  per-application resumes (`Application`) aren't represented anywhere in the prototype.

---

## 5. Resolved decisions + open items

### Resolved (2026-05-29)

- **Three top-level categories** — Candidate Profile · Roles · Job Preferences (§0). Skills fold into
  Candidate Profile; Resumes fold into Roles; Job Preferences is the global search-prefs surface.
- **Skill model** — one shared bucket `{id, name, years}` (Tier 3); roles hold a **binary visibility
  set** of references; no per-role weighting (emphasis via `scoring_notes`). Stable skill `id` required.
- **Location & Job/Contract Type — global, not per-role.** `locations[]`, `work_arrangement`, `job_types`.
- **Target salary — per-role**, seeded from `candidate.base_salary`.
- **Base salary — Candidate Profile field, dual-purpose (NEW 2026-05-29):** comparison anchor for the
  feed (*"+20% vs base"*) **and** the seed for new-role `target_salary`. Resolves the prior
  "shared salary default?" open refinement — **yes, it seeds; editable per role.**
- **Resumes & Applications modeled (NEW 2026-05-29):** `Resume` (A.6) with a per-role `default_resume_id`
  link, and `Application` (A.7) joining Job + Role + Resume + status — the home for *per-application
  resumes*.
- **Override UX — inline**; **Manage-skills surface — dedicated** (now under Candidate Profile);
  **Combined-view override labeling — yes, clutter-gated.** (See `roles-editor-rebuild.md §6`.)

### The "rock solid" checklist — ALL LOCKED (2026-05-29)

The six open items below are now decided. **No open model questions remain — the schema is locked
for UI work.**

1. ✅ **`base_salary` semantics → CURRENT/REFERENCE comp** (the comparison anchor), not a desired
   floor. (A.2)
2. ✅ **Radius → SINGLE global radius** applied to every location. No per-location radius;
   `Location` is just `{label, lat?, lng?}`. (A.5)
3. ✅ **Per-application resume → LINK ONLY for now** — an `applied_resume_id` reference on the Job,
   *not* a full `Application` join entity. The join entity is the documented deferred upgrade for
   when application *tracking* is scoped. (A.7/A.8)
4. ✅ **`work_arrangement` / `job_types` → HARD PULL FILTERS** — exclude non-matching postings at
   ingestion / before LLM scoring. Not soft scorer signals. (A.5)
5. ✅ **Job `salary` — no-salary is a RED FLAG, not a hard filter.** Postings without an extracted
   salary still surface, visibly flagged; the UI may offer an opt-in filter to hide them. Range
   postings use the midpoint. *(Live posting `salary` shape should still be verified against the repo
   at the moment delta-vs-base persistence is built — A.8/A.10.)*
6. ✅ **`max_days_old` → Job Preferences (global).** (A.5)

---

*Update this file as the model evolves. §A is normative (UI codes against it); §1–§3 capture the
real repo with `file:line` anchors; keep both honest. Companion: `roles-editor-rebuild.md`
(build plan), `design-principles.md` (layout rules).*
