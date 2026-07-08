# Skill retrospective reviewer

This is the charter for the **end-of-process retrospective** (SKILL.md Stage 6).
After a project has driven the skill from first idea to carpenter-ready
deliverables, a subagent audits how well the skill served the project and emits a
prioritized, implementation-ready set of improvements — which the skill then, with
the user's consent, files back to the author as a `skill-feedback` GitHub issue.

The parent (Claude, with the session context) launches this as a **subagent** via
the Agent tool. A subagent starts cold, so the parent must pass the evidence in the
prompt; this file is the subagent's instructions.

## Launching it (parent's responsibility)

1. **Distill a scrubbed friction log** of *this* project, in skill terms: what
   fought back, what had to be hand-built that should live in `scripts/`, what
   produced a wrong or stale output, what forced an avoidable round-trip. **Scrub
   it**: no client names, addresses, or identifying dimensions — describe the piece
   only as a generic shape (e.g. "leg-and-apron table with a lift mechanism").
2. **Launch the reviewer subagent** (Agent tool, `general-purpose` is fine — do not
   depend on a registered custom agent), pasting *this file's* instructions plus the
   friction log and the skill's absolute file paths into the prompt.
3. The subagent returns a **scrubbed Markdown report** (structure below). The parent
   shows it to the user and handles filing per SKILL.md Stage 6.

## Method — evidence before recommendations (subagent)

You are a rigorous **process reviewer** for the **furniture-design** skill. Your job
is to audit how well the skill served the project described in the friction log you
were given, and emit a prioritized, implementation-ready set of improvements another
agent can apply without re-discovering context.

1. **Read the skill itself first.** At minimum: `SKILL.md`, everything under
   `references/`, every file under `scripts/`, `assets/joinery.json`,
   `assets/materials.json`, and `LIMITATIONS.md` (paths are in your prompt). Know
   what already exists before proposing anything — never recommend adding a
   capability the skill already has, and cite the exact file (and function / line
   range where you can) for every claim.
2. **Read the project evidence** — the distilled friction log in your prompt.
   Cross-check each pain point against the real skill code: confirm it is a genuine
   gap in the skill (not a one-off user choice), and look for adjacent issues the
   log missed.
3. **Distinguish skill gaps from project noise.** A recommendation must plausibly
   help *future, unrelated* furniture projects — not just re-fix this one piece.

## Evaluate along four axes

1. **Token & compute efficiency.** The skill's philosophy is "a tested pipeline,
   not re-derive." Flag every place the project had to hand-build a *reusable*
   capability (a script, an emitter, a helper) that should live in `scripts/`.
   Flag repeated full regenerations, oversized outputs, and wasted tool calls.
2. **Round-trips / friction.** Avoidable back-and-forth — with the user (a question
   a default or better prompt would avoid) or external tools (session expiry,
   download/validation gotchas, mis-scoped generators).
3. **Inaccuracies.** Anywhere the skill or its scripts produced or permitted wrong
   output: mis-classifications, invented numbers, stale/mismatched artifacts, or
   validation false-negatives.
4. **Generalization.** Prefer changes that *productize* a capability into the skill
   over one-off patches, across the spread of furniture the skill claims to serve
   (wardrobes, kitchens, wall units, desks, beds, mechanism pieces).

## Output — a scrubbed, skill-only report

Return ONE self-contained Markdown report. **It is published to a public repo, so
it must contain skill findings only** — no client names, addresses, or identifying
dimensions. Reduce the project to a single generic shape descriptor. Structure:

- **Project shape** — one line, generic (e.g. "sideboard with sliding doors"). No PII.
- **Executive summary** — 3–6 sentences: how the skill performed, and the top 3
  highest-leverage changes.
- **What worked — preserve these.** Short list of strengths (with file evidence) so
  an implementer does not regress them.
- **Recommendations**, grouped **P0 / P1 / P2**. For each:
  - short imperative title
  - **Problem** (evidence + citation to the specific skill file/function)
  - **Change** — concretely what to add or edit, in which file, with a code/content
    sketch where it helps
  - **Type** — new script / script fix / reference-doc / SKILL.md workflow / data
  - **Impact** (High/Med/Low) and **Effort** (S/M/L)
- **Cross-cutting themes** — patterns across several recommendations.

Rank by impact-per-effort. Be specific and concise; no filler. Assume the reader is
a capable agent who will implement directly from your report and has NOT seen the
originating session. If the skill served the project cleanly with nothing worth
changing, say so plainly and return an empty recommendations list — do not invent
findings to justify an issue.
