'''
Develop by Rana Rahul

Skip-rule checks for Naukri jobs.
'''

import re

from config.search_naukri import (
    about_company_bad_words, about_company_good_words, bad_title_words, bad_words,
    current_experience, did_masters, experience_max, experience_min, security_clearance,
)

re_experience = re.compile(r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)", re.IGNORECASE)
re_experience_minimum = re.compile(r"(\d+)\s*\+?\s*(?:years?|yrs?)", re.IGNORECASE)


def extract_experience_range(text: str) -> tuple[int | str, int | None]:
    if not text:
        return "Unknown", None
    match = re_experience.search(text)
    if match:
        return int(match.group(1)), int(match.group(2))
    match = re_experience_minimum.search(text)
    if match:
        return int(match.group(1)), None
    return "Unknown", None


def extract_min_experience(text: str) -> int | str:
    if not text:
        return "Unknown"
    minimum, _ = extract_experience_range(text)
    if isinstance(minimum, int):
        return minimum
    nums = re.findall(r"(\d+)\+", text)
    if nums:
        return int(nums[0])
    return "Unknown"


def should_skip_job(
    company: str,
    description: str,
    experience_text: str,
    blacklisted_companies: set,
    title: str = "",
) -> tuple[bool, str, str]:
    company_lower = company.lower()
    desc_lower = description.lower()
    title_lower = title.lower()

    for bad in bad_title_words:
        if bad.lower() in title_lower:
            return True, "Excluded title keyword", f'Excluded title keyword "{bad}" in "{title}"'

    exp_required, exp_upper = extract_experience_range(experience_text or description)
    # The website's filter widget is unreliable, so enforce the configured
    # range from the job card before the bot opens or applies to a listing.
    if isinstance(exp_required, int):
        if experience_max >= 0 and exp_required > experience_max:
            return True, "Experience exceeds maximum", f"Requires {experience_text}; maximum is {experience_max} years"
        if experience_min >= 0 and exp_upper is not None and exp_upper < experience_min:
            return True, "Experience below minimum", f"Requires {experience_text}; minimum is {experience_min} years"

    for bad in about_company_bad_words:
        if bad.lower() in company_lower:
            if not any(g.lower() in company_lower for g in about_company_good_words):
                blacklisted_companies.add(company)
                return True, "Company blacklisted", f'Bad word "{bad}" in company name'

    for bad in bad_words:
        if bad.lower() in desc_lower:
            return True, "Bad word in JD", f'Bad word "{bad}" in job description'

    if security_clearance is False and any(w in desc_lower for w in ["security clearance", "clearance required", "secret clearance"]):
        return True, "Security clearance required", "Job requires security clearance"

    exp_required = extract_min_experience(experience_text or description)
    found_masters = 0
    if did_masters and "master" in desc_lower:
        found_masters = 2

    if current_experience > -1 and isinstance(exp_required, int):
        if exp_required > current_experience + found_masters:
            return True, "Experience too high", f"Required {exp_required} > current {current_experience + found_masters}"

    return False, "", ""
