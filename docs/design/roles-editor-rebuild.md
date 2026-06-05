# Roles editor — rebuild scope

> **Purpose.** Scope (not yet build) the rebuild of the **Profile › Roles** editor in
> `job-matcher-shell-b-2.html` so it reflects the *real* schema and the locked tier/skill model.
> Anchored to `docs/data-model.md` (data model) and `docs/design-principles.md` (layout rules).
>
> Scoped: 2026-05-29. Status: **awaiting go-ahead before any UI change.**

---

## 1. Why rebuild (not patch)

The current Roles editor invented its own field set and skill model. Per `data-model.md §4`, it:

- **Misses** real fields: `anti_preferences`, `education`, `scoring_notes`, prefilter
  `title_include` / `title_exclude`, `seniority`, `preferred_industries`.
- **Misrepresents skills** — it duplicates a skill set into each role with invented
  must-have / weighted / nice-to-have tiers. The real model is one **shared bucket** + a per-role
  **binary applicable** flag.
- **Ignores the tier model** — it treats every field as flatly per-role, with no shared-default /
  override distinction.

These are structural, not cosmetic — the data model the editor edits is wrong. A rebuild is cleaner
than retrofitting override semantics and a shared-bucket skill control onto the invented structure.

---

## 2. The data model the editor must edit

Two objects, per `data-model.md §3`:

### Shared candidate base (one, global)
```
candidate = {
  primary_skills: [ { id, name, years } ],   // ← shared bucket; {id,name,years} only
  education:        [ { degree_type, degree_field, school, graduation_year } ],
  anti_preferences: [ str ],
  country:          str,
  current_location: { label, lat?, lng? },   // home/base = distance origin
  current_role:     str,                     // what they do today (≠ target roles)
  base_salary:      { amount, currency, period },  // comparison anchor + seeds role target_salary
  defaults:         { seniority, preferred_industries },  // Tier-2 shared defaults
  // identity/contact…
}
```
Full normative shape (incl. Resume / Application / Job entities and relations): `data-model.md §A`.

### Role (one per target: SWE, Data Engineer, Platform, …)
```
role = {
  id, name, color, active,        // active=false → paused (stops ingesting, not deleted)

  // Tier 1 — target-defined (no shared base)
  search_what:     str,           // the core query — this *is* the role
  title_include:   [ str ],
  title_exclude:   [ str ],
  threshold:       0–10,
  scoring_notes:   [ str ],       // ← where "weigh skill X higher" lives (prose to LLM)

  // per-role attributes
  target_salary:     num,         // seeded from candidate.base_salary, then editable
  applicable_skills: [ skillId ], // BINARY refs into the shared bucket; no per-role weight
  default_resume_id: str?,        // the role's linked "matching resume"

  // Tier 2 — shared default, role may override (SPARSE: present key = override)
  overrides: { seniority?, preferred_industries? }
}
```

**Tier-2 is now just `seniority` + `preferred_industries`.** `salary` is a per-role attribute
(`target_salary`, seeded from `candidate.base_salary`); `location` / `distance` / `work_arrangement`
/ `job_types` moved **out of the role entirely** to the global **Job Preferences** surface — they are
NOT in this editor. See `data-model.md §A.4` (normative Role) and `§A.5` (Job Preferences).

**Locked skill decisions (2026-05-29):** global skill = `{id, name, years}` only (`active` dropped);
role↔skill is **binary** `applicable`; **no per-role numeric weighting** — emphasis goes through
`scoring_notes` prose.

---

## 3. Screen layout

