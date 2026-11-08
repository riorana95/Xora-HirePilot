'''
Develop by Rana Rahul

Auto Job Applier - Web Dashboard
'''

import collections
import csv
import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from modules.config_manager import get_all_config, save_config, sync_active_profile
from modules.profile_manager import (
    list_profiles, get_profile, create_profile, update_profile,
    delete_profile, activate_profile, create_default_profile_from_config,
)

app = Flask(__name__)
CORS(app)

PROJECT_ROOT = Path(__file__).resolve().parent
PATH = PROJECT_ROOT / "all excels"
BOT_SCRIPTS = {
    "linkedin": PROJECT_ROOT / "runAiBot.py",
    "naukri": PROJECT_ROOT / "runNaukriBot.py",
}

_bot_process: subprocess.Popen | None = None
_bot_platform: str | None = None
_bot_lock = threading.Lock()

bot_output_lines = collections.deque(maxlen=500)
bot_output_lock = threading.Lock()
_bot_reader_thread = None

def _read_bot_output(proc):
    for line in iter(proc.stdout.readline, ''):
        if line:
            with bot_output_lock:
                bot_output_lines.append(line.rstrip())
    proc.stdout.close()

def _bot_running() -> bool:
    global _bot_process
    return _bot_process is not None and _bot_process.poll() is None


@app.route("/")
def home():
    return render_template("dashboard.html")


@app.route("/api/config", methods=["GET"])
def api_get_config():
    try:
        return jsonify(get_all_config())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/config", methods=["POST"])
