# job-matcher — high-level API surface (root resources)

> **Purpose.** A high-level map of the API the redesigned job-matcher needs — **root resources and
> the operations they expose**, not specific paths or payload schemas. It exists to *seed* endpoint
> design: it names the resources, says whether each is a singleton or a collection, lists the
> domain actions beyond plain CRUD, and flags the genuine API-shape decisions still open.
>
> **Grounded in:** `docs/data-model.md §A` (the normative entity model — every resource below maps to
> an entity there) and `docs/ui-layout.md` (the screens each resource backs). Repo reality (the
> current Flask routes) is anchored to `I:\career\job-matcher` where cited.
>
> **Scope guard.** Root endpoints only. Where this doc says "actions," treat them as *capabilities the
> resource must support*, not finalized verbs/paths — those are the next level down.

---

## 1. Assumptions & conventions

These shape every resource below; if one is wrong, the map shifts — so they're stated up front, not buried.

- **Single-user today.** The live app has exactly one profile (`data-model.md §1`). So **Candidate**
  and **JobPreferences** are **singletons** — one resource instance, no ID, no list. Multi-user
  (would scope everything under a user/account) is an **open decision** (§6), not assumed here.
- **Three resource families.** *Config* (what the user sets up), *Content* (the data that flows
  through — postings & resumes), *Runtime/Admin* (the scraping + scoring pipeline and its controls).
  This mirrors the three-category IA (`data-model.md §0`) plus the Admin surface (`ui-layout.md §7`).
- **The pipeline is asynchronous.** Ingest + LLM scoring are long-running (the live app already
  streams an ingest drawer). So pipeline endpoints are **trigger + observe**, not request/response —
  a `/jobs` read returns *current* state; making more jobs appear is an `/ingest` action you watch.
- **Derived values are computed server-side and returned inline** (recommended — see §4/§6.1). A `Job`
  comes back already carrying its salary-delta and per-role match data; a `Role` can be asked for its
  *effective* (override-resolved) values. The alternative (client merges raw rows) is flagged in §6.

---

## 2. Resource map (the heart of this doc)

| Root resource | Backing entity (`data-model.md`) | Shape | Core ops | Notable domain actions (beyond CRUD) |
|---|---|---|---|---|
| **`candidate`** | `Candidate` singleton (A.2) | singleton | read · replace · patch | import-from-PDF (LLM extract → prefill) |
| **`candidate/skills`** | `Skill` bucket (A.3) | sub-collection | list · add · edit · remove | — (referenced by roles; deleting must handle role refs) |
| **`roles`** | `Role` (A.4) | collection | list · create · read · update · delete | activate / **pause** · **duplicate** · read **effective** (resolved) values · scope feed to a role |
| **`preferences`** | `JobPreferences` singleton (A.5) | singleton | read · replace · patch | — (changes re-scope ingestion filters) |
| **`resumes`** | `Resume` (A.6) | collection | list · create · read · update · delete | upload · generate · link as a role's default |
| **`jobs`** | `Job` + `Match` (A.8) | collection (query-heavy) | list (filtered) · read | set **user_state** (bookmark/apply/dismiss) · attach **applied_resume_id** · **scrape** a snippet · query by **role / combined** |
| **`ingest`** | runtime over `Job.state` | process | trigger · observe | **live event stream** (user-facing bar) · **history log** (admin table) |
| **`sources`** | provider config (A.8 `source`) | collection | list · update | enable/disable · reorder scrape priority |
| **`models`** | LLM routing config | collection/config | read · update | per-stage model assignment · provider keys · token budget |
| **`stats`** | aggregates over `Job`/`Match` | read-only | read | filter global vs per-role |
| **`system`** | app-level ops | config + actions | read · update | maintenance: re-score · vacuum · export · purge |

> Singletons (`candidate`, `preferences`) and config blobs (`models`, `system`) are read-then-patch
> resources; the collections (`roles`, `resumes`, `jobs`, `sources`) are list/CRUD with the extra
> domain actions noted. `stats` is pure read.

---

## 3. Per-resource detail

### Config family

**`candidate`** — singleton; the identity source of truth.
Owns: contact, `country`, `current_location`, `current_role`, `education[]`, `anti_preferences[]`,
`base_salary`, and the Tier-2 `defaults` (`seniority`, `preferred_industries`). Two cross-cutting
roles make this resource load-bearing well beyond its own screen: `base_salary` is the **feed's
comparison anchor** (A.10) and the **seed** for each new role's `target_salary` (A.4). The legacy
**PDF-import** path (`web/profile.py:/profile/import-pdf`) is a real action to carry forward.
*Skills* are a sub-collection (`candidate/skills`) because roles reference them by stable `id` (A.3) —
they need their own add/edit/remove lifecycle, and deletion must reckon with roles that reference the skill.

**`roles`** — collection; the multi-target core (genuinely new — no equivalent in the repo today).
Each role owns its Tier-1 query fields, `target_salary`, the **binary `applicable_skills` ref set**,
`default_resume_id`, and the **sparse `overrides`** map. Beyond CRUD it needs: **pause** (`active:false`
— stops ingesting without deleting), **duplicate** (clone as a draft), and — important for the UI —
a way to read a role's **effective values** (overrides resolved against candidate defaults, A.10.1).
Switching the *active* role to re-scope the feed is a read concern handled via `jobs` query params (§4), not a write here.

**`preferences`** — singleton; global search prefs (A.5). `locations[]` + single global `radius_km`,
`work_arrangement`, `job_types`, `max_days_old`. These are **hard pull filters** (A.5) — editing them
changes *what gets ingested at all*, so a write here has pipeline consequences (re-ingest / re-filter),
not just a stored-preference change.

### Content family

