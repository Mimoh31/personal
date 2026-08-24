# Career OS — Phase 0 through 6 (complete)

All eight agents from the original blueprint are built and verified.
Every agent runs *inside a Claude Code session opened on this
folder* — they are skills Claude Code follows using your
subscription, not background services and not API calls. The
dashboard (this Flask app) is the viewer/editor of the data they read
and write; it never does the AI reasoning itself.

## What each phase added

- **Phase 0** — login, account creation (supports 2+ local accounts,
  plain-text by design, no real security), and the profile setup
  screen: CV multi-file upload, LinkedIn export/URL capture,
  portfolio link, work authorization, salary/relocation/notice
  preferences, and a guardrails field.
- **Phase 1 — Agent 1** (`agent1-profile-guidance`): reads your CVs
  and preferences, writes `data/guidance/<username>.json`. Shown
  read-only in the Profile view's Guidance panel.
- **Phase 2 — Agent 5** (`agent5-web-search`): reads guidance,
  searches the open web only — no logins, no scraping behind auth —
  appends candidates to `data/jobs.json`. Shown in the Job feed view.
- **Phase 3 — Agent 6** (`agent6-ranker-tracker`): dedupes and scores
  every job against guidance, owns `data/tracker.json`. Drives the
  Ranked board's kanban (New / Shortlisted / CV ready / Applied). Also
  handles the "Add job" manual flow: the dashboard backend attempts
  one live fetch of a pasted link itself (`/api/manual-job/fetch` —
  plain HTTP, no Claude Code needed for this part); if it fails, the
  modal falls back to a JD paste box, exactly as designed. The fetch
  failure path is verified; the success path uses plain
  `requests.get()` and will work on a normal internet connection —
  it couldn't be verified from inside the sandboxed environment this
  was built in, which blocks non-allowlisted domains.
- **Phase 4 — Agents 2-4** (`agents234-inbox-parsers`): parse
  whatever's manually dropped into `inbox/linkedin/`, `inbox/naukri/`,
  `inbox/indeed/` — LinkedIn's data export, page saves, CSVs, or
  plain URL lists — into the same job schema Agent 5 uses. No logins,
  ever. The Inbox & folders view shows real pending-file counts.
- **Phase 5 — Agent 7** (`agent7-cv-tailor`): a drafter/reviewer
  pair. Reads guardrails from your profile as a hard constraint,
  proposes explicit before/after line changes, enforces a real
  one-page render via the docx/pdf skill (not font-shrinking), and
  writes a downloadable tailored file. Approving in the CV workspace
  moves the tracker status to `cv_ready`.
- **Phase 6 — Agent 8** (`agent8-apply-queue`): assembles the
  tailored CV, an optional cover letter draft, and screening-question
  answers pulled from your profile into a review package for any
  `cv_ready` job. It cannot submit an application under any
  circumstance. The Application queue view lists these jobs with an
  "I submitted this — mark applied" button that requires explicit
  confirmation and only updates the tracker.

Every one of these transitions was tested end-to-end via direct API
calls before being packaged — not just visually checked in the
dashboard. `tests/smoke_test.py` automates all of it: run the app,
then `python3 tests/smoke_test.py` re-verifies every mechanical
transition (accounts, profile, board join, manual-add fallback,
CV-tailoring approve, mark-applied) in one shot and cleans up after
itself. Useful to re-run after any future change to `app.py`.

## Open it (Windows: double-click `start.bat`, Mac/Linux: double-click or run `./start.sh`)

The first run installs Flask automatically. Every run after that
opens your browser straight to the login screen — no terminal
commands needed once it's set up. This is a real local app: your
data stays on your machine, nothing is hosted anywhere, and it costs
nothing to run.

## Run it locally (manual, if you'd rather not use the launcher)

```bash
cd career-os
pip install -r requirements.txt --break-system-packages   # or use a venv
python3 app.py
```

Open http://127.0.0.1:5000 — create an account, log in, upload a
couple of CVs, save your profile, then open a Claude Code session in
this same folder and say things like "generate guidance", "search
for jobs", "rank jobs", "parse inbox", "tailor cv for this job", or
"prep application" to trigger the corresponding agent.

## What's real vs. what needs Claude Code

- **Real right now, no Claude Code needed**: accounts, login, profile
  save/load, CV upload, the manual job-add fetch attempt, viewing
  whatever any agent has already written, marking a job applied.
- **Needs a Claude Code session on this folder**: all the actual AI
  reasoning — generating guidance, searching the web, scoring jobs,
  parsing inbox exports, tailoring CVs, prepping applications. The
  dashboard displays their output; it doesn't generate it.
- **No security**: passwords are stored in plain text in
  `data/accounts.json`, by design, since this is a local single-user
  tool with no real auth requirement.

## Publishing to your own repo

Personal data never leaves your machine — `.gitignore` excludes
`data/accounts.json`, `data/profiles/`, `data/profile-imports/`,
`data/guidance/`, `data/cv-tailoring/`, `data/apply-queue/`, and
everything inside `cv-library/` and `inbox/*` except the `.gitkeep`
placeholders. Only the app code, skill definitions, and empty folder
structure get published.

```bash
git init
git add -A
git status   # sanity check: should NOT list accounts.json, profiles/, or any cv/job data
git commit -m "Career OS: all 8 agents, Phase 0-6"
git remote add origin <your-repo-url>
git push -u origin main
```

## Folder map

```
career-os/
  app.py              backend: accounts, profile, guidance, jobs, tracker,
                       cv-tailoring decisions, apply-queue, uploads
  static/             dashboard - all 7 screens
  .claude/skills/
    agent1-profile-guidance/SKILL.md
    agent5-web-search/SKILL.md
    agent6-ranker-tracker/SKILL.md
    agents234-inbox-parsers/SKILL.md
    agent7-cv-tailor/SKILL.md
    agent8-apply-queue/SKILL.md
  data/
    accounts.json              gitignored - local login credentials
    profiles/                  gitignored - per-account profile data
    profile-imports/           gitignored - LinkedIn export uploads
    guidance/                  gitignored - Agent 1's output
    jobs.json                  Agents 2-5 append here
    tracker.json               Agent 6 owns this - status per job
    manual-job-requests.json   gitignored - queue for manual add flow
    cv-tailoring/              gitignored - Agent 7's drafts + decisions
    apply-queue/               gitignored - Agent 8's prepared packages
  cv-library/
    <username>/                gitignored - your uploaded CV versions
    <username>/tailored/       gitignored - Agent 7's output files
  inbox/
    linkedin/                  gitignored contents - Agent 2 parses this
    naukri/                    gitignored contents - Agent 3 parses this
    indeed/                    gitignored contents - Agent 4 parses this
```

## What's next

This completes the original 8-agent blueprint - everything from here
is refinement, not new architecture:

- Real resume/CV content in place of test data
- Tuning Agent 6's scoring against how it actually ranks your real jobs
- Iterating on guardrails once you see what Agent 7 actually produces
  against real job descriptions
- Trying the manual "Add job" fetch against real postings once
  running outside this sandboxed build environment
- Adding real LinkedIn/Naukri/Indeed exports to test Agents 2-4
  against actual file formats rather than the dummy CSVs used here
