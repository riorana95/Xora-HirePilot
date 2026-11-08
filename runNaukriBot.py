'''
Develop by Rana Rahul

Naukri Auto Job Applier — main entry point.
'''

import argparse
import os
import sys
import time

from random import shuffle

from config.questions import default_resume_path
from config.search_naukri import *
from config.secrets import use_AI, ai_provider, llm_api_key
from config.settings import *


def _run_check_mode() -> bool:
    '''Preflight: validate config + import the browser-dependent modules.

    Returns True if --check was requested (caller should exit). A config error
    or missing dependency is reported to stdout with a non-zero exit code, so
    the dashboard's Start button can show WHY nothing happened instead of
    silently spawning a process that dies.'''
    if "--check" not in sys.argv:
        return False
    print("Checking configuration...")
    try:
        from modules.validator import validate_naukri_config
        validate_naukri_config()
    except Exception as e:
        print(f"CONFIG ERROR: {e}")
        sys.exit(2)
    try:
        from modules import open_chrome as chrome  # noqa: F401
        from modules.naukri.login import login_naukri  # noqa: F401
        from modules.naukri.search import navigate_to_search  # noqa: F401
        from modules.naukri.apply import apply_from_detail_page  # noqa: F401
        from modules.naukri.skip_rules import should_skip_job  # noqa: F401
        from modules.jobs_logger import get_applied_job_keys, get_failed_job_counts  # noqa: F401
        if use_AI:
            if ai_provider == "openai":
                from modules.ai.openaiConnections import ai_create_openai_client  # noqa: F401
            elif ai_provider == "deepseek":
                from modules.ai.deepseekConnections import deepseek_create_client  # noqa: F401
            elif ai_provider == "gemini":
                from modules.ai.geminiConnections import gemini_create_client  # noqa: F401
    except Exception as e:
        print(f"IMPORT ERROR: {type(e).__name__}: {e}")
        print("Tip: pip install -r requirements.txt")
        sys.exit(3)
    _sanity_warnings_quiet()
    print("CHECK OK: config valid, all modules import cleanly.")
    print(f"  search_terms={search_terms} locations={search_locations}")
    print(f"  experience {experience_min}-{experience_max}, current={current_experience}, "
          f"retry_limit={failed_job_retry_limit}, gap={nonstop_cycle_gap_minutes}m")
    if required_skills:
        print(f"  skill filter: watching {required_skills}")
    sys.exit(0)


def _sanity_warnings_quiet() -> None:
    if current_experience == 0:
        print("WARNING: current_experience is 0 - every job requiring any experience will be skipped!")
    if experience_min >= 0 and current_experience >= 0 and experience_min > current_experience:
        print(f"WARNING: experience_min ({experience_min}) > current_experience ({current_experience}).")
    if use_AI and ai_provider == "gemini" and not llm_api_key:
        print("WARNING: use_AI is True but llm_api_key is empty; AI steps will fail.")


_run_check_mode()

