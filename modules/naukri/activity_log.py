'''
Develop by Rana Rahul

Detailed activity log for Naukri auto-apply — stores every application attempt
with full details for cross-verification.
'''

import json
import os
from datetime import datetime
from pathlib import Path

from config.settings import logs_folder_path
from modules.helpers import print_lg

ACTIVITY_LOG = Path(logs_folder_path) / "naukri_activity_log.jsonl"


def log_activity(
    action: str,
    job_id: str = "",
    title: str = "",
    company: str = "",
    location: str = "",
    experience: str = "",
    job_link: str = "",
    status: str = "",
    apply_type: str = "",
    questions_answered: list | None = None,
    ai_answers: list | None = None,
    resume_used: str = "",
    error: str = "",
    description_snippet: str = "",
    search_term: str = "",
    search_location: str = "",
    extra: dict | None = None,
) -> None:
    '''Append a detailed activity entry to the JSONL log file.'''
    ACTIVITY_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location,
        "experience": experience,
        "job_link": job_link,
        "status": status,
        "apply_type": apply_type,
        "questions_answered": [
            {"question": q, "answer": a, "type": t}
            for q, a, t in (questions_answered or [])
        ],
        "ai_answers": ai_answers or [],
        "resume_used": resume_used,
        "error": error,
        "description_snippet": description_snippet[:300] if description_snippet else "",
        "search_term": search_term,
        "search_location": search_location,
    }
    if extra:
        entry.update(extra)
    
    # Remove empty fields to keep the log clean
    entry = {k: v for k, v in entry.items() if v or v == 0}
    
    try:
        with open(ACTIVITY_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print_lg(f"Failed to write activity log: {e}")


def log_applied(job_id, title, company, location, job_link, questions, resume, description, search_term="", search_location=""):
    '''Log a successfully applied job.'''
    log_activity(
        action="APPLIED",
        job_id=job_id, title=title, company=company, location=location,
        job_link=job_link, status="success", apply_type="naukri",
        questions_answered=list(questions) if questions else [],
        resume_used=resume,
        description_snippet=description,
        search_term=search_term, search_location=search_location,
    )


def log_skipped(job_id, title, company, reason, job_link=""):
    '''Log a skipped job.'''
    log_activity(
        action="SKIPPED",
        job_id=job_id, title=title, company=company,
        job_link=job_link, status="skipped", error=reason,
    )


def log_failed(job_id, title, company, error, job_link=""):
    '''Log a failed application attempt.'''
    log_activity(
        action="FAILED",
        job_id=job_id, title=title, company=company,
        job_link=job_link, status="failed", error=str(error),
    )


def log_search(search_term, search_location, url, results_count):
    '''Log a search attempt.'''
    log_activity(
        action="SEARCH",
        search_term=search_term, search_location=search_location,
        job_link=url, extra={"results_count": results_count},
    )


def log_login(status, method="email"):
    '''Log a login attempt.'''
    log_activity(
        action="LOGIN", status=status,
        extra={"method": method},
    )
