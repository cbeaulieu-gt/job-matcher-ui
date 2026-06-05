# job-matcher — UI layout (high-level handoff)

> **Purpose.** A self-contained description of the redesigned job-matcher UI's high-level
> layout — the app shell, navigation, every screen, and the cross-cutting surfaces — written
> so another agent can build or reason about it without re-deriving decisions from the chat
> history. This is the **layout** companion to two other locked docs:
>
> - `docs/data-model.md` — the canonical entity/field model (Candidate · Roles · Job Preferences).
> - `docs/design-principles.md` — the alignment/visual rules every screen follows.
>
> Read those two for *what the data is* and *how things align*. This doc is *where things live
> on screen and how the user moves between them*.
>
> **Status (2026-05-29).** The locked shell is **"Shell B — sidebar rail + main + right inspector,"**
> chosen by the user because the persistent left rail frees horizontal room for a right inspector
> panel (the natural information-density expansion point). The working prototype is
> `job-matcher-shell-b-2.html`. Where the built prototype diverges from the locked target IA, this
> doc describes the **target** and flags the divergence in a callout.

---

## 1. Visual system (carried from the live app — non-negotiable)

The redesign keeps the existing app's **dark "industrial terminal-ledger"** DNA verbatim. Do not
introduce a new palette or type system.

| Token | Value | Role |
|---|---|---|
| `--bg-base` | `#0f1117` | App ground |
| `--bg-surface` | `#171b23` | Cards, rail, context bar |
| `--bg-raised` | `#1e2330` | Inputs, raised controls |
| `--text-primary` | `#eceef5` | Primary text |
| `--text-muted` | `#7a8599` | Metadata, labels |
| `--accent` | `#f5a623` | The one amber accent |

**Semantic score tiers** (load-bearing — drive card flags, scores, skill chips):
high `#4df590` (8+) · mid `#ffd24d` (5–7) · low `#ff6b6b` (<5).

**Per-target identity colors** (new): SWE `#f5a623` · Data `#4dd2f5` · Platform `#b58cf5`.
The active target's color is bound to `--target` and the **whole shell recolors** when the user
switches role.

**Type:** serif body (Georgia), mono for metadata/labels/numerics (Menlo/Consolas), system sans
for titles/buttons. **Density is non-negotiable** — this is a dense operator tool, not editorial.

---

## 2. The app shell — three regions

A single-file SPA. The shell is a CSS grid with three columns; the inspector column animates open
from 0 width.

```
┌───────────┬───────────────────────────────────────────┬──────────────────┐
│           │  CONTEXT BAR  (view-aware header)           │                  │
│           ├───────────────────────────────────────────┤                  │
│   RAIL    │  SUBBAR  (feed-only filters)                │   INSPECTOR      │
│ (sidebar) ├───────────────────────────────────────────┤  (slides in on   │
│           │                                             │   job click;     │
│  nav +    │           MAIN CONTENT                      │   right side)    │
│  role     │   (feed list OR a full-screen view)         │                  │
│  switcher │                                             │                  │
│           │                                             │                  │
│           │                          [ ⟳ Ingest FAB ]   │                  │
└───────────┴───────────────────────────────────────────┴──────────────────┘
   236px              fluid (fills)                            360px (open)
                ┌─────────── INGEST STREAM BAR (slides up from bottom) ──────────┐
                └────────────────────────────────────────────────────────────────┘
```

- **Rail** (`236px`, fixed) — persistent navigation + the role quick-switcher. §3.
- **Main** (fluid, fills) — a stack of: context bar → subbar → the active view. §4–§5.
- **Inspector** (`360px`, toggled) — job detail / drill-down. Closed by default; `Esc` closes. §6.
- **Ingest FAB + stream bar** — live scrape ticker, feed/role views only. §6.

---

## 3. The rail (left) — navigation + role switching

