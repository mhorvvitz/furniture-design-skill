# Skill retrospective feedback loop — design

**Date**: 2026-07-08
**Status**: Approved, pending implementation plan
**Repo**: `github.com/mhorvvitz/furniture-design-skill` (the furniture-design skill; the live skill dir is a symlink to this repo)

## Problem

The furniture-design skill has a reviewer that audits how well the skill served a
real project and emits prioritized, implementation-ready findings. Today it is a
**project-local** agent (`C:\projects\CoffeeTable\.claude\agents\furniture-skill-reviewer.md`),
so it only exists for that one project and must be launched by hand. Two gaps:

1. The reviewer is not part of the skill — a different person installing the skill
   does not get it, and even the author must remember to run it.
2. When the skill *is* used by someone else, the issues their run surfaces never
   come back to the author (`mhorvvitz`), so the skill can't improve from field use.

## Goal

Make the reviewer a **built-in end-of-process step** of the skill that:
- auto-runs when a user finishes a project,
- produces a scrubbed, skill-only findings report, and
- routes that report back to the author as a GitHub issue on the skill repo —
  even when a third party runs the skill on their own machine.

## Decisions (settled)

| Decision | Choice |
|---|---|
| Feedback transport | **GitHub issue** on `mhorvvitz/furniture-design-skill`, filed under the runner's own `gh` account, labelled `skill-feedback`. |
| Trigger | **Auto-run** at end of process; show the report; **confirm before filing** the issue. |
| Issue content | **Skill findings only, project scrubbed** — a generic project-shape descriptor, no client names / addresses / identifying dimensions. |
| Scope | Runs on **every** completed project (including the author's own dogfooding). Fires only at genuine project completion, not on partial deliverables. |
| Portability | Reviewer instructions live **inside the skill** and are launched as a subagent — no dependency on the runner having a registered agent. |

## Architecture

### Components

1. **`references/skill-review-agent.md`** (new, in the skill) — the reviewer's
   charter/prompt, migrated from the project-local agent file and adapted:
   - receives a distilled friction log **in its prompt** (a cold subagent has no
     session context) instead of reading a session memory file;
   - must emit a **scrubbed** report: skill-improvement findings (problem →
     file/function citation → fix, ranked P0/P1/P2) plus a one-line generic
     project-shape descriptor. No names, addresses, or client-identifying
     dimensions.
   - Keeps the existing method: read the skill first (`SKILL.md`, `references/`,
     `scripts/`, `assets/*.json`, `LIMITATIONS.md`); cross-check evidence against
     real code; distinguish skill gaps from project noise; four evaluation axes
     (token/compute, round-trips, inaccuracies, generalization).

2. **SKILL.md "Stage 6 — skill retrospective"** (new workflow step) — instructs
   Claude, once the stage-5 package is delivered and the user is satisfied, to:
   1. Distill a **scrubbed friction log** of this project in skill terms (what
      fought back, what had to be hand-built, what produced a wrong output),
      omitting client-identifying specifics.
   2. Launch the reviewer as a subagent (Agent tool), passing the friction log +
      the skill's file paths. The subagent returns the scrubbed report.
   3. Show the report to the user; if there are findings, ask to file it.
   4. On consent, file the GitHub issue (below). If declined, keep the local report.

3. **Issue-filing step** (in Stage 6 / a helper snippet) —
   ```bash
   gh issue create --repo mhorvvitz/furniture-design-skill \
     --title "skill-review: <project-shape> — <YYYY-MM-DD>" \
     --body-file <report.md> --label skill-feedback
   ```
   - Filed under the runner's own authenticated `gh` account (attribution +
     notifies the author).
   - **Fallback (no `gh` / not authed)**: write the report to
     `output/skill-review-<YYYY-MM-DD>.md` and give the user a prefilled
     `https://github.com/mhorvvitz/furniture-design-skill/issues/new?title=…&body=…&labels=skill-feedback`
     URL so it can still be submitted from a browser.

4. **One-time repo setup** — ensure the `skill-feedback` label exists:
   `gh label create skill-feedback --repo mhorvvitz/furniture-design-skill --color <hex> --description "Field feedback from skill retrospective runs"` (idempotent; ignore "already exists").

### Data flow

```
stage 5 package delivered + user satisfied
   │
   ▼
parent Claude distills a SCRUBBED friction log (skill terms, no client PII)
   │  + skill file paths
   ▼
Agent(reviewer subagent)  ──►  scrubbed P0/P1/P2 skill-findings report
   │
   ▼
parent shows report to user
   │
   ├─ no findings ─────────────► stop (nothing to file)
   ▼
consent to file?
   ├─ yes, gh authed ─────────► gh issue create … --label skill-feedback
   ├─ yes, no gh ─────────────► write output/skill-review-<date>.md + new-issue URL
   └─ no ─────────────────────► keep local report only
```

## Edge cases

- **No findings** → nothing is filed; report may still be shown.
- **`gh` absent or unauthenticated** → local report + prefilled new-issue URL.
- **Label missing on repo** → `gh issue create` still works if the label exists;
  the one-time setup creates it. If label creation is not possible (third-party
  without write access), file the issue **without** the label rather than fail.
- **Third-party lacks any repo access** → public repos accept issues from any
  authenticated GitHub user; if even that fails, fall back to the new-issue URL.
- **Author dogfooding** → identical path; issues simply file under the author's
  own account.

## Out of scope (YAGNI)

- Automated triage/labelling of findings beyond `skill-feedback`.
- Any telemetry beyond the explicit, user-consented issue.
- Aggregation/dashboarding of incoming feedback.
- Changing the reviewer's analytical method or its four evaluation axes.

## Success criteria

- The reviewer travels with the skill: a fresh install exposes it with no extra setup.
- At project end, Claude runs it automatically and shows a scrubbed report.
- With consent, a `skill-feedback` issue appears on the repo, attributed to the runner,
  containing skill findings and a generic project-shape — no client-identifying data.
- Every failure mode degrades to a local report + a manual submit URL, never a hard stop.