**`resumes`** — collection; the "Resume Management" feature (A.6). CRUD plus **upload** and
**generate** sources. A resume may be tailored to a role (`role_id`) and may be a role's linked
default (`Role.default_resume_id`).

**`jobs`** — collection; the feed, and the busiest resource. Reads are **query-driven**:
filter by a single role, by **combined** (union of all active roles' matches, de-duped — A.10.3),
by `user_state`, and by completeness (full vs **snippet**, the salary red-flag filter — A.10.4).
Writes are **state transitions on a posting**, not edits to it: set `user_state`
(bookmark / apply / dismiss), attach `applied_resume_id` on apply (A.7), and **scrape** a snippet
(promote `state: snippet → scored`). Each returned job carries its `matches[]` and computed
**salary delta** (§4). The Job `salary` shape must be **verified against the live ingest/scoring code**
before the delta feature is built (A.8 — flagged, not assumed).

### Runtime / Admin family

**`ingest`** — the scraping process, exposed two ways that share one event vocabulary (`ui-layout.md`
hybrid ingest log): a **live event stream** (the user-facing bottom bar — discovered/scored/deduped/error
events as they happen) and a **searchable history log** (the admin analytics table). Trigger-and-observe,
not request/response.

**`sources`** — provider config (LinkedIn, Indeed, Greenhouse, Lever, HN, Wellfound …). List + update,
with **enable/disable** and **reorder** (scrape priority — the live app's Sortable.js provider list).

**`models`** — LLM routing: per-stage model assignment (scoring / extraction / dedup / resume-tailoring),
provider keys, token budget. Config read/update.

**`stats`** — read-only aggregates over jobs/matches (ingested / scored / high-match / applied / apply-rate
/ avg-score), global or per-role.

**`system`** — app-level schedule + storage facts and **maintenance actions**: re-score, vacuum, export,
and the destructive purge/wipe operations (the "danger zone").

---

## 4. Cross-cutting derivations (where the model does real work)

These are the computed behaviors (A.10) the API must serve. They're the reason "just CRUD the entities"
isn't enough.

- **Effective Tier-2 values.** `effective(role, field) = role.overrides[field] ?? candidate.defaults[field]`.
  A role's *stored* shape is sparse; its *effective* shape needs the candidate merged in. **Decision point
  in §6.1** — does the API resolve this (return effective values) or hand back raw rows for the client to merge?
- **Effective skill set per role.** `candidate.primary_skills.filter(s ∈ role.applicable_skills)` (A.10.2).
- **Combined view.** Not stored — a runtime union of every `active` role's matched jobs, de-duped by
  `job.id`, each tagged with the role(s) that surfaced it (A.10.3). Best modeled as a **query mode on
  `jobs`** (e.g. a `combined` scope), not a separate resource — §6.2.
- **Salary delta vs base.** `(jobSalaryPoint − base_salary) / base_salary` → "+20% vs base" (A.10.4).
  Needs currency/period normalization; ranges use the midpoint. **No-salary = red flag, not a filter** —
  the job still returns, flagged. Where normalization happens is part of §6.1.
- **Hard pull filters.** `work_arrangement` / `job_types` / `max_days_old` constrain ingestion *before*
  scoring (A.5) — they belong to the `ingest` + `preferences` boundary, not to a post-hoc `jobs` filter.

---

## 5. UI screen → resource traceability

So the endpoint design stays anchored to what the screens (`ui-layout.md`) actually call:

| Screen | Primary resource(s) |
|---|---|
| Feed (per-role & Combined) | `jobs` (query: role / combined / state / completeness) |
| Inspector (job detail + apply) | `jobs` (read + state/apply), `resumes` (pick) |
| Candidate Profile | `candidate`, `candidate/skills` |
| Roles editor | `roles` (+ reads `candidate/skills`, `resumes` for linking) |
| Job Preferences | `preferences` |
| Ingest bar (live) / Admin ingest log | `ingest` (stream / history) |
| Admin → Job Sources | `sources` |
| Admin → LLM & Models | `models` |
| Admin → Stats | `stats` |
| Admin → System | `system` |

---

## 6. Open API-design decisions (flag, don't invent)

The model is locked; these are **API-shape** choices the model doesn't dictate. Each needs a call
before path/payload design. (Listed with a lean where I have one — none are decided.)

1. **Tier resolution: server-side vs client-side.** Recommend **server-side** — endpoints return
   effective (resolved) values and computed deltas inline, so each client/screen doesn't re-implement
   the inheritance + salary math. Raw-row alternative pushes that logic to every consumer. *Lean: server-side.*
2. **Combined view: query mode vs dedicated resource.** Recommend a **scope/param on `jobs`**
   (`combined` vs a single role) rather than a separate `/combined` resource — it's the same Job data,
   merged differently. *Lean: query mode.*
3. **Ingest contract: how `trigger → observe` is shaped.** Polling a task status vs a push/stream
   (SSE/websocket) for the live bar. The live app already streams, which argues for push. *Lean: stream.*
4. **Single-user singleton vs multi-user.** If multi-user is on the roadmap, `candidate` /
   `preferences` stop being singletons and everything scopes under an account — cheaper to decide now
   than to re-root later. *No lean — depends on product intent; worth your call.*
5. **Snippet promotion: explicit action vs automatic.** Is "scrape this snippet" a user-triggered
   action on a job, a background pass, or both? Affects whether `jobs` needs a write action or just reflects pipeline state.
6. **Salary normalization home.** Currency/period normalization for the delta — done at ingestion
   (stored normalized) or at read (computed per request)? Ties to decision #1.

---

*Companion docs: `docs/data-model.md` (normative entities — the source for every resource here),
`docs/ui-layout.md` (screens these resources back), `docs/design-principles.md` (layout rules).
Update this file if the data model or IA changes.*