The rail has two distinct jobs that must not be confused: a **runtime role switcher** (which
target's results am I browsing?) and the **config destinations** (where I set things up).

### 3.1 Target / role quick-switcher  *(runtime view control — top of rail)*

A group listing each target role with its identity dot + name + match count, then a **Combined
view** entry, then **Manage targets…**. Clicking a target:

- switches the feed to that role's results,
- rebinds `--target` so the shell recolors,
- persists the choice to `localStorage` (`jm_target`).

**Combined view** merges every active role's results, de-dupes by posting, and tags each row with
a per-target color flag showing which role(s) matched it.

This switcher is **separate** from the config destinations below — it is not "a page," it's the
lens on the feed.

### 3.2 Config & browse destinations

> **⚠ Build-vs-target divergence.** The locked IA (`data-model.md §0`) is **three top-level config
> destinations**. The current prototype rail still shows the older grouping (`Profile › Roles ·
> Resumes` + a separate `Admin` group). **Target structure the receiving agent should build toward:**

| Rail group | Destinations | Maps to |
|---|---|---|
| **Browse** | Feed · Bookmarks · Applied · Dismissed | runtime job lists (all feed-mode) |
| **Candidate Profile** | identity · education · **Skills** (shared bucket) · base salary | `data-model.md` Candidate |
| **Roles** | manage target roles (criteria, selected skills, **linked resume**) · **Resumes** | `data-model.md` Role + Resume |
| **Job Preferences** | Locations · Work Models · Job Types | `data-model.md` JobPreferences (global) |
| **Admin** | Stats · Job Sources · LLM & Models · System | operational surfaces |

Key IA moves baked into the target (per §0 of the data model):
- **Skills** is a destination *inside Candidate Profile* (skills belong to the person, defined once).
- **Resumes** folds *under Roles* (each role links its matching resume).
- **Job Preferences** is a *new* top-level destination for the global locations / work-model /
  job-type settings (these are search-wide, never per-role).

### 3.3 User footer

A `.me` row at the rail bottom — avatar, name, settings cog.

---

## 4. The main region — shared chrome

Two stacked bars sit above the active view:

### 4.1 Context bar (`#ctx`) — **view-aware**

The header changes by view (driven by a `VIEW_HEAD` map). It has two modes:

- **Feed mode** — active target dot + name, its criteria chips, the live match count, and a
  live-ingest indicator.
- **Management mode** — for Profile / Roles / Resumes / Job Preferences / Admin views: a
  view-specific title + icon + one-line descriptor. **No job-filter content** (no criteria chips,
  no match count) — those are meaningless off the feed.

> This was an explicit user requirement: *"when the user is managing Profiles/Resumes the top bar
> will need to change. It should not always show the Job filter information."*

### 4.2 Subbar (`#subbar`) — **feed-only filters**

Visible only on feed views; hidden on all management views. Holds:
- a **completeness filter** segment — **All · Full jobs · Snippets**,
- a search box.

(**Snippets** = postings discovered but not yet LLM-scored. They render in a distinct pre-scrape
state: muted dashed flag, `—` score, "awaiting scrape" badge, a ⟳ Scrape action.)

---

## 5. The screens (views)

Each view is a full panel in the main region. The feed is the default.

### 5.1 Feed (default)
The dense job list. Each row: score (tier-colored) · left tier flag · title (serif) · company /
location / salary metadata (mono) · matched/missing skill chips · badges (new/remote/source) ·
quick actions (View · ★ · ✓ · ×). In Combined view, rows also carry per-target color pills.
**New (per data model A.10):** each row shows a **salary delta vs the candidate's base salary**
("+20% vs base"); a posting with no extracted salary shows a **red "no salary" flag**, not a drop.
Clicking a row opens the inspector (§6).

### 5.2 Candidate Profile  *(target IA)*
The person, one source of truth: identity (name, email, **current location**, **current role**),
education, **base salary**, and the **Skills** shared-bucket manager. Skills here are the global
`{id, name, years}` definitions; roles only *reference* them — editing a skill here never edits a role.

### 5.3 Roles  *(master–detail editor)*
The headline new feature. Left = compact role list (dot · name · skill count · match count, paused
roles flagged, **+ New target role**). Right = a single role editor organized into **three labeled
bands** that make the data-model tiers visible:

1. **Target-defined** (Tier 1) — search query, prefilter title include/exclude, score threshold,
   scoring notes.
2. **Shared, overridable** (Tier 2) — seniority, preferred industries: each shows the inherited
   candidate default *inline* with an "override for this role" toggle + "revert to shared."
3. **Skills applicable** — the shared bucket shown as chips; a check toggles whether each shared
   skill applies to this role (binary — no per-role weighting). **+ target salary** (seeded from
   base salary, editable) and the **linked default resume** live here.

**Resumes** (the per-role resume library) is reached under this destination.

### 5.4 Job Preferences  *(target IA — global)*
The search-wide settings that apply to every role equally and cannot be overridden:
**Locations** (multiple willing-to-work places, one global radius), **Work Models** (onsite /
hybrid / remote multi-select), **Job Types** (Contract / Contract-to-Hire / Full-Time / … ). These
are **hard pull filters** — they exclude postings at ingestion.

### 5.5 Admin
Four operational views:
- **Stats** — pipeline KPIs (ingested / scored / high-match / applied / apply-rate / avg-score) +
  per-target matches table.
- **Job Sources** — provider list (LinkedIn, Indeed, Greenhouse, Lever, HN, Wellfound) with
  drag-priority, last-run/volume/dupe columns, status pills, per-source enable toggle. Hosts the
  **Ingest activity log** (searchable table — §6).
- **LLM & Models** — per-stage model routing (scoring / extraction / dedup / resume-tailoring) +
  provider keys + token budget.
- **System** — schedule & storage, maintenance actions, a red-bordered danger zone.

---

## 6. Cross-cutting surfaces

### 6.1 Right inspector
Slides in from the right (grid column 0 → 360px) when a job row is clicked. Holds the job's score
breakdown, matched/gap skills, verdict, and the **resume tie-in** (pick a per-application resume →
"Attach & apply"). `Esc` or ✕ closes it. This is the designed density-expansion point for richer
detail (full description, application timeline) later.

### 6.2 Ingest log — two distinct surfaces (hybrid, by design)
The user explicitly split this into two forms:

- **User-facing live stream** — a small **Ingest FAB** in the bottom-right of feed/role views opens
  a **horizontal bar that slides up from the bottom**: a LIVE indicator, the source currently being
  scraped, a running count, and a left-scrolling stream of target-colored event chips. Also openable
  from the top-bar ingest indicator. Feed/role views only; auto-closes when navigating away.
- **Admin-facing analytics** — an **Ingest activity log** table under Admin → Job Sources:
  time · source · target · event · detail, with a search box and an event-type filter
  (All · Discovered · Scored · Deduped · Errors).

Both share one event vocabulary so the live chips and the log rows read identically.

---

## 7. Layout & responsive rules (summary — full rules in `design-principles.md`)

- **Alignment by width:** expanding-width elements (fluid grids, tables, `1fr` form columns,
  `auto-fill` tiles, the feed) are **left-aligned and fill** — no `max-width` cap. Fixed-width
  elements (a bounded card/modal/control) are **center-aligned**. The intent is to eliminate the
  dead band of wasted space on the right. Exceptions: prose reading-measures (`~60ch`) stay capped;
  inline fixed controls inside a left-aligned form stay put.
- **Responsive:** the rail collapses to icons at `980px`; the Roles editor's two-pane layout
  collapses at `860px`.
- **State persistence:** the active target persists to `localStorage` (`jm_target`).
- **`data-od-id`** on every major region (`shell`, `rail`, `main`, `context`, `filters`, `feed`,
  `inspector`, `ingest-fab`, `ingest-stream`, `ingest-log`, the per-view ids) so regions are
  individually addressable.

---

## 8. What's locked vs. open

**Locked:** the Shell B three-region layout; the dark ledger visual system; the view-aware context
bar; the feed-only subbar; the inspector pattern; the hybrid ingest log; the Roles master–detail
editor with three tier bands; the alignment rule.

**Open / pending build:**
- The rail's **three-top-level-destination IA** (Candidate Profile · Roles · Job Preferences) is
  the target but **not yet reflected** in the prototype rail (§3.2 callout). The build toward it
  also needs the **Job Preferences** screen and the **Candidate Profile / Skills** screen, which do
  not exist as standalone surfaces yet.
- The Roles editor still needs to be rebuilt against the real schema (see `roles-editor-rebuild.md`)
  — current prototype invents skill tiers and misses several real fields.
- Salary delta-vs-base on feed rows (A.10) and the no-salary red flag are designed but not built.

---

*Companion docs: `data-model.md` (entities/fields/relations — normative), `roles-editor-rebuild.md`
(Roles editor build plan), `design-principles.md` (alignment/visual rules). Keep this file in sync
when the rail IA or any screen's region structure changes.*
