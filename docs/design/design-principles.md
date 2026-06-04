# Design principles — job-matcher redesign

> **Purpose.** Standing layout/visual rules for the job-matcher redesign, so every screen
> tailored from here on stays consistent. Applied across the active Shell B prototype
> (`job-matcher-shell-b-2.html`) and any screens that follow.
>
> Established: 2026-05-29. Keep updated as new principles are locked in.

---

## 1. Alignment by width behavior  (LOCKED 2026-05-29)

The governing rule, stated by the user:

> - **If an element has expanding width → left-aligned.**
> - **If an element has fixed width → center-aligned.**

The intent is to **eliminate wasted space**. The failure mode this fixes: expanding content
(fluid grids, `1fr` columns, `auto-fill` tiles) that was capped to a narrow `max-width` and
pinned left, leaving a dead band of empty canvas on the right.

### How to apply

| Element nature | Behavior | Rule |
|---|---|---|
| **Expanding** — fluid grids, tables, `1fr` form columns, `auto-fill` tile rows, feed lists | Fill the available content width | Left-aligned, no `max-width` cap. Let it stretch. |
| **Fixed** — a card/modal/control with an intrinsic or deliberately bounded width | Sits centered in its container | Center-aligned (e.g. `margin-inline: auto`). |

### Exceptions (NOT wasted space — leave capped)

- **Prose reading-measures.** Description/explainer paragraphs keep a `~60ch` / `62ch`
  `max-width` for line-length legibility. This is typographic control, not a layout cap.
- **Inline fixed-width controls inside a left-aligned form.** A genuinely fixed control
  (e.g. the ~340px skill-add input) stays at its width and stays put within its left-aligned
  parent — it does not get centered in isolation.

### Applied so far

Removed page-level width caps (`880 / 920 / 1040px`) that were pinning expanding content:
Roles workspace, Admin → Stats KPI tiles, Admin tables (Sources, Models, Ingest log) and their
toolbars, Profile cards / account banner / add buttons. All now fill the content column.

### Open watch item

On ultra-wide displays (≥1920px) the Roles **editor** two-column form gets very wide
(~700px/field). The editor is form content with a natural max width — it is the one place
that may warrant the *fixed → centered* branch (cap-and-center) rather than full-bleed.
Not yet applied; revisit if it reads too loose.

---

*Update this file as principles are added or refined. It is the standing rulebook for
per-screen tailoring — anchor new screen work to it.*