from modules import open_chrome as chrome
from modules.helpers import print_lg, buffer, critical_error_log
from modules.validator import validate_naukri_config
from modules.jobs_logger import (
    PLATFORM_NAUKRI, get_applied_job_keys, get_failed_job_counts, submitted_job,
    failed_job, skipped_job, screenshot,
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
_logged_skips: set = set()


def log_skipped_once(job_id: str, reason: str, message: str, job, search_term: str = "") -> None:
    '''Log a skip once per run, both to the activity log and the persistent
    skipped-jobs CSV (title/company/reason/detail), so you can always look up
    why any job was never applied to.'''
    if job_id in _logged_skips:
        return
    _logged_skips.add(job_id)
    log_skipped(job_id, job.title, job.company, f"{reason}: {message}", job.job_link)
    skipped_job(
        PLATFORM_NAUKRI, job_id, job.title, job.company, job.location,
        job.experience, search_term, reason, message, job.job_link,
    )


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
    # Count past failures per job so hopeless jobs are not retried forever
    # (one job in the old logs had been retried 73 times, each time costing a
    # page load, a Gemini call and a screenshot).
    failed_counts = get_failed_job_counts(PLATFORM_NAUKRI)
    session_failed_counts: dict[str, int] = {}
    blacklisted: set = set()
    terms = list(search_terms_list)
    if randomize_search_order:
        shuffle(terms)

    cycle_start = {"applied": applied_count, "external": external_count,
                   "failed": failed_count, "skipped": skip_count}
    given_up = 0

    for term in terms:
        for location in search_locations:
            navigate_to_search(chrome.driver, term, location)
            apply_naukri_filters(chrome.driver)
            results_url = chrome.driver.current_url
            log_search(term, location, chrome.driver.current_url, 0)  # count updated below
            current_count = 0
            seen_page_hashes: set = set()

            while current_count < max_applications_per_search:
                if not is_logged_in_naukri(chrome.driver):
                    print_lg("Naukri session expired. Please log in again.")
                    login_naukri(chrome.driver, skip_alerts)
                    chrome.driver.switch_to.window(naukri_tab)

                listings = get_job_listings(chrome.driver)
                if not listings:
                    print_lg("No job listings found on this page.")
                    break

                # Loop guard: if pagination stopped advancing (same job IDs in
                # the same order), stop instead of re-scanning this page forever.
                page_hash = hash(tuple(job.job_id for job in listings))
                if page_hash in seen_page_hashes:
                    print_lg("Pagination did not advance to a new page; stopping this search.")
                    break
                seen_page_hashes.add(page_hash)

                for job in listings:
                    if current_count >= max_applications_per_search:
                        break

                    # Retry cap: give up once the historical + this-session
                    # failures exceed the configured limit.
                    total_failures = failed_counts.get(job.job_id, 0) + session_failed_counts.get(job.job_id, 0)
                    if failed_job_retry_limit > 0 and total_failures >= failed_job_retry_limit:
                        given_up += 1
                        print_lg(f'[GAVE UP] "{job.title}" at {job.company}: {total_failures} failed attempts (retry limit {failed_job_retry_limit}).')
                        continue

                    key = (PLATFORM_NAUKRI, job.job_id)
                    if key in applied_keys:
                        print_lg(f'[ALREADY APPLIED] "{job.title}" at {job.company}')
                        continue

                    skip, reason, message = should_skip_job(
                        job.company, "", job.experience, blacklisted, title=job.title,
                    )
                    if skip:
                        skip_count += 1
                        print_lg(f'[SKIPPED] "{job.title}" at {job.company} | {reason}: {message}')
                        log_skipped_once(job.job_id, reason, message, job, term)
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
                            skip_count += 1
                            print_lg(f'[SKIPPED] "{job.title}" at {job.company} | {reason}: {message}')
                            log_skipped_once(job.job_id, reason, message, job, term)
                            continue

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
                                print_lg(f'[APPLIED - EXTERNAL SITE] "{job.title}" at {job.company}')
                            else:
                                applied_count += 1
                                print_lg(f'[APPLIED] "{job.title}" at {job.company}')
                            current_count += 1
                            # Skill extraction is only needed for the success
                            # row; doing it before the apply wasted a Gemini
                            # call on every job that then failed or was skipped.
                            skills = _extract_skills(description)
                            log_applied(job.job_id, job.title, job.company, job.location, job.job_link, result.questions, result.resume, description, term, location)
                        elif result.apply_type == "already_applied":
                            applied_keys.add(key)
                            skip_count += 1
                            print_lg(f'[ALREADY APPLIED] "{job.title}" at {job.company}')
                            continue
                        elif result.apply_type == "external_skipped":
                            applied_keys.add(key)
                            skip_count += 1
                            print_lg(f'[SKIPPED - EXTERNAL APPLY] "{job.title}" at {job.company} (apply_on_naukri_only = True)')
                            log_skipped_once(job.job_id, "External apply skipped",
                                              "Apply goes to the company site; apply_on_naukri_only = True",
                                              job, term)
                            continue
                        else:
                            failed_count += 1
                            session_failed_counts[job.job_id] = session_failed_counts.get(job.job_id, 0) + 1
                            print_lg(f'[FAILED] "{job.title}" at {job.company} | {result.error}')
                            ss = screenshot(chrome.driver, PLATFORM_NAUKRI, job.job_id, "apply_failed")
                            failed_job(PLATFORM_NAUKRI, job.job_id, job.job_link, result.resume, "Unknown",
                                       result.error, result.error, result.application_link, ss,
                                       title=job.title, company=job.company)
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
                        session_failed_counts[job.job_id] = session_failed_counts.get(job.job_id, 0) + 1
                        print_lg(f'[FAILED] "{job.title}" at {job.company} | Exception: {e}')
                        ss = screenshot(chrome.driver, PLATFORM_NAUKRI, job.job_id, "exception")
                        failed_job(PLATFORM_NAUKRI, job.job_id, job.job_link, "N/A", "Unknown",
                                   "Exception", e, "Failed", ss,
                                   title=job.title, company=job.company)
                        log_failed(job.job_id, job.title, job.company, str(e), job.job_link)
                    finally:
                        return_to_search_results(chrome.driver, results_url)

                    buffer(click_gap)

                if not go_to_next_page(chrome.driver):
                    break
                buffer(3)

    print_lg(
        '--- CYCLE SUMMARY --- '
        f'applied this run: {applied_count - cycle_start["applied"]}, '
        f'external: {external_count - cycle_start["external"]}, '
        f'failed: {failed_count - cycle_start["failed"]}, '
        f'skipped: {skip_count - cycle_start["skipped"]}, '
        f'gave up (retry cap): {given_up}'
    )


def _sanity_warnings() -> None:
    '''Cheap checks that catch silent misconfiguration before hours of runs.

    The shipped logs contained 5,077 "Experience too high" skips caused by
    current_experience having been saved as 0 by an empty dashboard field.'''
    if current_experience == 0:
        print_lg(
            'WARNING: current_experience is 0, so every job requiring any '
            'experience is skipped. If this is wrong, fix '
            'config/search_naukri.py (or the dashboard field) and restart.'
        )
    if experience_min >= 0 and current_experience >= 0 and experience_min > current_experience:
        print_lg(
            f'WARNING: experience_min ({experience_min}) is above your current '
            f'experience ({current_experience}); the bot will keep rejecting '
            'jobs you could actually get.'
        )
    if use_AI and ai_provider == 'gemini' and not llm_api_key:
        print_lg('WARNING: use_AI is True but llm_api_key is empty; AI steps will fail.')


def main() -> None:
    global aiClient, naukri_tab

    parser = argparse.ArgumentParser(description="Naukri Auto Job Applier")
    parser.add_argument("--no-alerts", action="store_true")
    parser.add_argument("--check", action="store_true",
                        help="Validate config and imports, print a report, exit (no browser).")
    args = parser.parse_args()
    skip_alerts = args.no_alerts or os.environ.get("LAUNCHED_FROM_UI") == "1"

    from config.settings import run_in_background
    if run_in_background:
        skip_alerts = True

    try:
        validate_naukri_config()
        _sanity_warnings()

        print_lg("=== NAUKRI BOT STARTING ===")
        print_lg(f"Search terms: {search_terms} | Locations: {search_locations}")
        print_lg(f"Experience {experience_min}-{experience_max} yrs (current {current_experience}) | "
                 f"AI={use_AI} provider={ai_provider} | retry limit={failed_job_retry_limit} | "
                 f"non-stop={run_non_stop}" + (f" (gap {nonstop_cycle_gap_minutes}m)" if run_non_stop else ""))
        if required_skills:
            print_lg(f"Skill filter on: watching {required_skills}; possessed: {possessed_skills}")

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
            gap_minutes = max(0, nonstop_cycle_gap_minutes)
            if gap_minutes:
                print_lg(f'Non-stop mode: waiting {gap_minutes} minute(s) before the next cycle...')
                time.sleep(gap_minutes * 60)
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
