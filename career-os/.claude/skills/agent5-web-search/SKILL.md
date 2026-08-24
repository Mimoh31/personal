---
name: agent5-web-search
description: >
  Searches the open web for job postings matching the user's guidance
  from Agent 1, dedupes against jobs already in the store, and appends
  new candidates to data/jobs.json. Triggers on: search for jobs,
  find jobs, web search jobs, /scrape web
allowed-tools: Read, Write, WebSearch, WebFetch
---

# Agent 5 — Web job search

Read-only on guidance and the existing job list; append-only on
`data/jobs.json`. This agent never logs into a portal and never
scrapes a site that requires authentication — open web search and
public job listing pages only.

## Inputs (read-only)

1. `data/guidance/<username>.json` — written by Agent 1. If this file
   doesn't exist yet, stop and tell the user to run Agent 1 first;
   don't guess at target roles.
2. `data/jobs.json` — the existing job store, used only for dedup
   (match on `url`, falling back to `title` + `company` if no URL).

## Output (append-only)

Add new entries to the `data/jobs.json` array. Each job object:

```json
{
  "id": "<uuid or hash of url>",
  "title": "<job title>",
  "company": "<company name>",
  "location": "<location string>",
  "url": "<posting url>",
  "source": "web",
  "description": "<full or truncated JD text>",
  "postedAt": "<ISO date if known, else null>",
  "discoveredAt": "<ISO timestamp of this run>",
  "status": "new"
}
```

Never overwrite or remove existing entries in `data/jobs.json` — only
append jobs that are genuinely new after dedup.

## Method

1. Load guidance; build 3-5 search queries from `targetRoles` +
   `mustHaves`, respecting `dealBreakers` as negative filters where
   the search syntax allows it (e.g. exclude on-site-only roles if
   `dealBreakers` includes "No relocation" and the role is tagged
   onsite).
2. Run WebSearch per query. WebFetch individual promising listings to
   pull the full JD text when the search snippet is too thin to judge
   fit.
3. Dedup against `data/jobs.json` before appending.
4. Do not rank or score here — that's Agent 6's job. This agent's only
   responsibility is: find candidates, normalize the schema, dedup,
   append.
5. Report a short summary back to the user: how many new jobs found,
   how many were duplicates, which queries came up empty.

## Guardrails

- No login flows, ever. If a search result requires sign-in to view
  the full posting, keep whatever is visible from the public
  search/listing page and note the limitation in `description` rather
  than attempting to authenticate.
- Respect `dealBreakers` from guidance — don't add jobs that
  obviously violate a stated deal-breaker (e.g. visa sponsorship not
  offered when the user requires it) unless the listing is ambiguous,
  in which case add it but leave a note in `description`.
