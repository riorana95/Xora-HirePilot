'''
Develop by Rana Rahul

Auto Job Applier - Configuration Manager
'''

import importlib
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_SECTIONS = {
    "search": {
        "file": "config/search.py",
        "module": "config.search",
        "fields": [
            "search_terms", "search_location", "switch_number", "randomize_search_order",
            "sort_by", "date_posted", "salary", "easy_apply_only",
            "experience_level", "job_type", "on_site", "companies",
            "under_10_applicants", "in_your_network", "fair_chance_employer", "pause_after_filters",
            "about_company_bad_words", "bad_words", "security_clearance", "did_masters", "current_experience",
        ],
    },
    "search_naukri": {
        "file": "config/search_naukri.py",
        "module": "config.search_naukri",
        "fields": [
            "search_terms", "search_locations", "randomize_search_order", "max_applications_per_search",
            "experience_min", "experience_max", "salary_min_lpa", "salary_max_lpa",
            "work_mode", "job_age_days", "apply_on_naukri_only", "pause_after_filters", "run_non_stop",
            "freshness", "filter_locations", "departments", "salary_ranges", "company_types",
            "role_categories", "educations", "posted_by", "industries", "top_companies",
            "about_company_bad_words", "about_company_good_words", "bad_title_words", "bad_words",
            "security_clearance", "did_masters", "current_experience",
        ],
    },
    "naukri_questions": {
        "file": "config/naukri_questions.py",
        "module": "config.naukri_questions",
        "fields": [
            "willing_to_relocate", "default_yes_no_answer", "pause_at_unknown_naukri_question",
            "custom_naukri_answers",
        ],
        "dict_fields": ["custom_naukri_answers"],
    },
    "settings": {
        "file": "config/settings.py",
        "module": "config.settings",
        "fields": [
            "close_tabs", "follow_companies", "run_non_stop", "alternate_sortby",
            "cycle_date_posted", "stop_date_cycle_at_24hr", "click_gap",
            "run_in_background", "disable_extensions", "safe_mode", "stealth_mode",
            "keep_screen_awake", "smooth_scroll", "showAiErrorAlerts",
        ],
    },
    "personals": {
        "file": "config/personals.py",
        "module": "config.personals",
        "fields": [
            "first_name", "middle_name", "last_name", "phone_number", "current_city",
            "street", "state", "zipcode", "country",
            "ethnicity", "gender", "disability_status", "veteran_status",
        ],
    },
    "secrets": {
        "file": "config/secrets.py",
        "module": "config.secrets",
        "fields": [
            "username", "password", "use_AI", "ai_provider",
            "llm_api_url", "llm_api_key", "llm_model", "llm_spec", "stream_output",
        ],
        "sensitive": ["password", "llm_api_key"],
    },
    "questions": {
        "file": "config/questions.py",
        "module": "config.questions",
        "fields": [
            "default_resume_path", "years_of_experience", "require_visa", "website", "linkedIn",
            "us_citizenship", "desired_salary", "current_ctc", "notice_period",
            "linkedin_headline", "linkedin_summary", "cover_letter",
            "recent_employer", "confidence_level",
            "pause_before_submit", "pause_at_failed_question", "overwrite_previous_answers",
        ],
        "multiline": ["linkedin_summary", "cover_letter"],
    },
}

BOOL_FIELDS = {
    "search", "search_naukri", "settings", "questions", "secrets", "naukri_questions",
}

SECTION_BOOL_FIELDS = {
    "search": {
        "randomize_search_order", "easy_apply_only", "under_10_applicants", "in_your_network",
        "fair_chance_employer", "pause_after_filters", "security_clearance", "did_masters",
    },
    "search_naukri": {
        "randomize_search_order", "apply_on_naukri_only", "pause_after_filters", "run_non_stop",
        "security_clearance", "did_masters",
    },
    "settings": {
        "close_tabs", "follow_companies", "run_non_stop", "alternate_sortby", "cycle_date_posted",
        "stop_date_cycle_at_24hr", "run_in_background", "disable_extensions", "safe_mode",
        "stealth_mode", "keep_screen_awake", "smooth_scroll", "showAiErrorAlerts",
    },
    "questions": {
        "pause_before_submit", "pause_at_failed_question", "overwrite_previous_answers",
    },
    "secrets": {"use_AI", "stream_output"},
    "naukri_questions": {"pause_at_unknown_naukri_question"},
}


def _coerce_bool(value: Any) -> bool | Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes", "1"):
            return True
        if low in ("false", "no", "0"):
            return False
    return value


def _normalize_updates(section_name: str, updates: dict[str, Any]) -> dict[str, Any]:
    bool_keys = SECTION_BOOL_FIELDS.get(section_name, set())
    normalized = {}
    for key, value in updates.items():
        if key in bool_keys:
            normalized[key] = _coerce_bool(value)
        else:
            normalized[key] = value
    return normalized


