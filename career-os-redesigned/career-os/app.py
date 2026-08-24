import json
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

BASE = Path(__file__).parent
DATA = BASE / "data"
CV_LIB = BASE / "cv-library"
LINKEDIN_IMPORTS = DATA / "profile-imports" / "linkedin"

app = Flask(__name__, static_folder="static", static_url_path="")


def load_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# --- Static dashboard ---
@app.route("/")
def index():
    return send_from_directory("static", "index.html")


# --- Accounts (plain local login, no real security by design) ---
@app.route("/api/accounts", methods=["GET"])
def list_accounts():
    accounts = load_json(DATA / "accounts.json", {})
    return jsonify(list(accounts.keys()))


@app.route("/api/accounts", methods=["POST"])
def create_account():
    body = request.get_json(force=True)
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400
    accounts = load_json(DATA / "accounts.json", {})
    if username in accounts:
        return jsonify({"error": "That username already exists."}), 409
    accounts[username] = {"password": password}
    save_json(DATA / "accounts.json", accounts)
    (CV_LIB / username).mkdir(parents=True, exist_ok=True)
    (LINKEDIN_IMPORTS / username).mkdir(parents=True, exist_ok=True)
    return jsonify({"ok": True})


@app.route("/api/login", methods=["POST"])
def login():
    body = request.get_json(force=True)
    username = body.get("username") or ""
    password = body.get("password") or ""
    accounts = load_json(DATA / "accounts.json", {})
    account = accounts.get(username)
    if not account or account.get("password") != password:
        return jsonify({"error": "That username or password doesn't match."}), 401
    return jsonify({"ok": True, "username": username})


# --- Profile ---
@app.route("/api/profile/<username>", methods=["GET"])
def get_profile(username):
    profile = load_json(DATA / "profiles" / f"{username}.json", {})
    return jsonify(profile)


@app.route("/api/profile/<username>", methods=["POST"])
def save_profile(username):
    body = request.get_json(force=True)
    save_json(DATA / "profiles" / f"{username}.json", body)
    return jsonify({"ok": True})


# --- Guidance (written by Agent 1, read-only from the dashboard) ---
@app.route("/api/guidance/<username>", methods=["GET"])
def get_guidance(username):
    guidance = load_json(DATA / "guidance" / f"{username}.json", None)
    return jsonify(guidance)


# --- Dashboard summary (landing page after login) ---
@app.route("/api/dashboard-summary/<username>", methods=["GET"])
def dashboard_summary(username):
    tracker = load_json(DATA / "tracker.json", [])
    guidance_path = DATA / "guidance" / f"{username}.json"
    return jsonify({
        "jobsCount": len(load_json(DATA / "jobs.json", [])),
        "shortlisted": sum(1 for t in tracker if t.get("status") == "shortlisted"),
        "cvReady": sum(1 for t in tracker if t.get("status") == "cv_ready"),
        "applied": sum(1 for t in tracker if t.get("status") == "applied"),
        "guidanceReady": guidance_path.exists(),
    })


# --- Agent trigger queue (dashboard can't run agents itself; Claude Code polls this) ---
@app.route("/api/agent-trigger", methods=["POST"])
def agent_trigger():
    import datetime
    body = request.get_json(force=True)
    agent = body.get("agent")
    username = body.get("username")
    if not agent or not username:
        return jsonify({"error": "agent and username are required"}), 400
    queue = load_json(DATA / "agent-requests.json", [])
    queue.append({
        "agent": agent,
        "username": username,
        "requestedAt": datetime.datetime.utcnow().isoformat() + "Z"
    })
    save_json(DATA / "agent-requests.json", queue)
    return jsonify({"ok": True, "queued": len(queue)})


@app.route("/api/agent-trigger", methods=["GET"])
def agent_trigger_list():
    return jsonify(load_json(DATA / "agent-requests.json", []))


# --- Jobs (written by Agents 2-5, read by the dashboard) ---
@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    jobs = load_json(DATA / "jobs.json", [])
    return jsonify(jobs)


# --- Tracker (written by Agent 6, read by the dashboard) ---
@app.route("/api/tracker", methods=["GET"])
def get_tracker():
    tracker = load_json(DATA / "tracker.json", [])
    return jsonify(tracker)


@app.route("/api/board", methods=["GET"])
def get_board():
    """Joined view: jobs + tracker status, for the ranked board."""
    jobs = {j["id"]: j for j in load_json(DATA / "jobs.json", [])}
    tracker = load_json(DATA / "tracker.json", [])
    board = []
    for t in tracker:
        job = jobs.get(t["jobId"])
        if not job:
            continue
        board.append({**job, **t})
    return jsonify(board)