Keep the **master–detail** shape (it works), but correct the detail pane to the real model.
Apply `design-principles.md`: the editor is expanding form content → **left-aligned, fills the
column** (the ultra-wide cap-and-center watch item from that doc may apply to the detail form only;
flag at build, don't pre-decide).

```
┌ Roles ─────────────────────────────────────────────────────────────────────┐
│ ┌── role list ──┐ ┌── role editor (selected) ───────────────────────────┐  │
│ │ ● SWE      12 │ │  [SWE ▸ editable title]            [⏸ pause] [Save]  │  │
│ │ ● Data      9 │ │                                                       │  │
│ │ ● Platform  7 │ │  TARGET-DEFINED (this role only)                      │  │
│ │ ⊕ New role    │ │   • Search query (what)                               │  │
│ └───────────────┘ │   • Title include / exclude gates                     │  │
│                    │   • Match threshold (0–10)                            │  │
│                    │   • Scoring notes  ← "weigh K8s higher", etc.         │  │
│                    │   • Target salary  ← seeded from candidate base       │  │
│                    │   • Linked resume  ← default_resume_id                │  │
│                    │                                                       │  │
│                    │  SHARED — OVERRIDABLE (inherits candidate default)    │  │
│                    │   • Seniority / Preferred industries                  │  │
│                    │     — each w/ inline override toggle                  │  │
│                    │   (location/distance/work-model/job-type are GLOBAL,  │  │
│                    │    not here → Job Preferences surface)                │  │
│                    │                                                       │  │
│                    │  SKILLS APPLICABLE (from shared bucket, on/off)       │  │
│                    │   [✓ Python] [✓ AWS] [ ] Spark [✓ SQL] [ ] Airflow…   │  │
│                    │   + manage shared skills →                            │  │
│                    └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

Three labeled bands in the detail pane, matching the tiers — this makes the shared-vs-per-role
distinction legible instead of implicit.

---

## 4. The two novel controls

1. **Shared-skills applicability.** The role shows the *whole shared bucket* as toggle chips; checked
   = `applicable` for this role. Toggling never edits the skill itself. A "manage shared skills" link
   opens the one place skills are authored (add/rename/set years) — likely a small section or modal
   that writes the candidate bucket, so every role sees the change. The chip's label shows
   `name · {years}y`; no weight UI.

2. **Override affordance (Tier 2).** Each shared-default field renders its inherited value with an
   "override for this role" toggle. Overridden → field becomes editable + shows a "revert to shared"
   action. Un-overridden → read-only, visibly inherited. (Inline pattern — locked in §6.)

---

## 5. Build phases (when greenlit)

1. **Data layer** — replace the invented role objects with the §2 shape; give shared skills stable
   `id`s; seed SWE/Data/Platform with realistic per-tier values.
2. **Detail pane bands** — render the three tier bands; wire target-defined fields first (they're the
   simplest, no inheritance).
3. **Shared-skills control** — bucket chips + applicable toggles + "manage shared skills".
4. **Override mechanics** — inherited display, override toggle, revert.
5. **List + lifecycle** — role list counts, pause, new/duplicate drafts, Save.
6. **Self-check** — checklist + 5-dim critique; confirm dark-ledger tokens, density, alignment rules,
   `data-od-id`, localStorage target persistence all intact.

Single-file SPA stays (live switching + shell recolor depend on it).

---

## 6. UX decisions (resolved 2026-05-29)

- **Override UX — INLINE.** Each Tier-2 field renders its inherited value in place with an
  "override for this role" toggle; overriding makes that one field editable + shows "revert to
  shared". No separate overrides sub-section. Keeps each field's context next to its control.
- **Manage-shared-skills surface — DEDICATED, now under Candidate Profile.** Skills are authored on
  their own surface, not a modal buried in one role's editor. The role editor's applicability chips
  link out to it. Rationale: it edits candidate-global data, so it deserves a first-class surface —
  and every role reads from the same bucket, so it shouldn't feel owned by one.
  - *Updated by the three-category IA (`data-model.md §0`, 2026-05-29):* the rail is now **three
    top-level config destinations — Candidate Profile · Roles · Job Preferences** (not the earlier
    "Profile › Roles · Skills · Resumes"). **Skills live inside Candidate Profile** (skills are part
    of the candidate); **Resumes live inside Roles** (each role links its matching resume). So the
    "manage shared skills" chip links into **Candidate Profile › Skills**, and the global
    location/work-model/job-type fields live on the new **Job Preferences** destination — neither is
    in the Roles editor.
- **Combined view labeling — YES, but clutter-gated.** When a job matched under a role's *overridden*
  Tier-2 value, the combined feed should surface it — but quietly. Decision: **a subtle marker, not a
  verbose string.** Default to a small superscript/dot or an "override" micro-pill on the role color
  flag, with the detail ("matched via SWE · salary floor overridden") deferred to the inspector on
  click. If even the micro-marker reads busy in the dense feed, fall back to inspector-only. Build it,
  judge clutter against the live feed at self-check, and dial back if it competes with the score tiers.

*All three open questions from the prior scope are now settled. No open model questions remain for
the Roles editor — the rebuild is unblocked.*

---

*Update alongside `data-model.md` if the model shifts. This is the build plan for the Roles screen;
anchor the implementation to it once the user greenlights.*
