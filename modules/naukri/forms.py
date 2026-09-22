'''
Develop by Rana Rahul

Fill Naukri application questionnaires using config + optional AI.
'''

import os
import re
from random import randint

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from config.questions import *
from config.personals import *
from modules.helpers import buffer, print_lg
from modules.naukri.dom_helpers import find_first
from modules.naukri import selectors as S

re_experience = re.compile(r"(\d+)\s*[-to]*\s*\d*\s*year", re.IGNORECASE)


def _salary_variants():
    desired_salary_lakhs = str(round(desired_salary / 100000, 2))
    desired_salary_monthly = str(round(desired_salary / 12, 2))
    current_ctc_lakhs = str(round(current_ctc / 100000, 2))
    current_ctc_monthly = str(round(current_ctc / 12, 2))
    notice_period_months = str(notice_period // 30)
    notice_period_weeks = str(notice_period // 7)
    return {
        "desired": str(desired_salary),
        "desired_lakhs": desired_salary_lakhs,
        "desired_monthly": desired_salary_monthly,
        "current": str(current_ctc),
        "current_lakhs": current_ctc_lakhs,
        "current_monthly": current_ctc_monthly,
        "notice": str(notice_period),
        "notice_months": notice_period_months,
        "notice_weeks": notice_period_weeks,
    }


def _full_name() -> str:
    fn = first_name.strip()
    mn = middle_name.strip()
    ln = last_name.strip()
    return f"{fn} {mn} {ln}".strip() if mn else f"{fn} {ln}".strip()


def answer_for_label(label: str, work_location: str = "") -> str:
    label = label.lower()
    sal = _salary_variants()
    if "experience" in label or "years" in label:
        return years_of_experience
    if "phone" in label or "mobile" in label:
        return phone_number
    if "email" in label:
        return ""
    if "notice" in label:
        if "month" in label:
            return sal["notice_months"]
        if "week" in label:
            return sal["notice_weeks"]
        return sal["notice"]
    if "salary" in label or "ctc" in label or "compensation" in label or "lpa" in label:
        if "current" in label or "present" in label:
            if "month" in label:
                return sal["current_monthly"]
            if "lakh" in label or "lpa" in label:
                return sal["current_lakhs"]
            return sal["current"]
        if "month" in label:
            return sal["desired_monthly"]
        if "lakh" in label or "lpa" in label:
            return sal["desired_lakhs"]
        return sal["desired"]
    if "visa" in label or "sponsor" in label:
        return require_visa
    if "gender" in label:
        return gender
    if "disability" in label:
        return disability_status
    if "veteran" in label:
        return veteran_status
    if "city" in label or "location" in label:
        return current_city or work_location
    if "state" in label:
        return state
    if "country" in label:
        return country
    if "street" in label or "address" in label:
        return street
    if "headline" in label:
        return linkedin_headline
    if "summary" in label or "about" in label:
        return linkedin_summary.strip()
    if "cover" in label:
        return cover_letter.strip()
    if "linkedin" in label:
        return linkedIn
    if "website" in label or "portfolio" in label:
        return website
    if "employer" in label:
        return recent_employer
    if "name" in label:
        if "first" in label:
            return first_name
        if "last" in label:
            return last_name
        return _full_name()
    if "scale" in label and "10" in label:
        return confidence_level
    return ""


def _ai_answer(ai_client, ai_provider: str, label: str, job_description: str, options: list[str] | None = None) -> str:
    try:
        if ai_provider == "gemini":
            from modules.ai.geminiConnections import gemini_answer_naukri_question
            return gemini_answer_naukri_question(
                ai_client, label, options=options,
                question_type='single_select' if options else 'text',
                job_description=job_description,
                user_information=user_information_all,
            )
        if ai_provider == "openai":
            from modules.ai.openaiConnections import ai_answer_question
            return ai_answer_question(ai_client, label, question_type="text", job_description=job_description, user_information_all=user_information_all)
        if ai_provider == "deepseek":
            from modules.ai.deepseekConnections import deepseek_answer_question
            return deepseek_answer_question(ai_client, label, options=None, question_type="text", job_description=job_description, about_company=None, user_information_all=user_information_all)
    except Exception as e:
        print_lg(f"AI answer failed for '{label}': {e}")
    return ""


def fill_form_fields(
    driver: WebDriver,
    work_location: str,
    job_description: str = "",
    ai_client=None,
    ai_provider: str = "openai",
    use_ai: bool = False,
    randomly_answered: set | None = None,
) -> set:
    randomly_answered = randomly_answered or set()
    answered: set = set()
    container = find_first(driver, S.FORM_CONTAINER, timeout=5) or driver

    for inp in container.find_elements(By.XPATH, S.FORM_INPUT):
        try:
            if inp.get_attribute("type") in ("hidden", "file", "submit", "button"):
                continue
            label = inp.get_attribute("placeholder") or inp.get_attribute("name") or inp.get_attribute("id") or "Unknown"
            prev = inp.get_attribute("value") or ""
            if prev and not overwrite_previous_answers:
                continue
            answer = answer_for_label(label, work_location)
            if not answer and use_ai and ai_client:
                answer = _ai_answer(ai_client, ai_provider, label, job_description)
            if not answer:
                answer = years_of_experience
                randomly_answered.add(label)
            inp.clear()
            inp.send_keys(answer)
            answered.add((label, answer, "text"))
            buffer(1)
        except Exception:
            continue

    for ta in container.find_elements(By.XPATH, S.FORM_TEXTAREA):
        try:
            label = ta.get_attribute("placeholder") or ta.get_attribute("name") or "textarea"
            prev = ta.text or ""
            if prev and not overwrite_previous_answers:
                continue
            answer = answer_for_label(label, work_location)
            if not answer and use_ai and ai_client:
                answer = _ai_answer(ai_client, ai_provider, label, job_description)
            if not answer:
                answer = linkedin_summary.strip() or cover_letter.strip()
            ta.clear()
            ta.send_keys(answer)
            answered.add((label, answer[:80], "textarea"))
        except Exception:
            continue

    for sel_el in container.find_elements(By.XPATH, S.FORM_SELECT):
        try:
            sel = Select(sel_el)
            label = sel_el.get_attribute("name") or "select"
            opts = [o.text for o in sel.options if o.text.strip()]
            answer = answer_for_label(label, work_location)
            if not answer and use_ai and ai_client:
                answer = _ai_answer(ai_client, ai_provider, label, job_description, options=opts)
            if not answer:
                answer = "Yes"
            try:
                sel.select_by_visible_text(answer)
            except Exception:
                # Try case-insensitive match
                matched = False
                for opt_text in opts:
                    if opt_text.lower() == answer.lower():
                        sel.select_by_visible_text(opt_text)
                        matched = True
                        break
                if not matched and len(opts) > 1:
                    sel.select_by_index(1)
                    randomly_answered.add(label)
            answered.add((label, answer, "select"))
        except Exception:
            continue

    for radio in container.find_elements(By.XPATH, S.FORM_RADIO):
        try:
            if radio.is_selected():
                continue
            label_id = radio.get_attribute("id")
            label_el = container.find_element(By.XPATH, f".//label[@for='{label_id}']") if label_id else None
            label_text = label_el.text if label_el else "radio"
            answer = answer_for_label(label_text.lower(), work_location) or "Yes"
            parent = radio.find_element(By.XPATH, "./..")
            try:
                opt = parent.find_element(By.XPATH, f".//label[contains(text(),'{answer}')]")
                opt.click()
            except Exception:
                radio.click()
            answered.add((label_text, answer, "radio"))
        except Exception:
            continue

    for checkbox in container.find_elements(By.XPATH, S.FORM_CHECKBOX):
        try:
            label_id = checkbox.get_attribute("id")
            label_text = "checkbox"
            if label_id:
                try:
                    label_text = container.find_element(By.XPATH, f".//label[@for='{label_id}']").text
                except Exception:
                    pass
            if checkbox.is_selected():
                continue
            answer = answer_for_label(label_text.lower(), work_location) or "Yes"
            if answer.lower() in ("yes", "true"):
                checkbox.click()
                answered.add((label_text, answer, "checkbox"))
        except Exception:
            continue

    return answered


def upload_resume(driver: WebDriver, resume_path: str) -> tuple[bool, str]:
    if not resume_path or not os.path.exists(resume_path):
        return False, "Previous resume"
    upload = find_first(driver, S.RESUME_UPLOAD, timeout=3)
    if upload:
        try:
            upload.send_keys(os.path.abspath(resume_path))
            return True, os.path.basename(resume_path)
        except Exception as e:
            print_lg(f"Resume upload failed: {e}")
    return False, "Previous resume"