def api_save_config():
    try:
        data = request.get_json(silent=True) or {}
        sections = data.get("sections", data)
        save_config(sections)
        return jsonify({"message": "Configuration saved successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/bot/status", methods=["GET"])
def api_bot_status():
    return jsonify({"running": _bot_running(), "platform": _bot_platform})


@app.route("/api/bot/start", methods=["POST"])
def api_bot_start():
    global _bot_process, _bot_platform
    data = request.get_json(silent=True) or {}
    platform = data.get("platform", request.args.get("platform", "linkedin")).lower()
    if platform not in BOT_SCRIPTS:
        return jsonify({"error": f"Unknown platform: {platform}"}), 400
    with _bot_lock:
        if _bot_running():
            return jsonify({"error": f"Bot is already running ({_bot_platform})"}), 409
        try:
            env = os.environ.copy()
            env["LAUNCHED_FROM_UI"] = "1"
            # The bot's log lines contain Unicode (job titles, arrows, rupee
            # signs). Without these, Windows pipes default to cp1252 and every
            # such line crashed the logger ('charmap' codec error), leaving the
            # dashboard console blank and log.txt riddled with holes.
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONUNBUFFERED"] = "1"
            # Sync active profile into config files before launching bot
            try:
                sync_active_profile()
            except Exception as sync_err:
                print(f"Profile sync warning: {sync_err}")
            script = BOT_SCRIPTS[platform]
            _bot_process = subprocess.Popen(
                [sys.executable, str(script), "--no-alerts"],
                cwd=str(PROJECT_ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )
            global _bot_reader_thread
            _bot_reader_thread = threading.Thread(target=_read_bot_output, args=(_bot_process,), daemon=True)
            _bot_reader_thread.start()
            _bot_platform = platform
            # Early-exit detection: a config/import crash kills the process
            # within a second or two; surface it instead of reporting success.
            import time as _time
            _time.sleep(1.5)
            if _bot_process.poll() is not None:
                with bot_output_lock:
                    tail = list(bot_output_lines)[-25:]
                _bot_process = None
                _bot_platform = None
                return jsonify({
                    "error": "Bot exited immediately after start (see output below)",
                    "output": tail,
                }), 500
            return jsonify({"message": f"{platform.title()} bot started", "pid": _bot_process.pid, "platform": platform})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@app.route("/api/bot/preflight", methods=["POST"])
def api_bot_preflight():
    '''Run a fast config/import check (runNaukriBot.py --check) before starting.'''
    data = request.get_json(silent=True) or {}
    platform = data.get("platform", request.args.get("platform", "naukri")).lower()
    if platform not in BOT_SCRIPTS:
        return jsonify({"error": f"Unknown platform: {platform}"}), 400
    try:
        # Same profile sync the real start does, so the check sees the values
        # the bot would actually run with (username etc. live in the profile).
        try:
            sync_active_profile()
        except Exception as sync_err:
            print(f"Profile sync warning: {sync_err}")
        result = subprocess.run(
            [sys.executable, str(BOT_SCRIPTS[platform]), "--check"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            env={**os.environ, "LAUNCHED_FROM_UI": "1", "PYTHONIOENCODING": "utf-8"},
        )
        output = (result.stdout + "\n" + result.stderr).strip()[-2000:]
        return jsonify({"ok": result.returncode == 0, "exit_code": result.returncode, "output": output})
    except subprocess.TimeoutExpired:
        return jsonify({"ok": False, "error": "Preflight check timed out"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route('/api/bot/logs', methods=['GET'])
def api_bot_logs():
    """Return recent bot output lines and status."""
    with bot_output_lock:
        lines = list(bot_output_lines)
    return jsonify({
        'lines': lines,
        'running': _bot_process is not None and _bot_process.poll() is None,
        'exit_code': _bot_process.returncode if _bot_process and _bot_process.poll() is not None else None,
    })

@app.route('/api/bot/logs/clear', methods=['POST'])
def api_bot_clear_logs():
    with bot_output_lock:
        bot_output_lines.clear()
    return jsonify({'message': 'Logs cleared'})


@app.route("/api/bot/stop", methods=["POST"])
def api_bot_stop():
    global _bot_process, _bot_platform
    with _bot_lock:
        if not _bot_running():
            return jsonify({"error": "Bot is not running"}), 404
        try:
            _bot_process.terminate()
            _bot_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _bot_process.kill()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            _bot_process = None
            stopped = _bot_platform
            _bot_platform = None
        return jsonify({"message": f"{stopped} bot stopped"})


def _naukri_search_link(title: str) -> str:
    '''Naukri search URL for a job title — used when the direct job link has
    expired ("Job you are looking for is expired").'''
    from urllib.parse import quote
    clean = (title or "").strip() or "jobs"
    return f"https://www.naukri.com/{quote(clean.replace(' ', '-').lower())}-jobs"


@app.route("/applied-jobs", methods=["GET"])
def get_applied_jobs():
    try:
        jobs = []
        csv_path = PATH / "all_applied_applications_history.csv"
        with open(csv_path, "r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                jobs.append({
                    "Platform": row.get("Platform", "LinkedIn"),
                    "Job_ID": row.get("Job ID", ""),
                    "Title": row.get("Title", ""),
                    "Company": row.get("Company", ""),
                    "Location": row.get("Work Location", ""),
                    "Experience": row.get("Experience required", ""),
                    "HR_Name": row.get("HR Name", "Unknown"),
                    "HR_Link": row.get("HR Link", ""),
                    "Job_Link": row.get("Job Link", ""),
                    "External_Job_link": row.get("External Job link", ""),
                    "Date_Applied": row.get("Date Applied", "Pending"),
                    # Naukri expires job pages after ~30 days; this fallback
                    # URL finds similar live jobs when the direct link is dead.
                    "Search_Link": _naukri_search_link(row.get("Title", "")),
                })
        return jsonify(jobs)
    except FileNotFoundError:
        return jsonify([])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/jobs/failed", methods=["GET"])
def api_failed_jobs():
    '''Failed applications with the reason each one failed (dashboard Job History).'''
    try:
        jobs = []
        csv_path = PATH / "all_failed_applications_history.csv"
        if not csv_path.exists():
            return jsonify([])
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                reason = row.get("Assumed Reason", "")
                # Rows written by old builds logged every *skip* here too;
                # the dashboard shows those under Skipped instead.
                if reason in SKIP_REASONS or row.get("External Job link") == "Skipped":
                    continue
                jobs.append({
                    "Job_ID": row.get("Job ID", ""),
                    "Platform": row.get("Platform", ""),
                    "Title": row.get("Title", ""),
                    "Company": row.get("Company", ""),
                    "Reason": reason,
                    "Detail": row.get("Stack Trace", ""),
                    "Date_Tried": row.get("Date Tried", ""),
                    "Job_Link": row.get("Job Link", ""),
                    "Screenshot": row.get("Screenshot Name", ""),
                })
        jobs.reverse()  # newest first
        return jsonify(jobs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/jobs/skipped", methods=["GET"])
def api_skipped_jobs():
    '''Skipped jobs with the reason each was rejected (dashboard Job History).'''
    try:
        jobs = []
        csv_path = PATH / "all_skipped_jobs_history.csv"
        if not csv_path.exists():
            return jsonify([])
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                jobs.append({
                    "Job_ID": row.get("Job ID", ""),
                    "Platform": row.get("Platform", ""),
                    "Title": row.get("Title", ""),
                    "Company": row.get("Company", ""),
                    "Location": row.get("Location", ""),
                    "Experience": row.get("Experience Required", ""),
                    "Reason": row.get("Reason", ""),
                    "Detail": row.get("Detail", ""),
                    "Search_Term": row.get("Search Term", ""),
                    "Job_Link": row.get("Job Link", ""),
                    "Date_Skipped": row.get("Date Skipped", ""),
                })
        jobs.reverse()  # newest first
        return jsonify(jobs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/jobs/summary", methods=["GET"])
def api_jobs_summary():
    '''Counts of applied / failed / skipped jobs for the history tab badges.'''
    counts = {"applied": 0, "failed": 0, "skipped": 0}
    try:
        with open(PATH / "all_applied_applications_history.csv", "r", encoding="utf-8-sig", newline="") as f:
            counts["applied"] = sum(1 for _ in csv.DictReader(f))
    except Exception:
        pass
    try:
        with open(PATH / "all_failed_applications_history.csv", "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("Assumed Reason") in SKIP_REASONS or row.get("External Job link") == "Skipped":
                    continue
                counts["failed"] += 1
    except Exception:
        pass
    try:
        with open(PATH / "all_skipped_jobs_history.csv", "r", encoding="utf-8-sig", newline="") as f:
            counts["skipped"] = sum(1 for _ in csv.DictReader(f))
    except Exception:
        pass
    return jsonify(counts)


SKIP_REASONS = {
    "Experience too high", "Experience below minimum", "Experience exceeds maximum",
    "Excluded title keyword", "Company blacklisted", "Avoided company",
    "Bad word in JD", "Security clearance required", "Skill mismatch",
}


ACTIVITY_LOG_PATH = PROJECT_ROOT / "logs" / "naukri_activity_log.jsonl"


def _read_activity_log(limit=5000) -> list[dict]:
    entries = []
    if ACTIVITY_LOG_PATH.exists():
        with open(ACTIVITY_LOG_PATH, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip().lstrip("\ufeff")
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries[-limit:]


@app.route("/api/jobs/timeline", methods=["GET"])
def api_jobs_timeline():
    '''Recent activity timeline: what the bot did, job by job, newest first.'''
    try:
        entries = _read_activity_log()
        timeline = []
        for e in entries:
            action = e.get("action", "")
            if action == "SEARCH":
                continue
            timeline.append({
                "time": e.get("timestamp", ""),
                "action": action,
                "job_id": e.get("job_id", ""),
                "title": e.get("title", ""),
                "company": e.get("company", ""),
                "location": e.get("location", ""),
                "status": e.get("status", ""),
                "error": e.get("error", ""),
                "job_link": e.get("job_link", ""),
                "search_term": e.get("search_term", ""),
                "questions_answered": [
                    {"q": qa.get("question", ""), "a": qa.get("answer", "")}
                    for qa in (e.get("questions_answered") or [])
                ],
            })
        timeline.reverse()
        return jsonify({"events": timeline[:300]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/jobs/<path:job_id>/detail", methods=["GET"])
def api_job_detail(job_id):
    '''Full history of one job: every apply attempt, skip, failure and the
    questions that were answered, from the activity log.'''
    try:
        entries = _read_activity_log(limit=20000)
        events = []
        for e in entries:
            if e.get("job_id", "") != job_id:
                continue
            events.append({
                "time": e.get("timestamp", ""),
                "action": e.get("action", ""),
                "status": e.get("status", ""),
                "error": e.get("error", ""),
                "resume_used": e.get("resume_used", ""),
                "search_term": e.get("search_term", ""),
                "search_location": e.get("search_location", ""),
                "questions_answered": [
                    {"q": qa.get("question", ""), "a": qa.get("answer", "")}
                    for qa in (e.get("questions_answered") or [])
                ],
                "description_snippet": e.get("description_snippet", ""),
            })
        if not events:
            return jsonify({"error": "No history found for this job"}), 404
        return jsonify({"job_id": job_id, "events": events})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def api_stats():
    '''Overview numbers for the dashboard header cards.'''
    stats = {
        "applied": 0, "failed": 0, "skipped": 0,
        "applied_today": 0, "failed_today": 0, "skipped_today": 0,
        "last_run": "", "ai_pending_review": 0, "unknown_questions": 0,
    }
    try:
        with open(PATH / "all_applied_applications_history.csv", "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        stats["applied"] = len(rows)
        today = datetime.now().strftime("%Y-%m-%d")
        stats["applied_today"] = sum(1 for r in rows if (r.get("Date Applied") or "").startswith(today))
    except Exception:
        pass
    try:
        with open(PATH / "all_failed_applications_history.csv", "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        genuine = [r for r in rows if r.get("Assumed Reason") not in SKIP_REASONS and r.get("External Job link") != "Skipped"]
        stats["failed"] = len(genuine)
        today = datetime.now().strftime("%Y-%m-%d")
        stats["failed_today"] = sum(1 for r in genuine if (r.get("Date Tried") or "").startswith(today))
    except Exception:
        pass
    try:
        with open(PATH / "all_skipped_jobs_history.csv", "r", encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        stats["skipped"] = len(rows)
        today = datetime.now().strftime("%Y-%m-%d")
        stats["skipped_today"] = sum(1 for r in rows if (r.get("Date Skipped") or "").startswith(today))
    except Exception:
        pass
    try:
        from modules.naukri import ai_answers_log
        answers = ai_answers_log.get_ai_answers()
        stats["ai_pending_review"] = sum(1 for a in answers if a["feedback"] == "pending")
    except Exception:
        pass
    try:
        if UNKNOWN_QUESTIONS_LOG.exists():
            seen = set()
            with open(UNKNOWN_QUESTIONS_LOG, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip().lstrip("\ufeff")
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if e.get("status") != "answered":
                        seen.add((e.get("question") or "").strip())
            stats["unknown_questions"] = len(seen)
    except Exception:
        pass
    return jsonify(stats)


@app.route("/applied-jobs/<job_id>", methods=["PUT"])
def update_applied_date(job_id):
    try:
        data = []
        csv_path = PATH / "all_applied_applications_history.csv"
        if not csv_path.exists():
            return jsonify({"error": f"CSV file not found at {csv_path}"}), 404
        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            field_names = reader.fieldnames
            found = False
            for row in reader:
                if row["Job ID"] == job_id:
                    row["Date Applied"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    found = True
                data.append(row)
        if not found:
            return jsonify({"error": f"Job ID {job_id} not found"}), 404
        with open(csv_path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=field_names)
            writer.writeheader()
            writer.writerows(data)
        return jsonify({"message": "Date Applied updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


UNKNOWN_QUESTIONS_LOG = PROJECT_ROOT / "logs" / "naukri_unknown_questions.jsonl"


@app.route("/api/profiles", methods=["GET"])
def api_list_profiles():
    try:
        result = list_profiles()
        # Auto-migrate: if no profiles exist, create default from current config
        if not result["profiles"]:
            profile = create_default_profile_from_config()
            result = list_profiles()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profiles/<profile_id>", methods=["GET"])
def api_get_profile(profile_id):
    try:
        return jsonify(get_profile(profile_id))
    except FileNotFoundError:
        return jsonify({"error": "Profile not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profiles", methods=["POST"])
def api_create_profile():
    try:
        data = request.get_json(silent=True) or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Profile name is required"}), 400
        profile = create_profile(name, data.get("data"))
        return jsonify(profile), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profiles/<profile_id>", methods=["PUT"])
def api_update_profile(profile_id):
    try:
        data = request.get_json(silent=True) or {}
        profile = update_profile(profile_id, data)
        return jsonify(profile)
    except FileNotFoundError:
        return jsonify({"error": "Profile not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profiles/<profile_id>", methods=["DELETE"])
def api_delete_profile(profile_id):
    try:
        delete_profile(profile_id)
        return jsonify({"message": "Profile deleted"})
    except FileNotFoundError:
        return jsonify({"error": "Profile not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/profiles/<profile_id>/activate", methods=["POST"])
def api_activate_profile(profile_id):
    try:
        activate_profile(profile_id)
        sync_active_profile()
        return jsonify({"message": f"Profile '{profile_id}' activated and synced"})
    except FileNotFoundError:
        return jsonify({"error": "Profile not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/naukri/unknown-questions", methods=["GET"])
def api_naukri_unknown_questions():
    """Read unknown questions log, deduplicate, and mark which are already answered."""
    try:
        # Load existing custom answers for cross-reference
        from modules.config_manager import get_all_config
        cfg = get_all_config()
        custom_answers = cfg.get("sections", {}).get("naukri_questions", {}).get("custom_naukri_answers", {})

        questions = []
        seen = set()
        if UNKNOWN_QUESTIONS_LOG.exists():
            # utf-8-sig strips a possible BOM on the first line, which would
            # otherwise make json.loads fail on that entry.
            with open(UNKNOWN_QUESTIONS_LOG, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip().lstrip("\ufeff")
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    q_text = entry.get("question", "").strip()
                    if not q_text or q_text in seen:
                        continue
                    seen.add(q_text)

                    # Check if any keyword in custom_answers matches this question
                    existing_answer = ""
                    matched_keyword = ""
                    for keyword, ans in custom_answers.items():
                        if keyword.lower() in q_text.lower():
                            existing_answer = str(ans)
                            matched_keyword = keyword
                            break

                    questions.append({
                        "question": q_text,
                        "options": entry.get("options", []),
                        "time": entry.get("time", ""),
                        "existing_answer": entry.get("answer", "") or existing_answer,
                        "matched_keyword": matched_keyword,
                        "status": "answered" if (entry.get("status") == "answered" or existing_answer) else "new",
                    })

        return jsonify({"questions": questions, "total": len(questions),
                         "unanswered": sum(1 for q in questions if q["status"] == "new")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/naukri/answer-questions", methods=["POST"])
def api_naukri_answer_questions():
    """Save user answers for unknown questions.

    The answer is written to the active profile AND the config file — the bot
    start syncs the profile over the config files, so saving only to the config
    meant your answers silently disappeared on the next run (the bug behind
    "saved but still showing pending"). Each JSONL row is also marked answered,
    which is what the Unknown Questions table reads."""
    try:
        data = request.get_json(silent=True) or {}
        new_answers = data.get("answers", {})
        if not new_answers:
            return jsonify({"error": "No answers provided"}), 400

        # Load current custom answers
        from modules.config_manager import _read_module_values, save_config
        current = _read_module_values("config.naukri_questions", ["custom_naukri_answers"])
        custom_answers = current.get("custom_naukri_answers", {})

        # Merge new answers
        custom_answers.update(new_answers)

        # Save to config file (what the bot reads)
        save_config({"naukri_questions": {"custom_naukri_answers": custom_answers}})

        # Save to the active profile (what sync_active_profile restores from)
        profile_saved = False
        try:
            from modules.profile_manager import get_active_profile, update_profile
            active = get_active_profile()
            if active:
                qa = dict(active.get("qa", {}) or {})
                profile_answers = dict(qa.get("custom_naukri_answers", {}) or {})
                profile_answers.update(new_answers)
                qa["custom_naukri_answers"] = profile_answers
                update_profile(active.get("id"), {"qa": qa})
                profile_saved = True
        except Exception as profile_err:
            print(f"Profile answer save warning: {profile_err}")

        # Mark the saved questions as answered in the JSONL the UI reads
        marked = 0
        if UNKNOWN_QUESTIONS_LOG.exists():
            rows = []
            try:
                with open(UNKNOWN_QUESTIONS_LOG, "r", encoding="utf-8-sig") as f:
                    for line in f:
                        line = line.strip().lstrip("\ufeff")
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        q = (entry.get("question") or "").strip()
                        for keyword, ans in new_answers.items():
                            if keyword.lower() in q.lower():
                                entry["status"] = "answered"
                                entry["answer"] = str(ans)
                                marked += 1
                                break
                        rows.append(entry)
                with open(UNKNOWN_QUESTIONS_LOG, "w", encoding="utf-8") as f:
                    for entry in rows:
                        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception as log_err:
                print(f"Unknown-questions log update warning: {log_err}")

        return jsonify({
            "message": f"Saved {len(new_answers)} answer(s)",
            "total_answers": len(custom_answers),
            "profile_saved": profile_saved,
            "questions_marked_answered": marked,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


AI_ANSWERS_SEEDED = False


@app.route("/api/naukri/ai-answers", methods=["GET"])
def api_naukri_ai_answers():
    """AI-answered recruiter questions for review, with your feedback status."""
    global AI_ANSWERS_SEEDED
    try:
        from modules.naukri import ai_answers_log
        if not AI_ANSWERS_SEEDED:
            # Backfill from logs/log.txt once, so the page opens with history.
            seeded = ai_answers_log.seed_from_log_txt(PROJECT_ROOT / "logs" / "log.txt")
            if seeded:
                print(f"Seeded {seeded} AI-answered questions from log.txt")
            AI_ANSWERS_SEEDED = True
        entries = ai_answers_log.get_ai_answers()
        counts = {
            "pending": sum(1 for e in entries if e["feedback"] == "pending"),
            "correct": sum(1 for e in entries if e["feedback"] == "correct"),
            "wrong": sum(1 for e in entries if e["feedback"] == "wrong"),
            "total": len(entries),
        }
        return jsonify({"answers": entries, "counts": counts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/naukri/ai-answers/feedback", methods=["POST"])
def api_naukri_ai_answers_feedback():
    """Mark an AI answer correct or wrong."""
    try:
        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()
        feedback = (data.get("feedback") or "").strip()
        if not question or feedback not in ("correct", "wrong", "pending"):
            return jsonify({"error": "question and feedback (correct|wrong|pending) required"}), 400
        from modules.naukri import ai_answers_log
        changed = ai_answers_log.set_feedback(question, feedback)
        if not changed:
            return jsonify({"error": "Question not found"}), 404
        return jsonify({"message": f'Marked "{question[:50]}" as {feedback}'})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/naukri/ai-answers/teach", methods=["POST"])
def api_naukri_ai_answers_teach():
    """Teach a keyword:answer pair for a question the AI answered wrongly.

    Writes the pair into custom_naukri_answers (profile + config), so the bot
    answers this question itself from now on."""
    try:
        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()
        keyword = (data.get("keyword") or "").strip()
        answer = (data.get("answer") or "").strip()
        if not question or not keyword or not answer:
            return jsonify({"error": "question, keyword and answer are required"}), 400

        from modules.config_manager import _read_module_values, save_config
        current = _read_module_values("config.naukri_questions", ["custom_naukri_answers"])
        custom_answers = current.get("custom_naukri_answers", {})
        custom_answers[keyword] = answer
        save_config({"naukri_questions": {"custom_naukri_answers": custom_answers}})

        # Also into the active profile so sync_active_profile keeps it.
        try:
            from modules.profile_manager import get_active_profile, update_profile
            active = get_active_profile()
            if active:
                qa = dict(active.get("qa", {}) or {})
                profile_answers = dict(qa.get("custom_naukri_answers", {}) or {})
                profile_answers[keyword] = answer
                qa["custom_naukri_answers"] = profile_answers
                update_profile(active.get("id"), {"qa": qa})
        except Exception as profile_err:
            print(f"Profile teach save warning: {profile_err}")

        from modules.naukri import ai_answers_log
        ai_answers_log.set_feedback(question, "wrong")
        ai_answers_log.set_keyword(question, keyword)

        return jsonify({"message": f'Taught "{keyword}" -> "{answer}"; bot will answer this itself from now on'})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
