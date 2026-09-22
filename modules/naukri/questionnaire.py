'''
Develop by Rana Rahul

Handle Naukri chat-style recruiter questionnaire (one question → Save → next).
'''

import json
import os
import time
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from config.naukri_questions import (
    custom_naukri_answers, default_yes_no_answer, pause_at_unknown_naukri_question,
    willing_to_relocate,
)
from config.settings import logs_folder_path
from modules.helpers import buffer, print_lg
from modules.naukri.dom_helpers import click_first, find_first
from modules.naukri.forms import answer_for_label, _ai_answer
from modules.naukri import selectors as S

UNKNOWN_LOG = Path(logs_folder_path) / "naukri_unknown_questions.jsonl"
MAX_STEPS = 15
def _log_unknown_question(question: str, options: list[str]) -> None:
    UNKNOWN_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"question": question, "options": options, "time": datetime.now().isoformat()}
    with open(UNKNOWN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print_lg(f"UNKNOWN Naukri question logged → {UNKNOWN_LOG}")
    print_lg(f'  Q: "{question}"')
    print_lg(f"  Options: {options}")
    print_lg('  Add to config/naukri_questions.py → custom_naukri_answers')


def _ask_and_remember_answer(
    question: str, options: list[str],
    ai_client=None, ai_provider: str = 'gemini', use_ai: bool = True,
    job_description: str = '',
) -> str:
    '''Use AI to answer the question, then persist the answer for future reuse.'''
    if not use_ai or not ai_client:
        return ""
    
    try:
        if ai_provider == 'gemini':
            from modules.ai.geminiConnections import gemini_answer_naukri_question
            from config.questions import user_information_all
            answer = gemini_answer_naukri_question(
                ai_client, question, options=options,
                question_type='single_select' if options else 'text',
                job_description=job_description,
                user_information=user_information_all,
            )
        else:
            from modules.naukri.forms import _ai_answer
            answer = _ai_answer(ai_client, ai_provider, question, job_description, options=options)
        
        answer = (answer or "").strip()
        if not answer:
            return ""
        
        # Persist answer for future applications
        custom_naukri_answers[question] = answer
        try:
            from modules.config_manager import save_config
            save_config({"naukri_questions": {"custom_naukri_answers": custom_naukri_answers}})
            print_lg(f'AI answered and saved for future: "{question}" → "{answer}"')
        except Exception as e:
            print_lg(f"Could not save AI answer: {e}")
        return answer
    except Exception as e:
        print_lg(f"AI failed to answer question: {e}")
        return ""


def _find_chat_modal(driver: WebDriver) -> WebElement | None:
    for xpath in S.RECRUITER_CHAT_MODAL:
        try:
            el = driver.find_element(By.XPATH, xpath)
            if el.is_displayed():
                return el
        except Exception:
            continue
    return None


def _extract_question_text(driver: WebDriver, modal: WebElement) -> str:
    for xpath in S.RECRUITER_QUESTION_TEXT:
        try:
            els = modal.find_elements(By.XPATH, xpath)
            for el in reversed(els):
                text = el.text.strip()
                if text and "thank you for showing interest" not in text.lower():
                    if "?" in text or len(text) > 15:
                        return text
        except Exception:
            continue
    # Fallback: last substantial text block in modal
    try:
        blocks = modal.find_elements(By.XPATH, ".//*[string-length(normalize-space(text())) > 20]")
        for el in reversed(blocks):
            t = el.text.strip()
            if t and "save" not in t.lower() and "recruiter" not in t.lower():
                return t.split("\n")[0]
    except Exception:
        pass

    # Naukri's drawer places the prompt and the input/save area in sibling
    # containers. In that layout the detected field panel does not contain the
    # prompt, so read the visible question from the right side of the page.
    try:
        question = driver.execute_script("""
            const visible = el => {
                const style = getComputedStyle(el), rect = el.getBoundingClientRect();
                return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
            };
            const candidates = [...document.querySelectorAll('body *')].filter(el =>
                el.children.length === 0 && visible(el) && el.innerText.includes('?') &&
                el.getBoundingClientRect().left >= window.innerWidth * 0.55
            ).map(el => el.innerText.trim()).filter(Boolean);
            return candidates.at(-1) || '';
        """)
        if question:
            return question
    except Exception:
        pass
    return ""


def _get_visible_options(modal: WebElement) -> list[str]:
    options: list[str] = []
    for xpath in [".//label", ".//span[contains(@class,'option')]", ".//div[contains(@class,'option')]"]:
        try:
            for el in modal.find_elements(By.XPATH, xpath):
                t = el.text.strip().lower()
                if t in ("yes", "no", "true", "false") or (len(t) < 40 and t):
                    if t not in options:
                        options.append(t)
        except Exception:
            continue
    return options


def resolve_answer(question: str, work_location: str, use_ai: bool, ai_client, ai_provider: str, job_description: str) -> str:
    q_lower = question.lower()

    if "relocate" in q_lower or "relocation" in q_lower:
        return willing_to_relocate.lower()

    for keyword, ans in custom_naukri_answers.items():
        if keyword.lower() in q_lower:
            return str(ans).lower() if str(ans).lower() in ("yes", "no") else str(ans)

    ans = answer_for_label(q_lower, work_location)
    if ans:
        return ans.lower() if ans.lower() in ("yes", "no") else ans

    if use_ai and ai_client:
        ai_ans = _ai_answer(ai_client, ai_provider, question, job_description)
        if ai_ans:
            return ai_ans.lower() if ai_ans.lower() in ("yes", "no") else ai_ans

    # Yes/no question heuristic
    if any(w in q_lower for w in ["are you", "do you", "will you", "have you", "willing"]):
        return default_yes_no_answer.lower()

    return ""


def _click_option(modal: WebElement, answer: str) -> bool:
    answer_lower = answer.strip().lower()
    yes_variants = ["yes", "y", "true"]
    no_variants = ["no", "n", "false"]
    targets = [answer_lower]
    if answer_lower in yes_variants:
        targets = yes_variants
    elif answer_lower in no_variants:
        targets = no_variants

    for target in targets:
        for xpath in [
            f".//label[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{target}')]",
            f".//span[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{target}')]",
            f".//*[contains(@class,'checkbox') or contains(@class,'radio')]/following-sibling::*[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'{target}')]",
        ]:
            try:
                els = modal.find_elements(By.XPATH, xpath)
                for el in els:
                    if el.is_displayed():
                        el.click()
                        buffer(1)
                        return True
            except Exception:
                continue

    # Native checkbox/radio
    for inp in modal.find_elements(By.XPATH, ".//input[@type='checkbox' or @type='radio']"):
        try:
            label_id = inp.get_attribute("id")
            label_text = ""
            if label_id:
                try:
                    label_text = modal.find_element(By.XPATH, f".//label[@for='{label_id}']").text.lower()
                except Exception:
                    pass
            if any(t in label_text for t in targets):
                if not inp.is_selected():
                    inp.click()
                    buffer(1)
                return True
        except Exception:
            continue

    return False


def _fill_text_input(modal: WebElement, answer: str) -> bool:
    for inp in modal.find_elements(By.XPATH, ".//input[@type='text' or @type='number' or @type='tel' or @type='email']"):
        try:
            if inp.is_displayed():
                inp.clear()
                inp.send_keys(answer)
                buffer(1)
                return True
        except Exception:
            continue
    for ta in modal.find_elements(By.XPATH, ".//textarea"):
        try:
            if ta.is_displayed():
                ta.clear()
                ta.send_keys(answer)
                buffer(1)
                return True
        except Exception:
            continue
    return False


def _click_save_or_next(driver: WebDriver, modal: WebElement) -> bool:
    # Click inside the active question drawer. A global lookup can otherwise
    # click the job card's "Save" button behind the drawer.
    for xpath in [
        ".//button[normalize-space()='Save']",
        ".//button[contains(normalize-space(.), 'Save')]",
        ".//button[contains(normalize-space(.), 'Continue')]",
        ".//button[contains(normalize-space(.), 'Next')]",
        ".//button[contains(normalize-space(.), 'Submit')]",
        ".//button[contains(normalize-space(.), 'Apply')]",
    ]:
        try:
            for button in modal.find_elements(By.XPATH, xpath):
                if button.is_displayed() and button.is_enabled():
                    button.click()
                    print_lg(f'Clicked recruiter drawer action: "{button.text.strip()}"')
                    buffer(2)
                    return True
        except Exception:
            continue

    # Naukri often renders the option text beside a bare checkbox instead of a
    # <label for="…">. Match the text on its nearest visible container.
    for inp in modal.find_elements(By.XPATH, ".//input[@type='checkbox' or @type='radio']"):
        try:
            container_text = inp.find_element(By.XPATH, "./..").text.strip().lower()
            if any(target == container_text or target in container_text.split() for target in targets):
                if not inp.is_selected():
                    inp.click()
                buffer(1)
                return True
        except Exception:
            continue

    # In the current Naukri chatbot the question controls and its footer are
    # siblings. Search the chatbot root specifically, never the page-wide
    # "Save" button that belongs to the job card behind the overlay.
    for xpath in [
        "//*[contains(@class,'chatbot')]//button[normalize-space()='Save']",
        "//*[contains(@class,'chatbot')]//button[contains(normalize-space(.), 'Save')]",
        "//*[contains(@class,'chatbot')]//button[contains(normalize-space(.), 'Continue')]",
        "//*[contains(@class,'chatbot')]//button[contains(normalize-space(.), 'Next')]",
    ]:
        try:
            for button in driver.find_elements(By.XPATH, xpath):
                if button.is_displayed() and button.is_enabled():
                    driver.execute_script("arguments[0].click();", button)
                    print_lg(f'Clicked chatbot action: "{button.text.strip()}"')
                    buffer(2)
                    return True
        except Exception:
            continue

    # The footer is sometimes a div/span with click handling instead of a
    # button. Select the visible, right-side Save control, never the card Save.
    try:
        clicked = driver.execute_script("""
            const visible = el => {
                const s = getComputedStyle(el), r = el.getBoundingClientRect();
                return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0;
            };
            const candidates = [...document.querySelectorAll('button, [role="button"], div, span')]
                .filter(el => el.children.length === 0 && el.textContent.trim().toLowerCase() === 'save' && visible(el))
                .filter(el => el.getBoundingClientRect().left >= window.innerWidth * 0.55)
                .sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top);
            const target = candidates[0];
            if (!target || target.getAttribute('disabled') !== null || target.getAttribute('aria-disabled') === 'true') return false;
            target.click();
            return true;
        """)
        if clicked:
            print_lg('Clicked right-side recruiter drawer Save control.')
            buffer(2)
            return True
    except Exception as e:
        print_lg(f"Right-side Save click failed: {e}")
    return False


def _wait_for_answer_selection(modal: WebElement, answer: str) -> bool:
    answer_lower = answer.strip().lower()
    for _ in range(15):
        try:
            for inp in modal.find_elements(By.XPATH, ".//input[@type='checkbox' or @type='radio']"):
                if inp.is_selected():
                    return True
            for inp in modal.find_elements(By.XPATH, ".//input[not(@type='checkbox') and not(@type='radio')]"):
                if (inp.get_attribute("value") or "").strip() == answer:
                    return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _detect_question_control(modal: WebElement) -> str:
    try:
        if modal.find_elements(By.XPATH, ".//input[@type='radio']"):
            return "radio"
        if modal.find_elements(By.XPATH, ".//input[@type='checkbox']"):
            return "checkbox"
        if modal.find_elements(By.XPATH, ".//textarea"):
            return "textarea"
        if modal.find_elements(By.XPATH, ".//input[not(@type='hidden')]"):
            return "text input"
    except Exception:
        pass
    return "unknown control"


def handle_recruiter_questionnaire(
    driver: WebDriver,
    work_location: str = "",
    job_description: str = "",
    ai_client=None,
    ai_provider: str = "openai",
    use_ai: bool = False,
    skip_alerts: bool = False,
) -> tuple[set, list[str]]:
    '''
    Loop through Naukri chat-style recruiter questions until modal closes.
    Returns (answered_set, unknown_questions_list).
    '''
    answered: set = set()
    unknown: list[str] = []

    for step in range(MAX_STEPS):
        modal = _find_chat_modal(driver)
        if not modal:
            break

        question = ""
        for _ in range(10):
            question = _extract_question_text(driver, modal)
            if question:
                break
            time.sleep(0.3)
        if not question:
            print_lg("Recruiter modal visible but question text not found.")
            break

        options = _get_visible_options(modal)
        control_type = _detect_question_control(modal)
        answer = resolve_answer(question, work_location, use_ai, ai_client, ai_provider, job_description)

        if not answer:
            _log_unknown_question(question, options)
            # Try AI first
            answer = _ask_and_remember_answer(
                question, options,
                ai_client=ai_client, ai_provider=ai_provider, use_ai=use_ai,
                job_description=job_description,
            )
            if not answer:
                # Fallback: default for yes/no, or skip
                if options:
                    answer = default_yes_no_answer.lower()
                    print_lg(f'AI and config both failed — using default: "{answer}"')
                else:
                    answer = default_yes_no_answer.lower()
                    print_lg(f'AI and config both failed — using default: "{answer}"')

        print_lg(f'Naukri Q [{control_type}]: "{question}" → "{answer}"')

        clicked = _click_option(modal, answer)
        if not clicked:
            clicked = _fill_text_input(modal, answer)

        if not clicked:
            print_lg(f'Could not select/type recruiter answer: "{answer}"')
            unknown.append(question)
            break
        print_lg(f'Recruiter answer entered: "{answer}"; waiting for the drawer to register it.')

        if not _wait_for_answer_selection(modal, answer):
            print_lg(f'Recruiter answer was not registered: "{answer}"; Save will not be clicked.')
            unknown.append(question)
            break
        print_lg('Recruiter answer registered; clicking Save/Next.')

        answered.add((question, answer, "checkbox" if options else "text"))

        if not _click_save_or_next(driver, modal):
            print_lg("Save/Next button not found on recruiter modal.")
            unknown.append(question)
            break

        buffer(2)
        # If modal gone, done
        if not _find_chat_modal(driver):
            break

    return answered, unknown


def is_recruiter_modal_visible(driver: WebDriver) -> bool:
    return _find_chat_modal(driver) is not None