# --- Manual job add: try fetching a link first, fall back to JD paste ---
@app.route("/api/manual-job/fetch", methods=["POST"])
def manual_job_fetch():
    import re
    import requests

    body = request.get_json(force=True)
    url = (body.get("url") or "").strip()
    if not url:
        return jsonify({"ok": False, "error": "No link provided."}), 400
    try:
        resp = requests.get(url, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200 or not resp.text:
            return jsonify({"ok": False, "error": f"Site returned status {resp.status_code}."})
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 200:
            return jsonify({"ok": False, "error": "Page returned too little readable content."})
        return jsonify({"ok": True, "text": text[:6000]})
    except Exception as e:
        return jsonify({"ok": False, "error": "Couldn't reach that link."})


@app.route("/api/manual-job", methods=["POST"])
def manual_job():
    body = request.get_json(force=True)
    url = (body.get("url") or "").strip()
    jd_text = (body.get("jdText") or "").strip()
    if not url and not jd_text:
        return jsonify({"error": "Provide a link or a job description."}), 400
    queue = load_json(DATA / "manual-job-requests.json", [])
    queue.append({"url": url, "jdText": jd_text})
    save_json(DATA / "manual-job-requests.json", queue)
    return jsonify({"ok": True, "queued": len(queue)})


# --- Apply queue (prepared by Agent 8, submission confirmed by the user) ---
@app.route("/api/apply-queue/<username>", methods=["GET"])
def apply_queue(username):
    tracker = load_json(DATA / "tracker.json", [])
    jobs = {j["id"]: j for j in load_json(DATA / "jobs.json", [])}
    queue = []
    for t in tracker:
        if t.get("status") != "cv_ready":
            continue
        job = jobs.get(t["jobId"])
        if not job:
            continue
        package = load_json(DATA / "apply-queue" / username / f"{t['jobId']}.json", None)
        queue.append({**job, **t, "package": package})
    return jsonify(queue)


@app.route("/api/apply-queue/<username>/<job_id>/mark-applied", methods=["POST"])
def mark_applied(username, job_id):
    import datetime
    tracker = load_json(DATA / "tracker.json", [])
    found = False
    for t in tracker:
        if t.get("jobId") == job_id:
            t["status"] = "applied"
            t.setdefault("statusHistory", []).append(
                {"status": "applied", "at": datetime.datetime.utcnow().isoformat() + "Z"}
            )
            found = True
    if not found:
        return jsonify({"error": "Job not found in tracker."}), 404
    save_json(DATA / "tracker.json", tracker)
    return jsonify({"ok": True})


# --- CV tailoring (written by Agent 7, decided by the user here) ---
@app.route("/api/cv-tailoring/<username>/<job_id>", methods=["GET"])
def get_cv_tailoring(username, job_id):
    data = load_json(DATA / "cv-tailoring" / username / f"{job_id}.json", None)
    return jsonify(data)


@app.route("/api/cv-tailoring/<username>/<job_id>/decision", methods=["POST"])
def cv_tailoring_decision(username, job_id):
    body = request.get_json(force=True)
    decision = body.get("decision")
    if decision not in ("approve", "reject"):
        return jsonify({"error": "decision must be approve or reject"}), 400

    path = DATA / "cv-tailoring" / username / f"{job_id}.json"
    tailoring = load_json(path, None)
    if tailoring is None:
        return jsonify({"error": "No tailoring draft found for this job."}), 404
    tailoring["status"] = "approved" if decision == "approve" else "rejected"
    save_json(path, tailoring)

    if decision == "approve":
        tracker = load_json(DATA / "tracker.json", [])
        for t in tracker:
            if t.get("jobId") == job_id:
                t["status"] = "cv_ready"
                t.setdefault("statusHistory", []).append(
                    {"status": "cv_ready", "at": __import__("datetime").datetime.utcnow().isoformat() + "Z"}
                )
        save_json(DATA / "tracker.json", tracker)

    return jsonify({"ok": True, "status": tailoring["status"]})


@app.route("/api/cv-download/<username>/<job_id>", methods=["GET"])
def cv_download(username, job_id):
    folder = CV_LIB / username / "tailored"
    for ext in ("docx", "pdf"):
        candidate = folder / f"{job_id}.{ext}"
        if candidate.exists():
            return send_from_directory(folder, candidate.name, as_attachment=True)
    return jsonify({"error": "No tailored file found yet."}), 404


# --- Inbox status (for the Inbox & folders view) ---
@app.route("/api/inbox-status", methods=["GET"])
def inbox_status():
    def count_pending(folder):
        if not folder.exists():
            return 0
        return len([p for p in folder.iterdir() if p.is_file() and p.name != ".gitkeep"])

    def count_cv_files(username):
        folder = CV_LIB / username
        if not folder.exists():
            return 0
        return len([p for p in folder.iterdir() if p.is_file()])

    username = request.args.get("username", "")
    return jsonify({
        "linkedin": count_pending(BASE / "inbox" / "linkedin"),
        "naukri": count_pending(BASE / "inbox" / "naukri"),
        "indeed": count_pending(BASE / "inbox" / "indeed"),
        "cvLibrary": count_cv_files(username) if username else 0
    })


# --- CV uploads (multiple files at once) ---
@app.route("/api/upload/cv/<username>", methods=["POST"])
def upload_cv(username):
    folder = CV_LIB / username
    folder.mkdir(parents=True, exist_ok=True)
    saved = []
    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        dest = folder / f.filename
        f.save(dest)
        saved.append(f.filename)
    return jsonify({"saved": saved})


@app.route("/api/cv-list/<username>", methods=["GET"])
def cv_list(username):
    folder = CV_LIB / username
    if not folder.exists():
        return jsonify([])
    return jsonify(sorted(p.name for p in folder.iterdir() if p.is_file()))


# --- LinkedIn import (data export .zip, or a profile URL saved to profile) ---
@app.route("/api/upload/linkedin/<username>", methods=["POST"])
def upload_linkedin(username):
    folder = LINKEDIN_IMPORTS / username
    folder.mkdir(parents=True, exist_ok=True)
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "No file received."}), 400
    dest = folder / f.filename
    f.save(dest)
    return jsonify({"saved": f.filename})


if __name__ == "__main__":
    app.run(debug=False, threaded=True, port=5000)
