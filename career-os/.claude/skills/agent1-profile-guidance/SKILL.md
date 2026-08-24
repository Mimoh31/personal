---
name: agent1-profile-guidance
description: >
  Reads the logged-in user's profile, CV files, and LinkedIn import, and
  produces structured role guidance that every other agent (search,
  ranking, CV tailoring) reads before doing its own job. Triggers on:
  build profile guidance, generate guidance, refresh guidance, /guide
allowed-tools: Read, Write, Glob, Bash(python3 -m json.tool *)
---

# Agent 1 — Career profile guidance

This is the only agent allowed to read the raw resume/CV content and
turn it into structured guidance. Every downstream agent (search,
ranker, CV tailor) reads the guidance output, not the raw files —
so getting this step right matters more than any other single agent.

## Inputs (read-only)

1. `data/profiles/<username>.json` — preferences saved from the
   dashboard's profile screen: salary, relocation, notice period,
   portfolio link, work authorization, guardrails.
2. `cv-library/<username>/*` — every CV version the user uploaded.
   Read all of them; don't assume the first file is representative.
3. `data/profile-imports/linkedin/<username>/*` — LinkedIn export, if
   present. Optional — proceed without it if missing.

## Output (write-only, this agent owns this file)

Write `data/guidance/<username>.json` with this shape:

```json
{
  "generatedAt": "<ISO timestamp>",
  "targetRoles": ["<role 1>", "<role 2>", "..."],
  "seniority": "<e.g. senior / staff / lead>",
  "mustHaves": ["<derived from profile prefs + resume signals>"],
  "dealBreakers": ["<e.g. from work authorization, relocation=no>"],
  "strengths": ["<3-5 things the resume actually demonstrates>"],
  "gaps": ["<honest gaps between resume and the target roles above>"],
  "notes": "<1-2 sentence plain-language summary for the human>"
}
```

## Method

1. Read every CV in `cv-library/<username>/`. If there are multiple
   versions, note what's consistent across all of them (that's signal)
   versus what differs (that's the person hedging between role types —
   surface this in `notes`).
2. Cross-check `mustHaves` and `dealBreakers` against the saved
   preferences — e.g. `relocate: "no"` becomes a deal-breaker for
   onsite-only roles; a stated work authorization constraint becomes a
   deal-breaker for roles that don't sponsor.
3. Be honest in `gaps`. A guidance file that only flatters the resume
   is worse than useless downstream — the ranker and CV tailor both
   depend on gaps being real.
4. Do not invent experience or skills not evidenced in the CVs.
5. Write the JSON file. Do not modify anything in `cv-library/` or
   `data/profiles/` — this agent is read-only on its inputs.

## When to re-run

Whenever a CV is added/changed, or the profile preferences are edited.
The dashboard's Guidance panel shows whatever this file last
contained, plus its `generatedAt` timestamp, so a stale guidance file
is visible, not silent.
