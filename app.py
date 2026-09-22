'''
Develop by Rana Rahul

Auto Job Applier - Web Dashboard
'''

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

from modules.config_manager import get_all_config, save_config

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
            script = BOT_SCRIPTS[platform]
            _bot_process = subprocess.Popen(
                [sys.executable, str(script), "--no-alerts"],
                cwd=str(PROJECT_ROOT),
                env=env,
            )
            _bot_platform = platform
            return jsonify({"message": f"{platform.title()} bot started", "pid": _bot_process.pid, "platform": platform})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


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


@app.route("/applied-jobs", methods=["GET"])
def get_applied_jobs():
    try:
        jobs = []
        csv_path = PATH / "all_applied_applications_history.csv"
        with open(csv_path, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                jobs.append({
                    "Platform": row.get("Platform", "LinkedIn"),
                    "Job_ID": row["Job ID"],
                    "Title": row["Title"],
                    "Company": row["Company"],
                    "HR_Name": row.get("HR Name", "Unknown"),
                    "HR_Link": row.get("HR Link", ""),
                    "Job_Link": row["Job Link"],
                    "External_Job_link": row.get("External Job link", ""),
                    "Date_Applied": row.get("Date Applied", "Pending"),
                })
        return jsonify(jobs)
    except FileNotFoundError:
        return jsonify({"error": "No applications history found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
            with open(UNKNOWN_QUESTIONS_LOG, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
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
                        "existing_answer": existing_answer,
                        "matched_keyword": matched_keyword,
                        "status": "answered" if existing_answer else "new",
                    })

        return jsonify({"questions": questions, "total": len(questions),
                         "unanswered": sum(1 for q in questions if q["status"] == "new")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/naukri/answer-questions", methods=["POST"])
def api_naukri_answer_questions():
    """Save user answers for unknown questions into custom_naukri_answers."""
    try:
        data = request.get_json(silent=True) or {}
        new_answers = data.get("answers", {})
        if not new_answers:
            return jsonify({"error": "No answers provided"}), 400

        # Load current custom answers
        from modules.config_manager import _read_module_values
        current = _read_module_values("config.naukri_questions", ["custom_naukri_answers"])
        custom_answers = current.get("custom_naukri_answers", {})

        # Merge new answers
        custom_answers.update(new_answers)

        # Save via config manager
        save_config({"naukri_questions": {"custom_naukri_answers": custom_answers}})

        return jsonify({"message": f"Saved {len(new_answers)} answer(s)", "total_answers": len(custom_answers)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
