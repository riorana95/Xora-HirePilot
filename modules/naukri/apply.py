'''
Develop by Rana Rahul

Naukri job apply flow — detect apply type, fill forms, submit.
'''

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from config.questions import default_resume_path, pause_before_submit
from config.search_naukri import apply_on_naukri_only
from modules.helpers import buffer, print_lg, is_headless
from modules.naukri.dom_helpers import click_first, find_first
from modules.naukri.forms import fill_form_fields, upload_resume
from modules.naukri.questionnaire import handle_recruiter_questionnaire, is_recruiter_modal_visible
from modules.naukri import selectors as S


class ApplyResult:
    def __init__(
        self,
        success: bool,
        apply_type: str = "unknown",
        application_link: str = "Pending",
        resume: str = "Pending",
        questions: set | None = None,
        error: str = "",
        unknown_questions: list | None = None,
    ):
        self.success = success
        self.apply_type = apply_type
        self.application_link = application_link
        self.resume = resume
        self.questions = questions or set()
        self.error = error
        self.unknown_questions = unknown_questions or []


def submit_application(driver: WebDriver, skip_alerts: bool) -> bool:
    for _ in range(5):
        if pause_before_submit and not skip_alerts and not is_headless():
            try:
                import pyautogui
                pyautogui.alert("Review the Naukri application form, then click OK to submit.", "Pause Before Submit", "OK")
            except Exception:
                pass
        if click_first(driver, S.FORM_SUBMIT, timeout=3):
            buffer(2)
            return True
        if click_first(driver, S.FORM_NEXT, timeout=2):
            buffer(2)
            continue
        break
    return False


def apply_from_detail_page(
    driver: WebDriver,
    work_location: str,
    job_description: str = "",
    ai_client=None,
    ai_provider: str = "openai",
    use_ai: bool = False,
    skip_alerts: bool = False,
    randomly_answered: set | None = None,
) -> ApplyResult:
    '''Apply to job on the current Naukri job detail page.'''
    for xpath in S.ALREADY_APPLIED:
        try:
            if driver.find_element(By.XPATH, xpath):
                return ApplyResult(False, "already_applied", error="Already applied")
        except Exception:
            continue

    for xpath in S.EXTERNAL_APPLY:
        try:
            el = driver.find_element(By.XPATH, xpath)
            if apply_on_naukri_only:
                return ApplyResult(False, "external_skipped", error="External apply skipped")
            el.click()
            buffer(2)
            return ApplyResult(True, "external", application_link=driver.current_url, resume="N/A")
        except Exception:
            continue

    if not click_first(driver, S.APPLY_BUTTON, timeout=5):
        return ApplyResult(False, "unknown", error="Apply button not found")

    buffer(2)
    all_questions: set = set()
    unknown_questions: list = []

    # Naukri chat-style recruiter questionnaire (one Q → Save → next Q)
    if is_recruiter_modal_visible(driver):
        print_lg("Naukri recruiter drawer detected immediately after Apply.")
        chat_answered, unknown = handle_recruiter_questionnaire(
            driver, work_location, job_description,
            ai_client=ai_client, ai_provider=ai_provider, use_ai=use_ai, skip_alerts=skip_alerts,
        )
        all_questions.update(chat_answered)
        unknown_questions.extend(unknown)
        if unknown:
            click_first(driver, S.FORM_CLOSE, timeout=2)
            return ApplyResult(False, "naukri", error="Unanswered recruiter question", questions=all_questions, unknown_questions=unknown_questions)

    # Avoid delaying the chat drawer with a resume-upload lookup. Upload only
    # after chat questions have been handled (or for a standard form).
    resume_ok, resume_name = upload_resume(driver, default_resume_path)

    # Standard form fields (if any remain after chat modal)
    form_answered = fill_form_fields(
        driver, work_location, job_description,
        ai_client=ai_client, ai_provider=ai_provider, use_ai=use_ai,
        randomly_answered=randomly_answered,
    )
    all_questions.update(form_answered)

    # Handle any additional chat steps that appear after standard form
    if is_recruiter_modal_visible(driver):
        chat_answered, unknown = handle_recruiter_questionnaire(
            driver, work_location, job_description,
            ai_client=ai_client, ai_provider=ai_provider, use_ai=use_ai, skip_alerts=skip_alerts,
        )
        all_questions.update(chat_answered)
        unknown_questions.extend(unknown)
        if unknown:
            click_first(driver, S.FORM_CLOSE, timeout=2)
            return ApplyResult(False, "naukri", error="Unanswered recruiter question", questions=all_questions, unknown_questions=unknown_questions)

    submitted = submit_application(driver, skip_alerts)
    if submitted or not is_recruiter_modal_visible(driver):
        return ApplyResult(
            True, "naukri", application_link="Applied on Naukri",
            resume=resume_name if resume_ok else "Previous resume",
            questions=all_questions, unknown_questions=unknown_questions,
        )
    click_first(driver, S.FORM_CLOSE, timeout=2)
    return ApplyResult(
        False, "naukri", error="Submit failed",
        questions=all_questions, unknown_questions=unknown_questions,
    )
