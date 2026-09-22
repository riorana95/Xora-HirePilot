'''
Develop by Rana Rahul

Apply Naukri search filters from config/search_naukri.py

Primary filtering is done via URL parameters in search.py::build_search_url().
This module handles secondary sidebar filter clicks for list-based filters
(location, department, company type, etc.) that cannot be encoded in the URL.
'''

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from config.search_naukri import (
    company_types, departments, educations, filter_locations,
    freshness, industries, pause_after_filters, posted_by, role_categories,
    salary_ranges, top_companies, work_mode,
)
from modules.helpers import buffer, print_lg
from modules.naukri.dom_helpers import click_first, find_first
from modules.naukri import selectors as S


def _click_filter_option(driver: WebDriver, filter_label: str, option_text: str, _depth: int = 0) -> bool:
    '''
    Try to click a sidebar filter option by label and option text.
    Uses JS to find the section header and click the matching option.
    Has a max recursion depth of 1 to prevent infinite loops.
    '''
    try:
        clicked = driver.execute_script("""
            const label = arguments[0], option = arguments[1];
            const visible = el => {
                try {
                    const s = getComputedStyle(el), r = el.getBoundingClientRect();
                    return s.display !== 'none' && s.visibility !== 'hidden' && r.width && r.height;
                } catch(e) { return false; }
            };
            const textIs = (el, text) => el.childElementCount === 0 && el.textContent.trim().toLowerCase() === text.toLowerCase();

            // Find the section header — search only specific elements, not all DOM
            const candidates = document.querySelectorAll('span, div, h2, h3, h4, label, p');
            let header = null;
            for (const el of candidates) {
                if (visible(el) && textIs(el, label)) { header = el; break; }
            }
            if (!header) return 'section-not-found';

            // Walk up to find the filter section container
            let section = header.parentElement;
            for (let i = 0; i < 6 && section; i++, section = section.parentElement) {
                if (section.innerText && section.innerText.toLowerCase().includes(option.toLowerCase())) break;
            }
            section = section || header.parentElement;

            // Find the option element
            let candidate = null;
            for (const el of section.querySelectorAll('label, span, div, a')) {
                if (visible(el) && textIs(el, option)) { candidate = el; break; }
            }

            if (!candidate) {
                // Try clicking "View More" to expand the section
                for (const el of section.querySelectorAll('button, a, span, div')) {
                    if (visible(el) && el.textContent.trim().toLowerCase().includes('view more')) {
                        el.click();
                        return 'expanded';
                    }
                }
                return 'option-not-found';
            }

            // Click the checkbox/input or the element itself
            const control = candidate.closest('label')?.querySelector('input') || candidate.parentElement?.querySelector('input') || candidate;
            control.scrollIntoView({ block: 'center' });
            control.click();
            return 'clicked';
        """, filter_label, option_text)

        if clicked == "expanded" and _depth < 1:
            buffer(1)
            return _click_filter_option(driver, filter_label, option_text, _depth + 1)
        if clicked == "clicked":
            buffer(1)
            print_lg(f"Filter applied: {filter_label} -> {option_text}")
            return True
        # Don't log section-not-found for primary URL-param filters
        if clicked != "section-not-found":
            print_lg(f"Filter '{filter_label}' -> '{option_text}': {clicked}")
        return False
    except Exception as e:
        err_msg = str(e).split('\n')[0][:100]  # First line, truncated
        print_lg(f"Filter '{filter_label}' -> '{option_text}' error: {err_msg}")
        return False


def _apply_list_filters(driver: WebDriver) -> None:
    '''Apply list-based sidebar filters that can't be encoded in URL params.'''
    filter_groups = {
        "Location": filter_locations,
        "Department": departments,
        "Salary": salary_ranges,
        "Company type": company_types,
        "Role category": role_categories,
        "Education": educations,
        "Posted by": posted_by,
        "Industry": industries,
        "Top companies": top_companies,
    }
    for label, options in filter_groups.items():
        for option in options:
            _click_filter_option(driver, label, option)


def apply_naukri_filters(driver: WebDriver) -> None:
    '''
    Apply Naukri filters. Primary filters (experience, salary, freshness,
    work mode) are already encoded in the URL by build_search_url().
    This function only applies list-based sidebar filters.
    '''
    print_lg("Filters: experience, salary, freshness, work mode handled via URL params.")

    # Only apply list-based sidebar filters if any are configured
    has_list_filters = any([
        filter_locations, departments, salary_ranges, company_types,
        role_categories, educations, posted_by, industries, top_companies,
    ])

    if has_list_filters:
        print_lg("Applying sidebar list filters...")
        buffer(2)
        _apply_list_filters(driver)
        buffer(1)
    else:
        print_lg("No additional sidebar filters configured.")

    if pause_after_filters:
        from modules.helpers import is_headless
        if not is_headless():
            import pyautogui
            pyautogui.alert(
                "Naukri filters applied.\n\nReview the search results and adjust if needed, then click OK to continue.",
                "Pause After Filters",
                "OK",
            )
        else:
            print_lg("Filters applied (pause_after_filters skipped in headless mode).")
