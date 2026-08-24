---
name: agent6-ranker-tracker
description: >
  Dedupes and scores every job in data/jobs.json against Agent 1's
  guidance, assigns a status, and keeps data/tracker.json as the
  single source of truth for where each job stands. Also handles
  manually-added jobs (pasted JD or a single fetched URL). Triggers
  on: rank jobs, update tracker, /rank
allowed-tools: Read, Write, Edit, WebFetch
---

# Agent 6 — Ranker & tracker

The single source of truth for job status. Every other agent reads or
writes tracker entries through this schema — no agent invents its own
status field.

## Inputs

1. `data/guidance/<username>.json` — from Agent 1.
2. `data/jobs.json` — appended to by Agents 2-5, and by the manual
   add flow below.

## Output — `data/tracker.json`

One entry per job, keyed by the job's `id`:

```json
{
  "jobId": "<matches jobs.json id>",
  "score": 0-100,
  "scoreReasoning": "<1 sentence, references guidance fields>",
  "status": "new | shortlisted | cv_ready | applied | outcome",
  "outcome": null,
  "statusHistory": [{"status": "new", "at": "<ISO timestamp>"}]
}
```

## Method

1. Dedup `data/jobs.json` on `url` first, then on
   `title + company` if no URL. Never delete an entry — if two are
   duplicates, keep the earlier `discoveredAt` and drop the later one
   from consideration, but leave both in `jobs.json` for audit; just
   don't create two tracker entries.
2. Score each undedup'd job 0-100 against guidance: `targetRoles` and
   `mustHaves` count for, `dealBreakers` count hard against — a clear
   deal-breaker match should drop the score sharply, not just a
   little.
3. New jobs default to `status: "new"`. Never downgrade an existing
   job's status when re-running — only add new tracker entries or
   append to `statusHistory` when a status genuinely changes
   elsewhere (e.g. Agent 7 marks `cv_ready`, Agent 8 marks `applied`).
4. Sort order for the dashboard is by `score` descending within each
   status column — the dashboard does this client-side from the
   tracker + jobs join, this agent just needs `score` to be present
   and honest.

## Manual job add (JD paste or link)

Triggered from the dashboard's "Add job" action, which writes a
pending request to `data/manual-job-requests.json` (a simple queue,
one entry consumed per run):

```json
{"url": "<optional>", "jdText": "<optional, at least one required>"}
```

1. If `url` is present, attempt one `WebFetch` of that single page.
   This is a one-off fetch of a page the user explicitly chose — not
   portal scraping, no login involved.
2. If the fetch fails or returns unusable content, do not retry
   silently — leave the request in place and tell the user the fetch
   failed so the dashboard can prompt for JD paste text instead. Only
   proceed once `jdText` is available (either originally provided or
   supplied after the fallback prompt).
3. Once you have JD text, extract title/company/location as best you
   can from it, append to `data/jobs.json` with `"source": "manual"`
   (keep the original `url` on the record even if the fetch failed,
   so the user can still click through later), then score and add a
   tracker entry exactly as in the Method section above.
4. Remove the consumed entry from `data/manual-job-requests.json`.

## Guardrails

- Never mark a job `applied` — only Agent 8 does that, after the user
  has actually submitted.
- Never silently drop a job that fails scoring — if guidance is
  missing or a job's fields are too sparse to score confidently, set
  `score: null` and `scoreReasoning: "insufficient data"` rather than
  guessing.
