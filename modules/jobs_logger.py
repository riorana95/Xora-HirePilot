'''
Develop by Rana Rahul

Shared CSV logging for LinkedIn and Naukri job applications.
'''

import csv
import os
from datetime import datetime
from typing import Literal

from config.settings import file_name, failed_file_name, logs_folder_path
from modules.helpers import make_directories, print_lg, truncate_for_csv

PLATFORM_LINKEDIN = "LinkedIn"
PLATFORM_NAUKRI = "Naukri"

SUCCESS_FIELDS = [
    "Job ID", "Platform", "Title", "Company", "Work Location", "Work Style",
    "About Job", "Experience required", "Skills required", "HR Name", "HR Link",
    "Resume", "Re-posted", "Date Posted", "Date Applied", "Job Link",
    "External Job link", "Questions Found", "Connect Request",
]

FAILED_FIELDS = [
    "Job ID", "Platform", "Job Link", "Resume Tried", "Date listed", "Date Tried",
    "Assumed Reason", "Stack Trace", "External Job link", "Screenshot Name",
]


def _ensure_success_header() -> None:
    make_directories([file_name])
    if not os.path.exists(file_name):
        return
    with open(file_name, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return
        if "Platform" in header:
            return
        rows = list(reader)
    old_fields = header
    new_header = SUCCESS_FIELDS
    migrated = []
    for row in rows:
        d = dict(zip(old_fields, row))
        d["Platform"] = PLATFORM_LINKEDIN
        migrated.append({k: d.get(k, "") for k in new_header})
    with open(file_name, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_header)
        writer.writeheader()
        writer.writerows(migrated)


def _ensure_failed_header() -> None:
    make_directories([failed_file_name])
    if not os.path.exists(failed_file_name):
        return
    with open(failed_file_name, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return
        if "Platform" in header:
            return
        rows = list(reader)
    old_fields = header
    new_header = FAILED_FIELDS
    migrated = []
    for row in rows:
        d = dict(zip(old_fields, row))
        d["Platform"] = PLATFORM_LINKEDIN
        migrated.append({k: d.get(k, "") for k in new_header})
    with open(failed_file_name, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=new_header)
        writer.writeheader()
        writer.writerows(migrated)


def get_applied_job_keys(platform: str | None = None) -> set[tuple[str, str]]:
    _ensure_success_header()
    keys: set[tuple[str, str]] = set()
    try:
        with open(file_name, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                job_id = row.get("Job ID", "")
                plat = row.get("Platform", PLATFORM_LINKEDIN)
                if not job_id:
                    continue
                if platform is None or plat == platform:
                    keys.add((plat, job_id))
    except FileNotFoundError:
        print_lg(f"The CSV file '{file_name}' does not exist.")
    return keys


def get_applied_job_ids(platform: str | None = None) -> set[str]:
    return {job_id for plat, job_id in get_applied_job_keys(platform) if platform is None or plat == platform}


def submitted_job(
    platform: str,
    job_id: str,
    title: str,
    company: str,
    work_location: str,
    work_style: str,
    description: str,
    experience_required,
    skills,
    hr_name: str,
    hr_link: str,
    resume: str,
    reposted: bool,
    date_listed,
    date_applied,
    job_link: str,
    application_link: str,
    questions_list,
    connect_request: str = "N/A",
) -> None:
    _ensure_success_header()
    try:
        with open(file_name, mode="a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=SUCCESS_FIELDS)
            if csv_file.tell() == 0:
                writer.writeheader()
            writer.writerow({
                "Job ID": truncate_for_csv(job_id),
                "Platform": truncate_for_csv(platform),
                "Title": truncate_for_csv(title),
                "Company": truncate_for_csv(company),
                "Work Location": truncate_for_csv(work_location),
                "Work Style": truncate_for_csv(work_style),
                "About Job": truncate_for_csv(description),
                "Experience required": truncate_for_csv(experience_required),
                "Skills required": truncate_for_csv(skills),
                "HR Name": truncate_for_csv(hr_name),
                "HR Link": truncate_for_csv(hr_link),
                "Resume": truncate_for_csv(resume),
                "Re-posted": truncate_for_csv(reposted),
                "Date Posted": truncate_for_csv(date_listed),
                "Date Applied": truncate_for_csv(date_applied),
                "Job Link": truncate_for_csv(job_link),
                "External Job link": truncate_for_csv(application_link),
                "Questions Found": truncate_for_csv(questions_list),
                "Connect Request": truncate_for_csv(connect_request),
            })
    except Exception as e:
        print_lg("Failed to update submitted jobs list!", e)


def failed_job(
    platform: str,
    job_id: str,
    job_link: str,
    resume: str,
    date_listed,
    error: str,
    exception,
    application_link: str,
    screenshot_name: str,
) -> None:
    _ensure_failed_header()
    try:
        with open(failed_file_name, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FAILED_FIELDS)
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow({
                "Job ID": truncate_for_csv(job_id),
                "Platform": truncate_for_csv(platform),
                "Job Link": truncate_for_csv(job_link),
                "Resume Tried": truncate_for_csv(resume),
                "Date listed": truncate_for_csv(date_listed),
                "Date Tried": datetime.now(),
                "Assumed Reason": truncate_for_csv(error),
                "Stack Trace": truncate_for_csv(exception),
                "External Job link": truncate_for_csv(application_link),
                "Screenshot Name": truncate_for_csv(screenshot_name),
            })
    except Exception as e:
        print_lg("Failed to update failed jobs list!", e)


def screenshot(driver, platform: str, job_id: str, failed_at: str) -> str:
    folder = f"{logs_folder_path}/screenshots/{platform.lower()}"
    make_directories([folder])
    screenshot_name = f"{job_id} - {failed_at} - {datetime.now()}.png"
    path = os.path.join(folder, screenshot_name.replace(":", "."))
    driver.save_screenshot(path.replace("//", "/"))
    return screenshot_name
