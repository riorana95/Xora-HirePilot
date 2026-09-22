'''
Develop by Rana Rahul

Naukri search URL building, navigation, and job listing parsing.
'''

import re
from dataclasses import dataclass
from urllib.parse import quote_plus

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver

from config.search_naukri import search_locations
from modules.helpers import buffer, print_lg
from modules.naukri.dom_helpers import find_all, find_child_attr, find_child_text, find_first, click_first
from modules.naukri import selectors as S


@dataclass
class NaukriJobListing:
    job_id: str
    title: str
    company: str
    location: str
    experience: str
    salary: str
    job_link: str
    card_element: object = None


def build_search_url(keyword: str, location: str) -> str:
    '''Build Naukri search URL with filters encoded as query parameters.'''
    from config.search_naukri import (
        experience_min, experience_max, salary_min_lpa, salary_max_lpa,
        job_age_days, work_mode,
    )
    kw = quote_plus(keyword.strip())
    params = [f"k={kw}"]
    
    loc = location.strip()
    if loc:
        loc_slug = loc.lower().replace(" ", "-")
        params.append(f"l={quote_plus(loc)}")
        base_path = f"{S.SEARCH_BASE}/{kw}-jobs-in-{loc_slug}"
    else:
        base_path = f"{S.SEARCH_BASE}/{kw}-jobs"
    
    # Experience filter (most reliable via URL)
    if experience_min >= 0 and experience_max >= 0:
        params.append(f"experience={experience_min}")
        params.append(f"nignbelow_experience={experience_max}")
    elif experience_min >= 0:
        params.append(f"experience={experience_min}")
    elif experience_max >= 0:
        params.append(f"nignbelow_experience={experience_max}")
    
    # Salary filter (in lakhs)
    if salary_min_lpa > 0:
        params.append(f"salary={salary_min_lpa}")
    if salary_max_lpa > 0:
        params.append(f"nignbelow_salary={salary_max_lpa}")
    
    # Freshness/job age filter
    if job_age_days > 0:
        params.append(f"jobAge={job_age_days}")
    
    # Work mode filter
    wfh_codes = []
    for mode in work_mode:
        mode_lower = mode.lower()
        if mode_lower in ('remote', 'wfh', 'work from home'):
            wfh_codes.append('1')  # Remote/WFH
        elif mode_lower == 'hybrid':
            wfh_codes.append('2')  # Hybrid
    if wfh_codes:
        params.append(f"wfhType={'%2C'.join(wfh_codes)}")
    
    return f"{base_path}?{'&'.join(params)}"


def navigate_to_search(driver: WebDriver, keyword: str, location: str) -> None:
    url = build_search_url(keyword, location)
    print_lg(f'Navigating to Naukri search: "{keyword}" in "{location}"')
    print_lg(url)
    driver.get(url)
    buffer(3)


def _extract_job_id(link: str) -> str:
    if not link:
        return ""
    match = re.search(r"job-listings-(\d+)", link)
    if match:
        return match.group(1)
    match = re.search(r"/(\d{6,})", link)
    if match:
        return match.group(1)
    return link.split("?")[0].rstrip("/").split("/")[-1] or link


def get_job_listings(driver: WebDriver) -> list[NaukriJobListing]:
    cards = find_all(driver, S.JOB_CARD)
    listings: list[NaukriJobListing] = []
    seen_ids: set[str] = set()

    for card in cards:
        try:
            link = find_child_attr(card, S.JOB_LINK, "href", "")
            job_id = _extract_job_id(link)
            if not job_id or job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            title = find_child_text(card, S.JOB_TITLE)
            company = find_child_text(card, S.JOB_COMPANY)
            location = find_child_text(card, S.JOB_LOCATION)
            experience = find_child_text(card, S.JOB_EXPERIENCE, "")
            salary = find_child_text(card, S.JOB_SALARY, "")
            if not link.startswith("http"):
                link = S.SEARCH_BASE + link if link.startswith("/") else link
            listings.append(NaukriJobListing(
                job_id=job_id,
                title=title,
                company=company,
                location=location,
                experience=experience,
                salary=salary,
                job_link=link,
                card_element=card,
            ))
        except Exception as e:
            print_lg(f"Failed to parse job card: {e}")
            
    if not listings:
        print_lg(f"No job cards found. Page title: {driver.title}")
        print_lg(f"Current URL: {driver.current_url}")
        # Save page source for debugging
        try:
            debug_path = f"logs/debug_page_{int(__import__('time').time())}.html"
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print_lg(f"Page source saved to {debug_path} for debugging.")
        except Exception as e:
            print_lg(f"Could not save debug page: {e}")

    return listings


def go_to_next_page(driver: WebDriver) -> bool:
    return click_first(driver, S.NEXT_PAGE, timeout=3)


def return_to_search_results(driver: WebDriver, fallback_url: str) -> None:
    '''Return to the already-filtered results page after handling one job.'''
    try:
        driver.back()
        buffer(2)
        if find_all(driver, S.JOB_CARD):
            return
    except Exception as e:
        print_lg(f"Browser back to results failed: {e}")

    # Some Apply flows replace the history entry. The filter state is normally
    # encoded in this URL, so it is the safest fallback.
    driver.get(fallback_url)
    buffer(3)


def get_job_description(driver: WebDriver) -> str:
    el = find_first(driver, S.JOB_DESCRIPTION, timeout=5)
    if el:
        return el.text.strip()
    return "Unknown"
