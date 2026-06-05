---
title: job-matcher 2.0 — Cycle 2 (API + Shell-B UI overhaul) implementation plan
touches:
  - web/**
  - services/**
  - db/**
  - templates/**
  - static/style.css
  - static/**
  - docs/design/**
  - docs/STYLE_GUIDE.md
  - tests/**
  - conftest.py
skills_relevant:
  - python
  - frontend-design
  - claude-github-tools:github-actions
tracking: { epic: 751, milestone: 12, cycle: 749, depends_on: [747, 748] }
---

# job-matcher 2.0 — Cycle 2 (API + Shell-B UI overhaul) — implementation plan

> **Plan only — do not implement.** This decomposes Cycle 2 (`glitchwerks/job-matcher#749`)
> into shippable slices with per-slice design-fidelity gates and cross-cycle drift controls,
> and proposes a set of GitHub sub-issues for the router to file under milestone #12.

> **REVISED 2026-06-04 (post project-reviewer + inquisitor; Slice P added).** This revision absorbs a
> constructive project-reviewer pass and an adversarial inquisitor pass, all findings re-verified
> against the LIVE tree before integration. **Slice P (early backend-less prototype, #776) was added per
> user request** — it is backend-independent and runs in parallel with Cycles 0/1 and Slice 0, gated
> only on vendor PR #765 (needs `docs/design/*`); see §4 and §6. The 8-slice decomposition **survived**
> (still S0–S8); the changes harden
> Slice 0's exit criteria and re-scope two slices rather than re-cutting the work. Summary of what
> changed:
> - **Slice 0 grew four hard gates** (was prose / partly-missing): (a) an **all-paths chokepoint
>   enumeration** — verified there are **five** card-render routes, not two (`/`, `/feed/fragment`,
>   `/bookmarks`, `/applied`, **plus `/snippets` which is a SEPARATE full HTML page**, `web/feed.py:L240-L287`,
>   `templates/snippets.html:L66-L74`); (b) an **executable schema-conformance test** asserting the
>   Cycle-0/1 tables/columns/types + the D19 best-fit query exist before any slice's fidelity gate opens;
>   (c) a **single shared effective-value resolver** (`services/api/effective.py`) with a cross-consumer
>   contract test welding ingest/feed/editor; (d) a **service-layer error contract**.
> - **`test_feed_card_markup_single_source` re-specified** to assert against the REAL include graph
>   (`_card.html` is `{% include %}`-ed by THREE files today: `index.html:L114`/`:L137`,
>   `snippets.html:L71` — verified), so #580/#581/#582 close only on an honest green.
> - **Slice 5 hardened**: `lifecycle IS NULL` defensive anomaly check + test (D19 filters
>   `WHERE l.lifecycle='scored'`, `roles-foundation-design.md:L445` — a NULL row silently vanishes);
>   mixed JSONB-`matches` ↔ TEXT-JSON-`listings` join mapping carried into the service contract
>   (`roles-foundation-design.md:L266-L267`, ADR-005 scope note `:L105-L122`); `salary_mode` branch.
> - **Slice 7 re-scoped**: SSE is **already built and tested** (`/ingest/stream`, `MAX_SSE_CONNECTIONS=2`,
>   Last-Event-ID replay, `EventSource` client, dedicated `tests/test_ingest_stream.py` +
>   `tests/test_ingest_integration.py` — verified `web/ingest.py:L241-L295`,
>   `services/ingest_control.py:L108`). Slice 7 is now a UI re-surface + admin-log build, and explicitly
>   resolves the **subscriber-cap hazard** (multiple `EventSource` subscribers vs the hard cap of 2 → 429).
> - **New §1 row R6** (`salary_mode`/`floor_amount` ownership, spec §2.4 `:L144-L154`) and **new §8
>   decision** (salary-normalization home, api-surface §6 item 6 `:L176-L177`).
> - **Slice 3** gained an `updated_at`/ETag optimistic-lock save check (spec §2.7 `:L226-L228`) and a
>   committed-up-front three-way sub-cut (was conditional).
> - **Log host moved to Slice 8** (ui-layout §6.2 `:L218` puts the activity log under Admin → Job Sources);
>   Slice 7 owns only the event vocab + history data/query endpoint.
> - **Citation NITs fixed**: snippet-promotion anchored to `roles-foundation-design.md:L463` (O2) with the
>   open API-shape question separately noted at api-surface §6 item 5 `:L174-L175`; redundant fidelity
>   cite trimmed on Slice 1; Slice 8 scope guard excludes the Cycle-3 resume-tailoring routing row.
>
> **Provenance caveat (verified this session):** the OpenDesign docs (`docs/design/ui-layout.md`,
> `api-surface.md`, `data-model.md`, `design-principles.md`, `roles-editor-rebuild.md`) currently exist
> **only in the `.worktrees/vendor-opendesign-docs` worktree, NOT on `main`** (verified via Glob). Every
> `docs/design/*.md` citation below — and the Slice-0 deliverable that commits
> `docs/design/cycle2-reconciliation.md` — depends on that vendor-docs PR landing on `main` first. The
> router must confirm those docs are merged before Slice 0 starts; otherwise add the vendor-docs merge as
> a Slice-0 prerequisite.

## 0. Dependency & sequencing statement (read first)

**Cycle 2 cannot start until Cycles 0 (#747) and 1 (#748) land.** The Cycle 2 service layer reads
the `profile`, `skills`, `roles`, `job_preferences`, and `matches` tables created and seeded in
Cycle 0, and depends on the multi-role `matches` join authority established in Cycle 1
(`docs/superpowers/specs/2026-05-29-job-matcher-2.0-roles-foundation-design.md:L25-L26`,
`:L431-L459`). Specifically, the feed read authority moves to a best-fit `DISTINCT ON` Match query
in Cycle 1 (spec D19, `:L439-L449`); Cycle 2's feed surface builds directly on that query. Building
the rail/inspector/roles-editor against a schema that does not yet exist would be speculative.

**Exception — Slice P (backend-independent prototype, #776).** Slice P is explicitly not a
data-wired vertical slice. It uses hardcoded fixture context — no live schema, no `services/api/*`
calls — and is therefore **not blocked by Cycles 0/1 or Slice 0**. Its only gate is vendor PR #765
(the `docs/design/*` files must be on `main` before the prototype can be built to spec). Slice P
runs in parallel with the Cycle 0/1 critical path; its real Jinja templates are reused by Slices
1–8 when those slices swap fixtures for live service-layer output. See §4 (Slice P subsection) and
the dependency graph below.

**Authority precedence** (when sources disagree, higher wins):
1. The **LOCKED roles-foundation spec** model — `2026-05-29-job-matcher-2.0-roles-foundation-design.md §2`
   (NORMATIVE per its `:L45-L48`).
2. The **2.0 ADRs** — `2026-05-29-job-matcher-2.0-architecture-decisions.md` (constrain every cycle).
3. **OpenDesign `ui-layout.md`** — authoritative for **UI/IA only** (spec `:L50`).
4. OpenDesign `data-model.md` / `api-surface.md` / `design-principles.md` / `roles-editor-rebuild.md`
   — **bridging references** (spec `:L50-L52`); they lose to (1) on every model conflict below.

---

## 1. Reconciliation reality — the design↔model disagreements (the #1 risk)

The OpenDesign handoff and the LOCKED model disagree in known, enumerable ways. **The locked model
wins every time.** Slice 0's first deliverable is a committed delta doc that records each resolution
so no screen is built against a stale assumption. The disagreements:

| # | OpenDesign handoff says | LOCKED model says (wins) | Source of truth |
|---|---|---|---|
| R1 | `scoring_notes` / `anti_preferences` are role-only (or Candidate-only) | **Profile baseline + per-Role additions** (concatenated at scoring time) | spec D1/D2 `:L497-L498`, §4.5 `:L418-L419` |
| R2 | `Role.overrides` implied as flat fields | **Sparse map** — absent=inherit, present=override, removed=revert | ADR-010 `:L196-L210`; spec §2.3 `:L125-L127` |
| R3 | Combined view ambiguous (possible dedicated resource) | **Jobs query *mode*** — de-duped union, per-role pills; feed reads best-fit Match row | spec §4.6 D19 `:L439-L449`; data-model A.10.3; api-surface §6.2 |
| R4 | `state='snippet'` as the pre-scrape axis | **`lifecycle = discovered\|scored`**, ORTHOGONAL to existing `description_source` | spec §2.5 naming note `:L185-L201`, D11 |
| R5 | Salary handling underspecified | **No-salary = red-flag badge, never auto-drop**; salary delta vs base computed server-side | data-model A.10.4 `:L314-L323`; spec §2.4 `:L150-L154` |
| R6 | OpenDesign treats salary as a single display concern | **`JobPreferences.salary_mode` ∈ {`floor`,`display`} + `floor_amount`** is a SPLIT concern: `floor` is a **hard ingest drop** (Slice 4); `display` gates the **Slice-5 feed delta render**. Cycle-0 migration seeds `salary_mode='floor'` from legacy `salary_min` | spec §2.4 `:L144-L154`; migration §3.3 step 2 `:L291` |

These R1–R6 plus the five open `api-surface.md §6` API-shape decisions (see §8 below) are the
content of Slice 0's reconciliation deliverable. **No vertical UI slice may start until that doc is
committed and the §8 open API decisions are answered by the user.**

> **R6 ownership note (project-reviewer BLOCKING).** `salary_mode` crosses the Slice 4/5 boundary and
> had no owner in the prior draft. Resolution: **Slice 4** owns the `salary_mode`/`floor_amount`
> preference surface + the `floor` hard-filter semantic; **Slice 5** branches on it — render the
> delta-vs-base only when `salary_mode=='display'`, and surface (do not re-implement) the `floor`
> drop as a copy/badge cue. The `floor`-drop filtering itself lives at ingestion (spec §2.4 `:L151`),
> not in the Cycle-2 read path.

---

## 2. Current-state map (VERIFIED 2026-06-04)

I verified the brief's recon against the live tree. Findings that change scoping:

- **`web/__init__.py::create_app`** registers 5 blueprints at `url_prefix=""`: `feed`, `settings`,
  `profile`, `ingest`, `admin` (per CLAUDE.md § Architecture; consistent with `web/feed.py` header).
- **Card-render paths (#580/#581/#582) — VERIFIED, and there are FIVE, not two (inquisitor BLOCKING):**
  `_card.html` is rendered by **five distinct routes**, all confirmed in `web/feed.py`:
  | Route | Template | Card include site | In Slice-0 chokepoint? |
  |---|---|---|---|
  | `GET /` | `index.html` (feed branch) | `index.html:L114` | **YES** (deliverable 3) |
  | `GET /feed/fragment` | `_feed_fragment.html` | `_feed_fragment.html:L25` | **YES** (deliverable 3) |
  | `GET /bookmarks` | `index.html` (`{% else %}` branch) | `index.html:L137` | **decide in Slice 0** |
  | `GET /applied` | `index.html` (`{% else %}` branch) | `index.html:L137` | **decide in Slice 0** |
  | `GET /snippets` | **`snippets.html` — a SEPARATE full HTML page** with its own `<html>`/nav | `snippets.html:L71` (passes `show_snippet_badge=true`) | **decide in Slice 0** |
  - **#580 (duplicated card markup): PARTLY SOLVED — but worse than the brief framed.** `_card.html` is a
    single source, but it is `{% include %}`-ed by **THREE** template files —
    `index.html:L114`/`:L137`, `_feed_fragment.html:L25`, **and `snippets.html:L71`** (all verified). The
    **card itself is not duplicated**, but the `#feed-content` **wrapper body** (feed-meta count line +
    `card-list` loop + empty-state) is duplicated verbatim across `index.html:L96-L130`,
    `_feed_fragment.html:L7-L41`, **and** the bookmarks/applied `{% else %}` branch `index.html:L134-L164`,
    **and** `snippets.html:L65-L86`. So the chokepoint hole is wider than "two paths": the
    `test_feed_card_markup_single_source` grep assertion would find `_card.html` included by THREE files
    and either FAIL or be written loosely enough to launder the ADR-009 `:L189-L191` violation. **Slice 0
    must enumerate ALL five paths and decide each (see Slice 0 deliverable 3 + exit criteria).**
  - **#581 (filters lost on refresh): CONFIRMED OPEN.** `templates/index.html:L13-L14` fires
    `htmx.ajax('GET', '/feed/fragment', {target:'#feed-content', swap:'outerHTML'})` on
    `ingestComplete` and passes **no query string**, so `job_type`/`search`/`remote_only`/`sort`/
    `min_score` are dropped after every ingest refresh.
  - **#582 (duplicated query parsing): CONFIRMED OPEN.** `web/feed.py:L77-L94` (full `/`) and
    `web/feed.py:L136-L153` (`/feed/fragment`) are byte-identical param-parse blocks.
- **Services seam (ADR-008 base):** `services/profile_store.py`, `services/ingest_control.py`,
  `services/provider_schemas.py`, `services/pdf_import.py` exist, all Flask-free (CLAUDE.md
  § Architecture). This is the layer the new resource/service modules extend.
- **`db.py`** is monolithic, no-ORM; Cycle 0 splits it into a `db/` package (ADR-002, spec §3.2
  `:L263-L267`). Cycle 2's service layer calls the `db/` package, not raw `db.py`.
- **Biggest gaps (no existing surface):** left rail, right inspector, role concept, combined view,
  Job Preferences surface, Candidate Profile/Skills surface, salary-delta render.
  The Roles master–detail editor and the three-region grid are the major new builds.
- **SSE is ALREADY BUILT and tested (inquisitor MAJOR — corrects the brief's "new SSE bar" framing):**
  `GET /ingest/stream` exists (`web/ingest.py:L241-L295`) with `MAX_SSE_CONNECTIONS=2`
  (`services/ingest_control.py:L108`), a 429 on cap exceed (`web/ingest.py:L253-L254`), Last-Event-ID
  replay (`:L256-L274`), an `EventSource` client (`static/ingest-drawer.js`, included via
  `index.html:L170`), and dedicated SSE test files (`tests/test_ingest_stream.py`,
  `tests/test_ingest_integration.py`). **Slice 7 is therefore a UI re-surface + admin-log build, NOT a
  stand-up-SSE build** (see re-scoped Slice 7). The live cap of **2** is a real hazard for a multi-widget
  Shell-B design (bottom bar + top indicator + admin live log = ≥3 subscribers → third 429s).
- **Cycle-0/1 schema does NOT exist on `main` yet (inquisitor BLOCKING):** verified absence of the `db/`
  package (`db.py` is still the monolith), the `matches`/`roles`/`skills`/`job_preferences` tables, the
  `lifecycle` column, and `services/api/`. The §0 sequencing statement says "build after Cycles 0–1
  land" but the prior draft had **no Cycle-2-side executable check** that the schema landed as spec'd.
  Slice 0 now adds a schema-conformance test (deliverable 5) so any upstream type divergence
  (`applicable_skills` as Postgres `int[]` vs JSONB, `lifecycle` DDL-defaulted vs in-txn backfilled, the
  D19 result column set) fails the Slice-0 PR loudly instead of silently corrupting all 8 slices.
- **CI gates (VERIFIED `.github/workflows/ci.yml:L31-L45`, `:L80-L83`):**
  - lint job — `ruff check .`, `shellcheck scripts/*.sh`, a CRLF check, **`djlint templates/ --lint`**.
  - test job — `pytest` against a Postgres-16 `jobmatcher_test` service DB (`DATABASE_URL` set,
    `ci.yml:L82`). `conftest.py` refuses non-`test` DBs (CLAUDE.md § Commands).
  - **Note:** the brief mentioned `black`/`mypy`; the live `ci.yml` runs **neither**. Per-slice exit
    criteria below name the *actual* gates (`ruff` + `djlint` + `pytest`), not assumed ones.

> `unverified:` Issue #749's body text and the live open/closed state of #580/#581/#582 were **not
> directly fetched** — the planning sub-agent had no GitHub MCP read tool or Bash this session. The
> #580/#581/#582 *closure contract* below rests on ADR-009 `:L189-L191`, which I read directly. The
> router should confirm the three issues are still open before filing sub-issues.

---

## 3. Drift controls (made explicit)

Four mechanisms keep Cycle 2 from re-introducing the rendering/coupling debt that motivated the ADRs:

1. **ADR-008 service seam = the shock absorber.** Every screen reads/writes through a JSON-capable
   resource/service layer (`services/api/*` over the `db/` package), with HTMX as a *thin* server-side
   renderer over the **same** layer (ADR-008 `:L150-L164`). A future JS-framework pivot then discards
   only the Jinja layer — bounded blast radius. **Rule:** no template calls `db.*` directly; all data
   flows through a service function that also has a JSON entry point.

2. **ADR-009 render chokepoint + 3 CI contract tests = structural enforcement** (ADR-009 `:L166-L194`).
   Slice 0 builds the chokepoint; the tests then fail CI on any regression, converting "discipline"
   from human memory to mechanical gate.

3. **Sequencing UI after Cycles 0–1 land** (§0). The service layer reads real tables; no speculative
   schema.

4. **The #580/#581/#582 closure rule (HARD).** Per ADR-009 `:L189-L191`: **close #580/#581/#582 ONLY
   when the chokepoint + the 3 named tests exist in code AND `test_feed_card_markup_single_source`
   asserts against the REAL include-site set** (Slice 0 deliverable 4). They must **not** be closed as
   "superseded" on the strength of this plan or the ADR — the `inquisitor` flagged that as laundering
   unsolved debt, and specifically warned that a loosely-written `single_source` test (matching a macro
   name instead of include sites) would launder the violation while `/snippets`/`/bookmarks`/`/applied`
   still render cards outside the chokepoint. The closure is honest only if Slice 0 first **classifies
   all five card-render paths** (deliverable 3 matrix) and the test enforces that classification. They
   close in Slice 0's PR, via `Closes #580` / `Closes #581` / `Closes #582` in the PR body (per
   CLAUDE.md § Pull Requests — one keyword per issue), only after the tests are green, **and only after
   the router confirms all three are still OPEN** (§2 caveat — issue states were not fetched).

---

## 4. Slice decomposition

A **foundation slice (Slice 0)** lands first; then **vertical per-surface slices** each deliver
service endpoint(s) + HTMX template + tests + a fidelity check against `docs/design/ui-layout.md`.

### Slice 0 — Foundation: reconciliation doc + service seam + render chokepoint  *(BLOCKING — no UI slice starts before this lands)*

**Deliverables**
1. **Reconciliation delta doc** — commit `docs/design/cycle2-reconciliation.md` recording R1–R5 (§1)
   and the resolved §8 open API decisions, each with a one-line "locked model wins because …" +
   citation. This is the design↔model anchor every later slice checks fidelity against, alongside
   `ui-layout.md`.
2. **ADR-008 service-layer skeleton** — a `services/api/` package (Flask-free) exposing resource
   functions over the `db/` package for the resources in `api-surface.md §2`
   (`candidate`, `candidate/skills`, `roles`, `preferences`, `jobs`, `ingest`, `sources`, `models`,
   `stats`, `system`). Each function is JSON-serializable and is the *only* path templates use to read
   data. **PATCH merge policy (ADR-010 `:L196-L210`) is defined once per resource here** (absent=no
   change / null=clear / value=set), with **pydantic models (ADR-013 `:L233-L236`)** as the typed
   payload + validation layer. Secrets never echoed — presence indicator only.
3. **ADR-009 render chokepoint — ALL card-render paths enumerated and decided** (inquisitor BLOCKING).
   `render_feed(query: FeedQuery, *, fragment: bool) -> str` (indicative signature per ADR-009
   `:L177-L179`); one shared `_feed_cards.html` partial `{% include %}`-ed by every in-scope page (extract
   the duplicated `#feed-content` wrapper body found at `index.html:L96-L130` /
   `_feed_fragment.html:L7-L41` — **not** the already-shared `_card.html`); one shared
   `parse_feed_query(request) -> FeedQuery` replacing the duplicated parse blocks (`web/feed.py:L77-L94`
   / `:L136-L153`) and covering the new `role` / `combined` / `lifecycle` dims. **#581 is fixed here**
   by having the `ingestComplete` `htmx.ajax` call (`index.html:L13-L14`) forward the current query
   string to `/feed/fragment`.
   **Mandatory all-paths decision matrix** — Slice 0 must classify EACH of the five verified card-render
   routes (§2 table) as either *in-scope-for-chokepoint* or *documented-exception-with-justification*:
   - `/` and `/feed/fragment` → **in scope** (route through `render_feed()`/`_feed_cards.html`).
   - `/bookmarks` and `/applied` (the `index.html:L134-L139` `{% else %}` branch) → **default in scope**;
     their `card-list` loop should consume the same `_feed_cards.html`. If excluded (e.g. these are not
     score-feeds and want different empty-states), say so explicitly in the reconciliation doc.
   - `/snippets` (`snippets.html` — a SEPARATE full page, `:L66-L74`) → **decide explicitly.** It renders
     `lifecycle='scored' AND description_source='snippet'` (NOT the new `lifecycle='discovered'` snippet
     UI Slice 5 adds — those are orthogonal axes, spec `:L185-L201`). Either fold its card-list into
     `_feed_cards.html`, or document it as an intentional exception with its own page chrome. **Do not
     leave it silently outside the chokepoint while closing #580.**
4. **The 3 literal CI contract tests** (ADR-009 `:L180-L188`) — **`single_source` re-specified to assert
   against the REAL include graph** (inquisitor BLOCKING; today `_card.html` is included by THREE files):
   - `test_feed_fullpage_and_fragment_card_markup_identical` — `#feed-content` subtree of `GET /`
     equals the entire body of `GET /feed/fragment` for a fixed `FeedQuery` fixture (byte-for-byte
     after whitespace normalization).
   - `test_feed_card_markup_single_source` — **asserts the `_feed_cards.html` wrapper-body partial
     appears as an `{% include %}` site in exactly the set of templates Slice 0 declared in-scope above,
     and in NO others** (an include-site grep against the real template tree — NOT a loose macro-name
     match). If `/snippets`/`/bookmarks`/`/applied` are declared exceptions, the test asserts they do
     NOT include `_feed_cards.html`; if declared in-scope, it asserts they DO. The test must fail if any
     template renders a card-list outside the declared set.
   - `test_fragment_refresh_preserves_query` — a fragment fetch with filter/role/view params returns
     the same filtered set as the full page with those params (this is the #581 regression guard).
5. **Executable schema-conformance gate** (inquisitor BLOCKING — no UI slice's fidelity gate opens until
   this is green). A `test_cycle01_schema_conformance` test that introspects the LIVE test DB and asserts:
   - the Cycle-0 tables exist (`skills`, `roles`, `job_preferences`, `matches`, profile additions) with
     the **exact column types** the Cycle-2 service layer codes against — including `applicable_skills`
     as **JSONB** (spec `:L253`/§4.5 `:L425-L428` — flag loudly if Cycle 0 shipped `int[]` instead),
     `matches` JSONB columns (ADR-005), and `lifecycle TEXT` (added nullable then `SET NOT NULL`,
     migration §3.3 `:L283`/`:L298`);
   - the `matches` PK is `(listing_id, role_id)` (spec `:L181`) and FKs target `roles`/`listings`;
   - the **Cycle-1 D19 best-fit query** runs and returns the expected column set
     (`l.*, m.role_id, m.score, m.matched_skills, m.missing_skills, m.concerns, m.verdict, m.model_used`,
     spec `:L440-L441`). This is the gate that makes "Slice 0 verifies live schema" executable instead
     of prose. It fails the Slice-0 PR if Cycle 0/1 shipped any divergence.
6. **Single shared effective-value resolver** (inquisitor MAJOR — the most coherence-critical compute).
   `services/api/effective.py::resolve_role(role, candidate) -> EffectiveRole` is the ONE function that
   computes the §4.5 resolution table (`roles-foundation-design.md:L411-L420`): sparse-override merge
   (`role.overrides.X ?? candidate.defaults.X`), baseline-plus-role concatenation for
   `anti_preferences`/`scoring_notes`, and id-membership skill filtering. **Cycle 1's `ingest.py` scoring
   path must import and call this exact function — not a parallel copy** (the resolver is a Cycle-2
   deliverable that Cycle 1 retroactively adopts; if Cycle 1 already inlined it, Slice 0 extracts it and
   reroutes the scorer). A **cross-consumer contract test** (`test_effective_values_agree_across_consumers`)
   feeds one fixture role+candidate through (a) the scoring path, (b) the Slice-5 feed render path, and
   (c) the Slice-3 editor "effective values" display, and asserts all three produce byte-identical
   effective values. This welds the seam ADR-008 `:L150-L164` is supposed to close.
7. **Service-layer error contract** (inquisitor MAJOR — ADR-008's reversibility is void without it).
   Slice 0 defines how `services/api/*` functions signal failure (typed exceptions or result objects,
   chosen here once), how the HTMX layer maps each to an HTTP response, and what the (claimed-reversible)
   JSON entry point returns for the same failure. Must cover at minimum: DB/constraint errors, pydantic
   validation failures, and the **delete-skill-with-active-role-references** case (api-surface `:L67-L69`
   — a skill three roles reference). A test asserts the same failure produces a coherent signal on BOTH
   the template and JSON paths.

**Exit criteria**
- [ ] `docs/design/cycle2-reconciliation.md` committed; **R1–R6** + the **five** §8 API decisions each
      recorded with citation; the §6.6 salary-normalization-home decision (new §8) recorded; the
      D14/D19 `MAX(score)` vs `DISTINCT ON` upstream doc-trap (§8 note) flagged for upstream fix.
- [ ] `services/api/` resource functions exist, JSON-serializable, Flask-free; PATCH merge + pydantic
      validation centralized; no template reads `db.*` directly; **error contract (deliverable 7) defined
      and tested on both HTMX and JSON paths**.
- [ ] **All five card-render routes classified** (deliverable 3 matrix), each in-scope-or-exception with
      justification in the reconciliation doc.
- [ ] `render_feed()` + `parse_feed_query()` + shared `_feed_cards.html` exist; every declared in-scope
      route renders through them.
- [ ] All 3 ADR-009 contract tests present and green — **`test_feed_card_markup_single_source` asserts
      against the declared include-site set, not a macro name**.
- [ ] **`test_cycle01_schema_conformance` present and green** (deliverable 5) — schema/types/D19 query
      match the spec; no Cycle-0/1 divergence.
- [ ] **`effective.py::resolve_role` exists; `ingest.py` calls it (not a copy); the cross-consumer
      contract test is green** (deliverable 6).
- [ ] **#580/#581/#582 closed** via PR-body keywords — and only because the chokepoint + the honest
      `single_source` test + the all-paths classification now exist (drift control #4). **Router must
      confirm all three issues are still OPEN before filing** (§2 caveat — issue states were not fetched).
- [ ] **CI gate green:** `ruff check .`, `djlint templates/ --lint`, `pytest` (Postgres test DB).
- [ ] **Fidelity gate:** N/A (no new screen) — but the reconciliation doc is reviewed and confirmed by
      the user before vertical slices begin.

---

### Slice P — Static Shell-B UI prototype (backend-less, fixtures only)  *(parallel — NOT blocked by Slice 0, Cycle 0, or Cycle 1)*

**Tracked as #776. Gated only on vendor PR #765** (`docs/design/*` must be on `main`). All other
vertical slices are blocked by Cycles 0/1 + Slice 0; Slice P is the single exception because it
touches no live schema and calls no service layer.

**Why it exists.** The plan as written gates the first clickable UI behind two full cycles of
database and service-layer work. Slice P delivers a fully interactive Shell-B prototype immediately,
in parallel, so design feedback and layout iteration can happen on the critical-path timeline rather
than two cycles after it.

**Built as real templates, not throwaway.** Slice P produces the actual Jinja templates that Slices
1–8 later populate with live data. The fixture context objects are shaped per `docs/design/data-model.md`
so they act as a field contract — when a later slice wires a service-layer call, it replaces a fixture
dict with a function return that already matches the same shape. Accepted caveat: possible drift from
final data-wired screens if `data-model.md` changes after Slice P lands; mitigated by building
strictly to `data-model.md` shapes and flagging any mid-flight spec changes as a Slice P re-touch.

**Scope (mirrors #776):**
- Three-region grid (`ui-layout.md §2`).
- Left rail: role quick-switcher (fixture roles) + three config destinations + Admin group + `.me`
  footer; `--target` recolor on role switch; `jm_target` localStorage persistence.
- View-aware context bar + feed-only subbar (`ui-layout.md §3–§4`).
- Static layouts of every screen rendered against fixtures:
  - Feed cards — per-role pills, salary-delta/no-salary badge, snippet visuals.
  - Candidate Profile screen.
  - Roles editor (master list + detail bands).
  - Job Preferences screen.
  - Inspector panel.
  - Admin views.
- Runnable via the existing Flask app: a `/prototype` route tree (or a `PROTOTYPE=1` feature flag)
  so the prototype is clickable and screenshottable without any database present.
- Fidelity against `ui-layout.md`, `design-principles.md`, and `docs/STYLE_GUIDE.md`.
- CI green: `ruff check .`, `djlint templates/ --lint`, `pytest` (a lightweight route-smoke test
  suite — no Postgres required since the prototype routes use fixture context only).

**Depends on:** vendor PR #765 only (needs `docs/design/*` on `main`). Does NOT depend on Slice 0,
Cycle 0, or Cycle 1.

**Templates feed Slices 1–8.** Each later slice that wires a screen replaces the fixture context
import with the appropriate `services/api/*` call and removes the `/prototype` route stub for that
screen. No Jinja is discarded; the work is additive.

---

### Vertical slices (each: service endpoint(s) + HTMX template + tests + fidelity check)

Every vertical slice's **fidelity gate** = visual/interaction parity against `docs/design/ui-layout.md`
(the named section) **and** the Slice-0 reconciliation doc, following `docs/design/design-principles.md`
(alignment-by-width, `:L11-L48`) and `docs/STYLE_GUIDE.md` (no hard-coded hex; semantic tier colors —
CLAUDE.md § UI Development). Every slice's **CI gate** = `ruff check .` + `djlint templates/ --lint` +
`pytest` (Postgres test DB), plus the Slice-0 contract tests staying green.

#### Slice 1 — App shell + left rail + view-aware context bar/subbar
The three-region CSS grid (rail 236px · fluid main · inspector 0→360px), the rail's runtime
role quick-switcher + three config destinations + Admin group + `.me` footer, the **view-aware
context bar** (feed mode vs management mode — no job-filter chrome off-feed) and the **feed-only
subbar** (completeness segment All·Full·Snippets + search). `data-od-id` on every region; `--target`
recolor on role switch; `jm_target` localStorage persistence. **Depends on:** Slice 0.
**Fidelity:** `ui-layout.md §2`, `§3`, `§4`.

**Combined-view rail entry — partial-state resolution (project-reviewer BLOCKING).** The rail includes a
**Combined** quick-switch entry, but its backend (the `combined` `jobs` query mode + de-duped union +
per-target pills) lands in **Slice 5**. To avoid a rail entry that links to a non-existent backend
during the Slice-1→Slice-5 window, Slice 1 renders the Combined entry **disabled/stub** with a named
enable signal — gate it on a `combined_enabled` flag (or feature-detect the Slice-5 `jobs?scope=combined`
endpoint) that flips on only when Slice 5 ships. The dependency graph below shows this partial-state
window explicitly. (Alternative if cleaner at build time: defer the Combined rail wiring entirely to
Slice 5 and ship Slice 1's rail without the entry. Decide in Slice 1; do not ship a live-but-dead link.)

#### Slice 2 — Candidate Profile + Skills shared-bucket surface
The `candidate` singleton screen (identity incl. current_location/current_role, education,
base_salary) + the **Skills** shared-bucket manager (`candidate/skills` sub-collection — global
`{id, name, years}`; deletion must reckon with role references, api-surface `:L67-L69`). Carry forward
the PDF-import action (`services/pdf_import.py`). **Depends on:** Slice 0, Slice 1 (rail destination).
**Fidelity:** `ui-layout.md §5.2`; reconciliation R1 (baseline scoring_notes/anti_preferences live here).

**Skill-deletion cross-role ref — AC split (project-reviewer CONCERN).** The full integration test
(delete a skill referenced by a real role and assert the configured behavior — block, or scrub the
`applicable_skills` arrays per spec §4.5 `:L428`) can't run until Slice 3's role rows exist. So split
the acceptance criterion: **Slice 2 owns the deletion *service logic* + a unit test with a fixture role
row** (insert a synthetic role referencing the skill, assert the service's error/scrub behavior via the
Slice-0 error contract); **the real cross-role integration test is a Slice-3 sub-criterion** (listed in
S3's AC). This keeps Slice 2 shippable without a forward dependency on the Roles editor.

#### Slice 3 — Roles master–detail editor
The headline new build. Left role list (dot · name · skill count · match count · paused flag ·
+New) → right editor in **three labeled tier bands**: Target-defined (Tier 1) · Shared-overridable
(Tier 2, inline override toggle + revert) · Skills-applicable (shared bucket as binary on/off chips)
+ target salary (seeded from base) + linked default resume. Sparse-`overrides` PATCH semantics
(ADR-010). **Depends on:** Slice 0, Slice 1, Slice 2 (reads `candidate/skills`).
**Fidelity:** `ui-layout.md §5.3` + `roles-editor-rebuild.md §3`, `§4`, `§6`; reconciliation R2.

**Optimistic-locking on save (inquisitor MAJOR).** The spec already builds `roles.updated_at` and the
ingest run-start snapshot + staleness mechanism (§2.7 `:L226-L228`), and Slice 3 is the surface that
*causes* mid-run edits. The sparse-PATCH model makes lost updates especially nasty: a PATCH that omits a
key means "no change," so a stale-read-then-save in a second tab silently reverts the first tab's
override-add with **no field-level conflict visible**. **Slice 3's PATCH contract must carry `updated_at`
as an optimistic-lock token** — an `If-Unmodified-Since`-style precondition (or an ETag derived from
`updated_at`): the save includes the `updated_at` it read, and the service rejects the write (409/
conflict via the Slice-0 error contract) if the row's current `updated_at` is newer. Single-user
(ADR-007) reduces but does not eliminate this — two tabs, or a save during a cron `python ingest.py`
run, are real paths the spec anticipated. Last-write-wins is acceptable ONLY if the reconciliation doc
explicitly justifies it against the sparse-override revert hazard; the default here is the precondition.

**Planned three-way sub-cut — committed up front, not conditional (inquisitor MINOR).** Slice 3 is the
largest build; rather than deferring the split to a runtime "if it grows" call, it ships as a primary
`feature-roles-editor` branch with **three sub-issues decided before code** (CLAUDE.md § Git Commits
primary+sub-branch pattern): **S3a** data-wiring (role list + read/effective-values endpoint, reads
`candidate/skills`) → **S3b** the three tier bands + sparse-`overrides` PATCH + `updated_at`
optimistic-lock + revert mechanics → **S3c** skills binary-chip control + target-salary seeding + linked
default resume. Sub-PRs merge into `feature-roles-editor`; the integration PR merges to `main` (repeat
`Closes` keywords there — sub-PR closes against a feature branch don't fire, CLAUDE.md § Pull Requests).

**Ultra-wide cap watch (moved here from Slice 1, NIT).** The editor's detail pane is the surface most at
risk of unbounded growth on ultra-wide viewports — honor any `design-principles.md` max-width cap here,
not in the shell slice.

**Skill-deletion integration sub-criterion (from Slice 2 split).** The real cross-role skill-deletion
integration test (delete a skill a live role references; assert block-or-scrub per spec §4.5 `:L428`)
runs HERE, since this is the first slice with real role rows. Listed in S3's AC.

#### Slice 4 — Job Preferences (global) surface
New top-level destination: Locations (multi, single global radius) · Work Models (multi-select) ·
Job Types (multi-select) · **Salary mode** (`floor` vs `display`) + `floor_amount`. These are **hard
pull filters** (data-model A.5) — surface that semantic in copy. **Owns `salary_mode`/`floor_amount`
(reconciliation R6, spec §2.4 `:L144-L154`):** `salary_mode=='floor'` is a **hard ingest drop** below
`floor_amount` (spec `:L151`) — Slice 4 owns the preference surface + the copy that makes the drop
semantic explicit; the drop itself happens at ingestion, not the Cycle-2 read path. `floor_amount` is
required when mode is `floor`; validate it in the PATCH payload (Slice-0 pydantic/error contract).
**Depends on:** Slice 0, Slice 1. **Fidelity:** `ui-layout.md §5.4`.

#### Slice 5 — Feed surface (per-role + Combined) with salary delta + snippet state
The dense feed reading the Cycle-1 best-fit `DISTINCT ON` Match row, rendered through the Slice-0
`render_feed()` chokepoint. Adds: per-role vs **Combined** query mode (reconciliation R3 — query
param on `jobs`, per-target color pills, de-duped union; **enables the Slice-1 Combined rail stub**);
**salary delta vs base** ("+20% vs base", server-side per api-surface §6 item 1 `:L163-L165`) and the
**no-salary red-flag badge** (reconciliation R5, never an auto-drop); the
**snippet/`lifecycle='discovered'`** pre-scrape render (muted dashed flag, `—` score, "awaiting scrape"
badge, ⟳ Scrape action — distinct from the existing `/snippets` page which is `lifecycle='scored' AND
description_source='snippet'`, spec `:L185-L201`). **Depends on:** Slice 0, Slice 1.
**Fidelity:** `ui-layout.md §4.2`, `§5.1`; reconciliation R3/R4/R5/R6.

**`lifecycle IS NULL` defense (inquisitor MAJOR — silent data loss).** The D19 feed query filters
`WHERE l.lifecycle = 'scored'` (spec `:L445`); any row with `lifecycle IS NULL` is **silently dropped**
with no error and no log — and the user can't distinguish "no matching jobs" from "jobs dropped by a
NULL predicate." Cycle 0's migration adds `lifecycle` nullable then `SET NOT NULL` inside one txn (§3.3
`:L298`), so a NULL should never persist — but a post-migration insert that omits `lifecycle`, or an
interrupted migration the assertion misses, reintroduces it. **Slice 5's feed service must treat
`lifecycle IS NULL` as an explicit, logged/counted anomaly** (surface a count, don't silently filter) —
**and a test asserts a seeded `lifecycle=NULL` row is reported as an anomaly, not silently excluded.**
(Belt-and-suspenders alternative the plan also accepts: Slice 0 asserts
`COUNT(*) WHERE lifecycle IS NULL = 0` as a startup invariant — but the downstream-defense version is
required regardless, because depending on upstream correctness for a silent-data-loss path is not
acceptable.)

**Mixed-type join mapping carried into the service contract (inquisitor BLOCKING #2 tail).** The D19
query joins the **JSONB `matches`** table against the **TEXT-JSON `listings`** table (existing `listings`
columns stay REAL/TEXT-JSON per ADR-005 scope note `:L105-L122`; the spec flags this at `:L266-L267` as
needing per-column-aware mapping — psycopg2 returns JSONB as Python objects already but TEXT-JSON needs
explicit `json.loads`). **Slice 5's service function must use the per-column-aware row mapper** (not the
legacy `_deserialise_row` on JSONB columns, and not raw psycopg2 dicts on TEXT-JSON columns); a unit
test asserts a joined row's `matched_skills` (JSONB, from `matches`) and any legacy `listings` JSON
column both deserialize to Python lists/dicts correctly.

**`salary_mode` branch (reconciliation R6).** Render the salary **delta-vs-base ONLY when the global
`salary_mode=='display'`** (spec §2.4 `:L152-L153` — neutral below base, green above). When
`salary_mode=='floor'`, no delta render; surface a copy/badge cue that a floor filter is active (the
drop happened at ingestion, Slice 4). The no-salary red-flag badge (R5) renders in BOTH modes.

#### Slice 6 — Right inspector
Slides in (grid col 0→360px) on job-row click: score breakdown, matched/gap skills, verdict, the
resume tie-in (pick per-application resume → Attach & apply — link-only, `applied_resume_id` per spec
D10), Combined-view override detail ("matched via SWE · salary floor overridden", deferred from the
feed micro-marker per `roles-editor-rebuild.md §6`). `Esc`/✕ closes. **Depends on:** Slice 5.
**Fidelity:** `ui-layout.md §6.1`.

#### Slice 7 — Ingest: re-surface existing SSE as bottom stream bar + shared event vocab + history endpoint
**RE-SCOPED (inquisitor MAJOR): SSE is already built and tested — this slice does NOT stand up SSE.** The
live stream (`GET /ingest/stream`, `web/ingest.py:L241-L295`), the `MAX_SSE_CONNECTIONS=2` cap
(`services/ingest_control.py:L108`), Last-Event-ID replay, the `EventSource` client
(`static/ingest-drawer.js`), and the SSE test suite (`tests/test_ingest_stream.py`,
`tests/test_ingest_integration.py`) all exist. The NEW work is:
1. **Re-surface the existing `/ingest/stream` consumer as the Shell-B bottom stream bar** — Ingest FAB →
   bottom bar (LIVE indicator, current source, running count, left-scrolling target-colored event
   chips). This is a UI reskin of the existing drawer's client, **reusing** `services/ingest_control.py`
   SSE state — not a new SSE endpoint. Re-use the existing SSE test suite; add UI/render tests only.
2. **Shared event vocabulary** — the canonical event-type set both the bottom bar and the admin log
   (Slice 8) consume.
3. **History data/query endpoint** — the backing query for the admin activity log (time·source·target·
   event·detail, searchable/filterable). **Slice 7 owns the endpoint; Slice 8 owns the admin-surface log
   *template*** (ui-layout §6.2 `:L218` hosts the table under Admin → Job Sources — project-reviewer
   CONCERN). The ADR-015 `proxy_buffering off` doc note (`:L245-L250`) stays here.

**Subscriber-cap hazard — must be resolved here (inquisitor MAJOR).** The Shell-B design wants a persistent
bottom bar on feed/role views, openable from a top-bar indicator, plus a potential admin live-log view —
that is **≥3 concurrent `EventSource` subscribers against a hard cap of 2** (`web/ingest.py:L253-L254`
returns 429 on the third). A duplicate browser tab pushes it further. **Slice 7 must state the
resolution**, and the default is: **a single shared `EventSource` multiplexed to all widgets** (one
connection per tab, fanned out to bottom bar + top indicator + any in-page log via a client-side
event bus) rather than one connection per widget. If multiplexing is impractical, the fallback is to
**raise `MAX_SSE_CONNECTIONS`** with a stated rationale + worker-cost note (per-connection holds a
waitress thread). Do not ship a multi-widget design that silently 429s the third surface.
**Depends on:** Slice 0, Slice 1. **Fidelity:** `ui-layout.md §6.2`.

#### Slice 8 — Admin surfaces
Stats (pipeline KPIs + per-target matches table), Job Sources (provider list, drag-priority,
enable toggle — **hosts the Ingest activity-log *template*** that renders the Slice-7 history endpoint +
shared event vocab, ui-layout §6.2 `:L218`), LLM & Models (per-stage routing + provider keys
[presence-only per ADR-010/011] + token budget), System (schedule/storage, maintenance, danger zone).
**Depends on:** Slice 0, Slice 1, Slice 7 (log endpoint + event vocab). **Fidelity:** `ui-layout.md §5.5`.

**Scope guard (NIT).** The **resume-tailoring model-routing row** is a **Cycle 3** concern (Resumes,
#750) — Slice 8's LLM & Models surface covers only the Cycle-0..2 pipeline stages (ingest scoring +
any existing routing). Do NOT add a resume-tailoring routing row here; it lands with Cycle 3.

### Dependency graph / parallelization

```
PR #765  (vendor-docs — docs/design/* lands on main)
   │
   ├──────────────────────────────────────────────────────────────────────────────┐
   │                                                                              │
   ▼                                                                              ▼
Slice 0  (foundation — BLOCKING for S1–S8:                             Slice P  (backend-less prototype —
          chokepoint+all-paths · schema-conformance ·                            PARALLEL, not blocked by S0/C0/C1)
          effective-resolver · error-contract)                                   [fixture templates → reused by S1–S8]
   │
   ▼
Slice 1  (shell + rail — Combined rail entry ships DISABLED/STUB)
   ├──────────────┬──────────────┬───────────────┐
   ▼              ▼              ▼               ▼
Slice 2        Slice 4        Slice 5 ···········> (enables Slice-1 Combined stub)
(Profile)      (Job Prefs +   (Feed +              │
   │            salary_mode)   salary delta/        │
   ▼                           NULL-defense/        ▼
Slice 3                        mixed-join)        Slice 6
(Roles ed.                       │                (Inspector)
 S3a→S3b→S3c)                     ▼
                               Slice 7  (re-surface existing SSE + vocab + history endpoint)
                                  │
                                  ▼
                               Slice 8  (Admin — hosts log TEMPLATE over Slice-7 endpoint)
```

- **Slice P is parallel and independent:** gated only on vendor PR #765; runs concurrently with
  Cycles 0/1 and Slice 0. Its real Jinja templates are consumed by Slices 1–8 (fixtures swapped for
  live service output). It does not block and is not blocked by the S0→S8 critical path.
- **Strictly serial:** Slice 0 → Slice 1 (everything hangs off the shell). No vertical slice's fidelity
  gate opens until Slice 0's **schema-conformance test** (deliverable 5) is green.
- **Parallelizable after Slice 1:** Slices 2, 4, 5, 7 are independent surfaces against distinct
  service resources — safe to run concurrently (different `services/api/*` modules, different
  templates, no shared write state). Use `superpowers:dispatching-parallel-agents` posture.
- **Serial tails:** Slice 3 after Slice 2 (reads skills; itself S3a→S3b→S3c sub-PRs under
  `feature-roles-editor`); Slice 6 after Slice 5 (inspector opens from feed rows); Slice 8 after Slice 7
  (renders the log template over Slice 7's history endpoint + shared event vocab).
- **Partial-state window (project-reviewer BLOCKING):** the **Combined rail entry** ships in Slice 1 as
  a disabled/stub and is **enabled by Slice 5**. During the Slice-1→Slice-5 window the entry must not be
  a live link to a non-existent backend (Slice 1 gates it on a `combined_enabled` signal).

---

## 5. Per-slice exit-criteria template (applies to every vertical slice)

- [ ] Service endpoint(s) exist in `services/api/*`, JSON-serializable, Flask-free; writes use the
      centralized PATCH merge + pydantic validation (ADR-010/013); failures use the Slice-0 **error
      contract** (typed signal mapped consistently on HTMX + JSON paths); secrets presence-only.
- [ ] HTMX template(s) render **only** through service-layer data (no direct `db.*` in templates).
- [ ] Any slice consuming effective role values (3, 5, 6) calls the shared
      `services/api/effective.py::resolve_role` — **no parallel resolution logic**.
- [ ] Tests: service-layer unit tests + a route/template test; for any write, a PATCH
      absent/null/value test; regression test for any bug fixed.
- [ ] **Fidelity gate:** visual + interaction parity vs the named `ui-layout.md` section and the
      Slice-0 reconciliation doc; `design-principles.md` alignment rule honored; `STYLE_GUIDE.md`
      respected (no hard-coded hex; semantic tier colors) and updated in-PR if a new token/component
      is introduced.
- [ ] **CI gate:** `ruff check .` + `djlint templates/ --lint` + `pytest` (Postgres test DB) all
      green; the 3 Slice-0 contract tests + `test_cycle01_schema_conformance` +
      `test_effective_values_agree_across_consumers` still green.
- [ ] README onboarding updated if the slice changes run/build/env (CLAUDE.md § README Maintenance);
      ADR-015 proxy note added for Slice 7.

---

## 6. Proposed GitHub sub-issues (for the router to file — DO NOT create here)

All under **milestone #12**, epic #751, labeled `cycle-2`. Each is one slice.

| # | Proposed title | Acceptance-criteria sketch |
|---|---|---|
| SP | `Cycle 2 · Slice P — Static Shell-B UI prototype (backend-less, fixtures only)` | **Already filed as #776 — do not refile.** Dependency: vendor PR #765 only (needs `docs/design/*` on `main`). Three-region grid + left rail (fixture roles, quick-switcher, `--target` recolor, `jm_target` localStorage) + view-aware context bar + feed-only subbar; static layouts of all screens (Feed cards incl. per-role pills/salary-delta/snippet visuals, Candidate Profile, Roles editor, Job Preferences, Inspector, Admin) rendered against `data-model.md`-shaped fixture context; runnable via a `/prototype` route tree or `PROTOTYPE=1` feature flag (clickable/screenshottable, no Postgres required); fidelity vs `ui-layout.md` + `design-principles.md` + `STYLE_GUIDE.md`; CI green (`ruff`, `djlint`, `pytest` route-smoke). Real Jinja templates — not throwaway; Slices 1–8 swap fixtures for live service output. |
| S0 | `Cycle 2 · Slice 0 — Foundation: reconciliation doc + service seam + chokepoint + schema/effective/error gates` | Reconciliation delta doc (**R1–R6** + **five** §8 API decisions incl. salary-normalization + D14/D19 doc-trap flag) committed to `docs/design/`; `services/api/` skeleton over `db/` with centralized PATCH/pydantic + **error contract** (HTMX+JSON); `render_feed()`/`parse_feed_query()`/shared `_feed_cards.html`; **all 5 card-render paths classified**; 3 ADR-009 contract tests green (**`single_source` asserts the real include-site set**); **`test_cycle01_schema_conformance` green** (tables/types/D19 query match spec); **`effective.py::resolve_role` + cross-consumer contract test green; `ingest.py` calls it**; **#580/#581/#582 closed because the chokepoint+honest tests now exist** (router confirms still-open first); CI green. |
| S1 | `Cycle 2 · Slice 1 — App shell + left rail + view-aware context bar/subbar` | Three-region grid; rail (role switcher + 3 config dests + Admin + `.me`); **Combined rail entry ships DISABLED/STUB gated on a `combined_enabled` signal** (enabled by S5); view-aware context bar (mgmt mode hides job chrome); feed-only subbar; `--target` recolor; `jm_target` persistence; `data-od-id` on regions; fidelity vs `ui-layout.md §2–§4`; CI green. |
| S2 | `Cycle 2 · Slice 2 — Candidate Profile + Skills shared-bucket surface` | `candidate` singleton screen + `candidate/skills` bucket CRUD ({id,name,years}); **skill-delete service logic + unit test with a fixture role row** (real cross-role integration test deferred to S3); PDF-import carried forward; baseline scoring_notes/anti_preferences live here (R1); fidelity vs `§5.2`; CI green. |
| S3 | `Cycle 2 · Slice 3 — Roles master–detail editor` | Role list + 3-band detail editor (Tier1 / Tier2 inline override+revert / binary skills chips) + target salary seeded from base + linked resume; sparse-overrides PATCH (R2) **with `updated_at` optimistic-lock precondition** (rejects stale writes, spec §2.7); **real cross-role skill-deletion integration test** (from S2 split); calls shared `effective.resolve_role`; fidelity vs `§5.3`+`roles-editor-rebuild.md`; CI green. **Ships as planned sub-PRs S3a (data-wiring) → S3b (bands+PATCH+lock+revert) → S3c (skills chips+salary seed+resume)** under primary `feature-roles-editor`. |
| S4 | `Cycle 2 · Slice 4 — Job Preferences (global) surface` | Locations (single global radius) + Work Models + Job Types **+ `salary_mode`(`floor`/`display`)+`floor_amount`** as hard-pull-filter surface (R6; `floor_amount` required-when-floor validated in PATCH); fidelity vs `§5.4`; CI green. |
| S5 | `Cycle 2 · Slice 5 — Feed surface (per-role + Combined) + salary delta + snippet state` | Feed via `render_feed()` reading Cycle-1 best-fit Match (calls `effective.resolve_role`); Combined query mode + per-target pills (R3) **enabling the S1 Combined stub**; **salary delta vs base ONLY when `salary_mode=='display'`** + no-salary red flag (R5/R6); `lifecycle='discovered'` snippet render + Scrape action (R4); **`lifecycle IS NULL` logged/counted as anomaly (not silently dropped) + test**; **mixed JSONB-`matches`↔TEXT-JSON-`listings` per-column-aware join mapper + test**; fidelity vs `§4.2,§5.1`; CI green. |
| S6 | `Cycle 2 · Slice 6 — Right inspector` | Inspector slide-in (score breakdown via `effective.resolve_role`, gap skills, verdict, resume tie-in/Attach&apply link-only, override detail); `Esc`/✕ close; fidelity vs `§6.1`; CI green. |
| S7 | `Cycle 2 · Slice 7 — Ingest: re-surface existing SSE as bottom bar + event vocab + history endpoint` | **SSE already built — NOT a new SSE stand-up**; re-surface `/ingest/stream` consumer as Shell-B bottom stream bar (reuse existing SSE tests, add UI tests); shared event vocabulary; **history data/query endpoint** for the admin log; **subscriber-cap hazard resolved** (single shared `EventSource` multiplexed, or raise `MAX_SSE_CONNECTIONS` with rationale — no silent third-surface 429); ADR-015 `proxy_buffering off` doc note; fidelity vs `§6.2`; CI green. |
| S8 | `Cycle 2 · Slice 8 — Admin surfaces (Stats · Sources · LLM & Models · System)` | Four admin views; **hosts the Ingest activity-log *template*** over Slice-7's history endpoint + shared vocab (ui-layout §6.2); provider keys presence-only (ADR-010/011); **scope guard: NO Cycle-3 resume-tailoring routing row**; fidelity vs `§5.5`; CI green. |

---

## 7. Quality-check summary

- Requirements testable/unambiguous: yes — each slice has service + template + test + named fidelity
  and CI gates; Slice 0 now adds four executable gates (chokepoint all-paths, schema-conformance,
  shared effective-resolver contract, service error contract).
- Hidden assumptions surfaced: the **five** card-render paths incl. `/snippets` as a separate page (§2);
  **SSE is already built and tested** — Slice 7 re-scoped (§2); the **Cycle-0/1 schema does not exist on
  `main` yet** — schema-conformance gate added (§2); the **OpenDesign docs live only in the
  `vendor-opendesign-docs` worktree, not `main`** (REVISED note + §9); the `black`/`mypy` non-existence
  in CI (§2); the unverified issue-states caveat (§2).
- Technical decisions confirmed (not assumed): all rest on read ADRs / the locked spec, cited inline;
  the live-code findings (chokepoint paths, SSE infra, cap value) re-verified this revision.
- Scope bounded: Slice 0 blocks; vertical slices enumerated; Cycle 3 (Resumes, #750) is explicitly
  out of scope (only `applied_resume_id` link-only tie-in appears, Slice 6; Slice 8 scope-guards out the
  resume-tailoring routing row).
- **Slice P decouples UI feedback from the Cycle 0/1 critical path** (#776): by building real Jinja
  templates against fixture context immediately (gated only on vendor PR #765), design-fidelity review
  and layout iteration happen in parallel with schema and service-layer work rather than two cycles
  after it. Slices 1–8 inherit the templates and replace fixture context with live service output.
- Open questions listed: §8 (now five decisions + the D14/D19 upstream doc-trap).

---

## 8. Open decisions that need the USER (Discovery — answer before Slice 0 closes)

These are the `api-surface.md §6` API-shape decisions — a six-item numbered list at api-surface `:L158-L177`
(the model is locked; these are not dictated by it). Each carries the handoff's lean; **none is decided**
— the user must confirm in Slice 0's reconciliation doc:

1. **Tier/delta resolution — server-side vs client-side?** api-surface §6 item 1 (`:L163-L165`) leans
   **server-side** (endpoints return effective override-resolved values + computed salary deltas inline).
   Confirms how Slices 3 and 5 are built. *Recommend confirming server-side.*
2. **Combined view — jobs query mode vs dedicated resource?** §6 item 2 (`:L166-L168`) leans **query
   mode** (a `combined` scope param on `jobs`). Confirms Slice 5's shape. *Recommend confirming query
   mode.*
3. **Ingest stream contract — SSE/push vs polling?** §6 item 3 (`:L169-L170`) leans **stream**; **ADR-015
   already commits to SSE over waitress** and **the live app already streams** (`/ingest/stream` exists).
   Surfaced for explicit user sign-off since it carries the proxy-config + per-connection-worker cost +
   the `MAX_SSE_CONNECTIONS=2` multi-subscriber hazard (Slice 7). *Recommend confirming SSE per ADR-015.*
4. **Snippet promotion — explicit action vs automatic vs both?** The **API-shape** question is open at
   api-surface §6 item 5 (`:L174-L175` — does `jobs` need a write action or just reflect pipeline state?).
   The **model-level default is already RESOLVED**: spec **O2 (`roles-foundation-design.md:L463`)** sets
   **inline-score as the default** with `discovered` only on deferred/failed scoring, and an explicit
   per-snippet Scrape action for those cases. So Slice 5 DOES need a `jobs` Scrape write action.
   *Recommend confirming inline-default + explicit Scrape action per O2.*
5. **Salary normalization home — ingest-time vs read-time? (project-reviewer CONCERN — was missing.)**
   api-surface §6 item 6 (`:L176-L177`): currency/period normalization for the salary delta — stored
   normalized at ingestion, or computed per request at read? This determines whether Slice 5's service
   layer is **thin** (reads pre-normalized values) or **carries normalization logic** (currency/period
   math + range-midpoint per api-surface `:L132`). Ties to decision #1. *Recommend confirming
   ingest-time normalization* (keeps the read path thin and the delta cheap), *pending user call.*

> `api-surface.md §6 item 4` (single-user vs multi-user, `:L171-L173`) is **already settled** by ADR-007
> (single-user; multi-user deferred to v3, `architecture-decisions.md:L139-L148`) — not re-opened here.

> **Upstream doc-trap to flag, NOT to fix here (project-reviewer CONCERN — D14/D19 inconsistency).** The
> Cycle-0/1 spec is internally inconsistent on the feed read: §4.6/D19 (`:L434-L448`) correctly mandates a
> `DISTINCT ON` **row** select (so the card can render the best-fit role's `matched_skills`/`verdict`/
> `model_used`), but if any other passage describes the feed read as a `MAX(score)` **scalar** it
> contradicts D19 and is not legal SQL beside the non-aggregated columns. **Slice 0's reconciliation doc
> records this as a doc-trap for the Cycle-0/1 spec owners to fix upstream** — the Cycle 2 plan does NOT
> edit the locked spec; it builds against D19 (`DISTINCT ON` row) and flags the inconsistency so the
> upstream is corrected before an implementer follows the wrong passage.

---

## 9. References

- LOCKED roles-foundation spec: `docs/superpowers/specs/2026-05-29-job-matcher-2.0-roles-foundation-design.md`
  (§2 normative model, §4.5/§4.6 scoring/feed, D1/D2/D19, O2).
- 2.0 ADRs: `docs/superpowers/specs/2026-05-29-job-matcher-2.0-architecture-decisions.md`
  (ADR-008/009/010/011/013/015).
- OpenDesign handoff (UI authority + bridging refs): `docs/design/ui-layout.md`, `data-model.md`,
  `api-surface.md`, `design-principles.md`, `roles-editor-rebuild.md` — **currently only in the
  `.worktrees/vendor-opendesign-docs` worktree, NOT on `main`** (verified this session); cited line
  numbers (e.g. api-surface `:L158-L177`, ui-layout `:L218`) are against that worktree copy. The
  vendor-docs PR must merge before these paths resolve on `main`.
- Verified current state (re-verified this revision 2026-06-04): five card-render routes
  `web/feed.py:L61-L287` (`/`, `/feed/fragment`, `/bookmarks`, `/applied`, `/snippets`); `_card.html`
  included by THREE templates `index.html:L114`/`:L137`, `_feed_fragment.html:L25`, `snippets.html:L71`;
  `snippets.html` is a separate full page `:L1-L90`; SSE already built `web/ingest.py:L241-L295` with
  `MAX_SSE_CONNECTIONS=2` `services/ingest_control.py:L108`; `ingestComplete` listener drops query
  `index.html:L13-L14`; duplicated parse blocks `web/feed.py:L77-L94`/`:L136-L153`;
  `.github/workflows/ci.yml:L31-L45`/`:L80-L83`. Spec facts re-verified: salary_mode §2.4 `:L144-L154`;
  effective-value table §4.5 `:L411-L420`; D19 feed query §4.6 `:L439-L448`; mixed-type mapping §3.2
  `:L266-L267`; `updated_at` staleness §2.7 `:L226-L228`; migration `lifecycle` §3.3 `:L283`/`:L298`;
  ADR-005 scope note `:L105-L122`; O2 `:L463`.
- Tracking: epic #751, milestone #12, cycle #749, deps #747/#748.