FILTER_OPTIONS = {
    "sort_by": ["", "Most recent", "Most relevant"],
    "date_posted": ["", "Any time", "Past month", "Past week", "Past 24 hours"],
    "salary": ["", "$40,000+", "$60,000+", "$80,000+", "$100,000+", "$120,000+",
               "$140,000+", "$160,000+", "$180,000+", "$200,000+"],
    "experience_level": ["Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"],
    "job_type": ["Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship", "Other"],
    "on_site": ["On-site", "Remote", "Hybrid"],
    "work_mode": ["Remote", "Hybrid", "Office"],
    "ethnicity": ["", "Decline", "Hispanic/Latino", "American Indian or Alaska Native",
                  "Asian", "Black or African American", "Native Hawaiian or Other Pacific Islander",
                  "White", "Other"],
    "gender": ["", "Male", "Female", "Other", "Decline"],
    "disability_status": ["Yes", "No", "Decline"],
    "veteran_status": ["Yes", "No", "Decline"],
    "require_visa": ["Yes", "No"],
    "us_citizenship": [
        "", "U.S. Citizen/Permanent Resident", "Non-citizen allowed to work for any employer",
        "Non-citizen allowed to work for current employer", "Non-citizen seeking work authorization",
        "Canadian Citizen/Permanent Resident", "Other",
    ],
    "ai_provider": ["openai", "deepseek", "gemini"],
}


def _format_python_value(value: Any, multiline: bool = False, as_dict: bool = False) -> str:
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, dict) or as_dict:
        import pprint
        return pprint.pformat(value, width=120, sort_dicts=False)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(int(value) if isinstance(value, float) and value.is_integer() else value)
    if isinstance(value, list):
        return repr(value)
    if isinstance(value, str):
        if multiline or "\n" in value:
            return '"""\n' + value.strip() + '\n"""'
        return repr(value)
    return repr(value)


def _repair_bool_fields(section_name: str, values: dict[str, Any]) -> dict[str, Any]:
    bool_keys = SECTION_BOOL_FIELDS.get(section_name, set())
    repaired = {}
    for key, value in values.items():
        if key in bool_keys and isinstance(value, str) and value.strip().lower() in ("true", "false"):
            repaired[key] = _coerce_bool(value)
        else:
            repaired[key] = value
    return repaired


def _read_module_values(module_name: str, fields: list[str]) -> dict[str, Any]:
    module = importlib.import_module(module_name)
    importlib.reload(module)
    return {field: getattr(module, field) for field in fields}


def repair_bool_fields_on_disk() -> None:
    '''Fix string "true"/"false" bool fields in config files (e.g. after dashboard save bug).'''
    for section_name, section in CONFIG_SECTIONS.items():
        values = _read_module_values(section["module"], section["fields"])
        repaired = _repair_bool_fields(section_name, values)
        bool_keys = SECTION_BOOL_FIELDS.get(section_name, set())
        fixes = {k: repaired[k] for k in bool_keys if isinstance(values.get(k), str) and repaired.get(k) != values.get(k)}
        if fixes:
            file_path = PROJECT_ROOT / section["file"]
            _update_config_file(
                file_path, fixes,
                multiline_fields=section.get("multiline", []),
                dict_fields=section.get("dict_fields", []),
            )


def get_all_config() -> dict[str, Any]:
    repair_bool_fields_on_disk()
    config: dict[str, Any] = {"sections": {}, "options": FILTER_OPTIONS}
    for section_name, section in CONFIG_SECTIONS.items():
        values = _read_module_values(section["module"], section["fields"])
        sensitive = section.get("sensitive", [])
        for key in sensitive:
            if values.get(key):
                values[key + "_set"] = True
                values[key] = ""
        config["sections"][section_name] = values
    return config


def _update_config_file(file_path: Path, updates: dict[str, Any], multiline_fields: list[str] | None = None, dict_fields: list[str] | None = None) -> None:
    multiline_fields = multiline_fields or []
    dict_fields = dict_fields or []
    content = file_path.read_text(encoding="utf-8")
    for key, value in updates.items():
        formatted = _format_python_value(value, multiline=key in multiline_fields, as_dict=key in dict_fields)
        is_multiline = key in multiline_fields or (isinstance(value, str) and "\n" in value)
        is_dict = key in dict_fields or isinstance(value, dict)
        if is_multiline:
            pattern = rf'^{re.escape(key)}\s*=\s*("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|.+)$'
        elif is_dict:
            # Support both pprint's multi-line dictionaries and an empty or
            # one-line dictionary, so a newly learned answer is never lost.
            pattern = rf'^{re.escape(key)}\s*=\s*\{{[\s\S]*?\}}'
        else:
            pattern = rf'^{re.escape(key)}\s*=\s*.+$'
        replacement = f"{key} = {formatted}"
        new_content, count = re.subn(pattern, replacement, content, count=1, flags=re.MULTILINE)
        if count:
            content = new_content
    file_path.write_text(content, encoding="utf-8")


def save_config(section_updates: dict[str, dict[str, Any]]) -> None:
    for section_name, updates in section_updates.items():
        if section_name not in CONFIG_SECTIONS or not updates:
            continue
        section = CONFIG_SECTIONS[section_name]
        file_path = PROJECT_ROOT / section["file"]
        updates = _normalize_updates(section_name, updates)
        if section.get("sensitive"):
            current = _read_module_values(section["module"], section["fields"])
            for key in section["sensitive"]:
                if key in updates and not updates[key] and current.get(key):
                    updates[key] = current[key]
                updates.pop(key + "_set", None)
        _update_config_file(file_path, updates, multiline_fields=section.get("multiline", []), dict_fields=section.get("dict_fields", []))
        importlib.import_module(section["module"])
