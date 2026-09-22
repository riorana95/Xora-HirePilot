'''
Develop by Rana Rahul

Naukri Auto Job Applier — main entry point.
'''

import argparse
import os
import time

from random import shuffle

from config.questions import default_resume_path
from config.search_naukri import *
from config.secrets import use_AI, ai_provider
from config.settings import *

from modules import open_chrome as chrome
from modules.helpers import print_lg, buffer, critical_error_log
from modules.validator import validate_naukri_config
from modules.jobs_logger import (
    PLATFORM_NAUKRI, get_applied_job_keys, submitted_job, failed_job, screenshot,
)
from modules.naukri.login import login_naukri, is_logged_in_naukri
from modules.naukri.search import (
    navigate_to_search, get_job_listings, go_to_next_page, get_job_description,
    return_to_search_results,
)
from modules.naukri.filters import apply_naukri_filters
from modules.naukri.apply import apply_from_detail_page
from modules.naukri.skip_rules import should_skip_job
from modules.naukri.activity_log import log_applied, log_skipped, log_failed, log_search

if use_AI:
    from modules.ai.openaiConnections import ai_create_openai_client, ai_extract_skills, ai_close_openai_client
    from modules.ai.deepseekConnections import deepseek_create_client, deepseek_extract_skills
    from modules.ai.geminiConnections import gemini_create_client, gemini_extract_skills

applied_count = 0
external_count = 0
failed_count = 0
skip_count = 0
randomly_answered_questions: set = set()
aiClient = None
naukri_tab = None


def _extract_skills(description: str) -> str:
    if not use_AI or not aiClient or description == "Unknown":
        return "Needs AI"
    try:
        if ai_provider == "openai":
            skills = ai_extract_skills(aiClient, description)
        elif ai_provider == "deepseek":
            skills = deepseek_extract_skills(aiClient, description)
        elif ai_provider == "gemini":
            skills = gemini_extract_skills(aiClient, description)
        else:
            return "Needs AI"
        return skills if skills else "Needs AI"
    except Exception as e:
        print_lg("AI skill extraction failed:", e)
        return "Error"


