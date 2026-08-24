"""
End-to-end smoke test for Career OS's plumbing (Phases 0-6).

This does NOT test the agents' AI reasoning (that only runs inside
Claude Code). It tests every mechanical path the dashboard depends
on: accounts, profile, guidance display, jobs/board join, manual job
add fetch-fail fallback, CV tailoring decision -> tracker transition,
and apply-queue mark-applied -> tracker transition.

Run with the Flask app already running on localhost:5000:
    python3 app.py &
    python3 tests/smoke_test.py

Uses a throwaway test account and cleans up after itself.
"""
import json
import sys
from pathlib import Path

import requests

BASE = "http://127.0.0.1:5000"
USER = "smoke-test-user"
PASS = "smoke-test-pass"
ROOT = Path(__file__).parent.parent

passed = 0
failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ok   {name}")
    else:
        failed += 1
        print(f"  FAIL {name}")


def main():
    print("== accounts + login ==")
    r = requests.post(f"{BASE}/api/accounts", json={"username": USER, "password": PASS})
    check("create account", r.status_code == 200)

    r = requests.post(f"{BASE}/api/login", json={"username": USER, "password": PASS})
    check("login with correct password", r.status_code == 200)

    r = requests.post(f"{BASE}/api/login", json={"username": USER, "password": "wrong"})
    check("login rejects wrong password", r.status_code == 401)

    print("== profile ==")
    profile = {"guardrails": "Never remove certifications.", "salaryExpected": "40 LPA"}
    r = requests.post(f"{BASE}/api/profile/{USER}", json=profile)
    check("save profile", r.status_code == 200)
    r = requests.get(f"{BASE}/api/profile/{USER}")
    check("profile persists", r.json().get("guardrails") == profile["guardrails"])

    print("== guidance (simulated Agent 1 output) ==")
    guidance_path = ROOT / "data" / "guidance" / f"{USER}.json"
    guidance_path.parent.mkdir(parents=True, exist_ok=True)
    guidance_path.write_text(json.dumps({
        "generatedAt": "2026-01-01T00:00:00Z",
        "targetRoles": ["Test role"], "seniority": "Senior",
        "mustHaves": [], "dealBreakers": [], "strengths": [], "gaps": [],
        "notes": "test"
    }))
    r = requests.get(f"{BASE}/api/guidance/{USER}")
    check("guidance readable", r.json() is not None)

    print("== jobs + board ==")
    jobs_path = ROOT / "data" / "jobs.json"
    tracker_path = ROOT / "data" / "tracker.json"
    jobs_path.write_text(json.dumps([
        {"id": "smoke1", "title": "Smoke test role", "company": "Acme",
         "location": "Remote", "url": "https://example.com/smoke1",
         "source": "web", "description": "...", "postedAt": None,
         "discoveredAt": "2026-01-01T00:00:00Z", "status": "new"}
    ]))
    tracker_path.write_text(json.dumps([
        {"jobId": "smoke1", "score": 90, "scoreReasoning": "test",
         "status": "shortlisted", "outcome": None,
         "statusHistory": [{"status": "new", "at": "2026-01-01T00:00:00Z"}]}
    ]))
    r = requests.get(f"{BASE}/api/board")
    board = r.json()
    check("board joins jobs + tracker", any(j["id"] == "smoke1" and j["status"] == "shortlisted" for j in board))

    print("== manual job add: fetch failure falls back correctly ==")
    r = requests.post(f"{BASE}/api/manual-job/fetch", json={"url": "https://this-does-not-resolve-xyz123.invalid"})
    check("bad url returns ok:false, not a crash", r.status_code == 200 and r.json()["ok"] is False)

    r = requests.post(f"{BASE}/api/manual-job", json={"url": "https://x.com", "jdText": "Test JD text"})
    check("manual job queues after fallback", r.status_code == 200 and r.json()["ok"])

    print("== CV tailoring approve -> cv_ready ==")
    tailoring_dir = ROOT / "data" / "cv-tailoring" / USER
    tailoring_dir.mkdir(parents=True, exist_ok=True)
    (tailoring_dir / "smoke1.json").write_text(json.dumps({
        "jobId": "smoke1", "baseCv": "test.pdf",
        "guardrailsApplied": "Never remove certifications.",
        "changes": [{"existing": "old line", "modified": "new line"}],
        "reviewerNotes": "test", "generatedAt": "2026-01-01T00:00:00Z",
        "status": "pending_review"
    }))
    r = requests.post(f"{BASE}/api/cv-tailoring/{USER}/smoke1/decision", json={"decision": "approve"})
    check("approve decision succeeds", r.status_code == 200)

    tracker = json.loads(tracker_path.read_text())
    check("tracker moved to cv_ready after approve", tracker[0]["status"] == "cv_ready")

    print("== apply queue: mark applied -> applied ==")
    r = requests.get(f"{BASE}/api/apply-queue/{USER}")
    check("job appears in apply queue when cv_ready", len(r.json()) == 1)

    r = requests.post(f"{BASE}/api/apply-queue/{USER}/smoke1/mark-applied")
    check("mark-applied succeeds", r.status_code == 200)

    tracker = json.loads(tracker_path.read_text())
    check("tracker moved to applied", tracker[0]["status"] == "applied")

    r = requests.get(f"{BASE}/api/apply-queue/{USER}")
    check("job leaves apply queue once applied", len(r.json()) == 0)

    print("== inbox status ==")
    r = requests.get(f"{BASE}/api/inbox-status?username={USER}")
    check("inbox status responds", r.status_code == 200)

    # --- cleanup ---
    print("== cleanup ==")
    accounts = json.loads((ROOT / "data" / "accounts.json").read_text())
    accounts.pop(USER, None)
    (ROOT / "data" / "accounts.json").write_text(json.dumps(accounts))
    jobs_path.write_text("[]")
    tracker_path.write_text("[]")
    (ROOT / "data" / "manual-job-requests.json").unlink(missing_ok=True)
    guidance_path.unlink(missing_ok=True)
    (tailoring_dir / "smoke1.json").unlink(missing_ok=True)
    (ROOT / "data" / "profiles" / f"{USER}.json").unlink(missing_ok=True)
    print("  cleaned up test data")

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