def apply_to_naukri_jobs(search_terms_list: list[str], skip_alerts: bool) -> None:
    global applied_count, external_count, failed_count, skip_count, naukri_tab

    applied_keys = get_applied_job_keys(PLATFORM_NAUKRI)
    blacklisted: set = set()
    terms = list(search_terms_list)
    if randomize_search_order:
        shuffle(terms)

    for term in terms:
        for location in search_locations:
            navigate_to_search(chrome.driver, term, location)
            apply_naukri_filters(chrome.driver)
            results_url = chrome.driver.current_url
            log_search(term, location, chrome.driver.current_url, 0)  # count updated below
            current_count = 0

            while current_count < max_applications_per_search:
                if not is_logged_in_naukri(chrome.driver):
                    print_lg("Naukri session expired. Please log in again.")
                    login_naukri(chrome.driver, skip_alerts)
                    chrome.driver.switch_to.window(naukri_tab)

                listings = get_job_listings(chrome.driver)
                if not listings:
                    print_lg("No job listings found on this page.")
                    break

                for job in listings:
                    if current_count >= max_applications_per_search:
                        break

                    key = (PLATFORM_NAUKRI, job.job_id)
                    if key in applied_keys:
                        print_lg(f'Already applied: "{job.title}" at {job.company}')
                        continue

                    skip, reason, message = should_skip_job(
                        job.company, "", job.experience, blacklisted, title=job.title,
                    )
                    if skip:
                        print_lg(message)
                        failed_job(PLATFORM_NAUKRI, job.job_id, job.job_link, "N/A", "Unknown", reason, message, "Skipped", "N/A")
                        skip_count += 1
                        log_skipped(job.job_id, job.title, job.company, message, job.job_link)
                        continue

                    print_lg(f'\n>>> "{job.title}" | {job.company} | {job.location}')

                    try:
                        chrome.driver.get(job.job_link)
                        buffer(2)
                        description = get_job_description(chrome.driver)

                        skip, reason, message = should_skip_job(
                            job.company, description, job.experience, blacklisted, title=job.title,
                        )
                        if skip:
                            print_lg(message)
                            failed_job(PLATFORM_NAUKRI, job.job_id, job.job_link, "N/A", "Unknown", reason, message, "Skipped", "N/A")
                            skip_count += 1
                            log_skipped(job.job_id, job.title, job.company, message, job.job_link)
                            continue

                        skills = _extract_skills(description)
                        result = apply_from_detail_page(
                            chrome.driver, job.location, description,
                            ai_client=aiClient, ai_provider=ai_provider, use_ai=use_AI,
                            skip_alerts=skip_alerts, randomly_answered=randomly_answered_questions,
                        )

                        date_applied = "Pending"
                        if result.success:
                            date_applied = time.strftime("%Y-%m-%d %H:%M:%S")
                            if result.apply_type == "external":
                                external_count += 1
                            else:
                                applied_count += 1
                            current_count += 1
                            log_applied(job.job_id, job.title, job.company, job.location, job.job_link, result.questions, result.resume, description, term, location)
                        elif result.apply_type in ("already_applied", "external_skipped"):
                            skip_count += 1
                            continue
                        else:
                            failed_count += 1
                            ss = screenshot(chrome.driver, PLATFORM_NAUKRI, job.job_id, "apply_failed")
                            failed_job(PLATFORM_NAUKRI, job.job_id, job.job_link, result.resume, "Unknown",
                                       result.error, result.error, result.application_link, ss)
                            log_failed(job.job_id, job.title, job.company, result.error, job.job_link)
                            continue

                        submitted_job(
                            PLATFORM_NAUKRI, job.job_id, job.title, job.company, job.location, "",
                            description[:500] if description else "", job.experience, skills,
                            "Unknown", "Unknown", result.resume, False, "Unknown",
                            date_applied, job.job_link, result.application_link,
                            result.questions, "N/A",
                        )
                        applied_keys.add(key)

                    except Exception as e:
                        critical_error_log(f"Failed applying to {job.title}", e)
                        failed_count += 1
                        ss = screenshot(chrome.driver, PLATFORM_NAUKRI, job.job_id, "exception")
                        failed_job(PLATFORM_NAUKRI, job.job_id, job.job_link, "N/A", "Unknown",
                                   "Exception", e, "Failed", ss)
                        log_failed(job.job_id, job.title, job.company, str(e), job.job_link)
                    finally:
                        return_to_search_results(chrome.driver, results_url)

                    buffer(click_gap)

                if not go_to_next_page(chrome.driver):
                    break
                buffer(3)


def main() -> None:
    global aiClient, naukri_tab

    parser = argparse.ArgumentParser(description="Naukri Auto Job Applier")
    parser.add_argument("--no-alerts", action="store_true")
    args = parser.parse_args()
    skip_alerts = args.no_alerts or os.environ.get("LAUNCHED_FROM_UI") == "1"

    from config.settings import run_in_background
    if run_in_background:
        skip_alerts = True

    try:
        validate_naukri_config()

        chrome.init_chrome_session()

        if use_AI:
            if ai_provider == "openai":
                aiClient = ai_create_openai_client()
            elif ai_provider == "deepseek":
                aiClient = deepseek_create_client()
            elif ai_provider == "gemini":
                aiClient = gemini_create_client()

        login_naukri(chrome.driver, skip_alerts)
        naukri_tab = chrome.driver.current_window_handle

        apply_to_naukri_jobs(search_terms, skip_alerts)

        while run_non_stop:
            apply_to_naukri_jobs(search_terms, skip_alerts)

    except Exception as e:
        critical_error_log("Naukri Applier Main", e)
        if not skip_alerts:
            print_lg(f"Naukri Bot Error: {str(e)}")
    finally:
        summary = (
            f"Jobs Applied on Naukri: {applied_count}\n"
            f"External links: {external_count}\n"
            f"Failed: {failed_count}\n"
            f"Skipped: {skip_count}\n"
        )
        print_lg(summary)
        if not skip_alerts:
            print_lg(f"Naukri Bot Finished\n{summary}\n\nDevelop by Rana Rahul")
        if use_AI and aiClient:
            try:
                if ai_provider == "openai":
                    ai_close_openai_client(aiClient)
                # Gemini and DeepSeek clients don't need explicit closing
            except Exception:
                pass
        try:
            if chrome.driver:
                chrome.driver.quit()
        except Exception as e:
            print_lg("Browser close error:", e)


if __name__ == "__main__":
    main()
