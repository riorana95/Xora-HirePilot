'''
Develop by Rana Rahul

Handle Naukri chat-style recruiter questionnaire (one question → Save → next).
'''

import json
import re
import time
from datetime import datetime
from pathlib import Path

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import Select

from config.naukri_questions import (
    custom_naukri_answers, default_yes_no_answer, pause_at_unknown_naukri_question,
    willing_to_relocate,
)
from config.questions import current_ctc, desired_salary, notice_period, years_of_experience
from config.settings import logs_folder_path
from modules.helpers import buffer, print_lg
from modules.naukri.dom_helpers import click_first, find_first
from modules.naukri.forms import answer_for_label, _ai_answer
from modules.naukri.ai_answers_log import record_ai_answer
from modules.naukri import selectors as S

UNKNOWN_LOG = Path(logs_folder_path) / "naukri_unknown_questions.jsonl"
MAX_STEPS = 25

YES_VARIANTS = {"yes", "y", "true", "yeah", "sure", "ok", "okay"}
NO_VARIANTS = {"no", "n", "false", "nah", "not really"}

# Longest name first so "months" matches before "month".
_DURATION_UNITS = [
    ("years", 365.0), ("year", 365.0), ("yrs", 365.0), ("yr", 365.0),
    ("months", 30.0), ("month", 30.0),
    ("weeks", 7.0), ("week", 7.0),
    ("days", 1.0), ("day", 1.0),
]


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


_last_unknown_logged: set = set()

# True while resolving a question whose answer came from the AI (not from
# config); the main loop records such answers into the AI-answers review log.
_answer_was_ai = False


def _log_unknown_question(question: str, options: list[str]) -> None:
    # Log each distinct question once per run: the file feeds the dashboard's
    # unknown-questions list, and repeats just bury the genuinely new ones.
    key = _norm_text(question)
    if key in _last_unknown_logged:
        return
    _last_unknown_logged.add(key)
    UNKNOWN_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {"question": question, "options": options, "time": datetime.now().isoformat()}
    # utf-8 (no BOM): a BOM on the first line breaks naive json.loads readers.
    with open(UNKNOWN_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    print_lg(f"UNKNOWN Naukri question logged -> {UNKNOWN_LOG}")
    print_lg(f'  Q: "{question}"')
    print_lg(f"  Options: {options}")
    print_lg('  Add to config/naukri_questions.py -> custom_naukri_answers')


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
            answer = _ai_answer(ai_client, ai_provider, question, job_description, options=options or None)

        answer = (answer or "").strip()
        if not answer:
            return ""

        # Persist answer for future applications
        custom_naukri_answers[question] = answer
        try:
            from modules.config_manager import save_config
            save_config({"naukri_questions": {"custom_naukri_answers": custom_naukri_answers}})
            print_lg(f'AI answered and saved for future: "{question}" -> "{answer}"')
        except Exception as e:
            print_lg(f"Could not save AI answer: {e}")
        global _answer_was_ai
        _answer_was_ai = True
        return answer
    except Exception as e:
        print_lg(f"AI failed to answer question: {e}")
        return ""


# --------------------------------------------------------------------------- #
# Option parsing / matching                                                     #
# --------------------------------------------------------------------------- #

def _unit_scale(option_text: str, unit: str) -> float | None:
    '''Multiplier converting the number inside `option_text` into `unit` units.'''
    t = option_text
    if unit == "days":
        for name, days in _DURATION_UNITS:
            if name in t:
                return days
        return 1.0  # bare number: assume days
    if unit == "years":
        for name, days in _DURATION_UNITS:
            if name in t:
                return days / 365.0
        return 1.0  # bare number: assume years
    if unit == "lakhs":
        if "crore" in t or " cr" in t:
            return 100.0
        if "lakh" in t or "lac" in t or "lpa" in t:
            return 1.0
        if "thousand" in t or " k" in t or t.endswith("k"):
            return 0.001
        return 1.0  # bare number: assume lakhs
    return 1.0


def _parse_option_range(option: str, unit: str) -> tuple[float, float] | None:
    '''Parse an option label into a numeric range expressed in `unit` units.

    Handles "1.5 month", "2 weeks", "30 days", "3-5 years", "10-15 Lacs",
    "5+ years", "Immediate" (→ 0).
    '''
    t = _norm_text(option)
    if not t:
        return None
    if "immediate" in t or "right away" in t or "instant" in t:
        return (0.0, 0.0)
    scale = _unit_scale(t, unit)
    if scale is None:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)", t)
    if m:
        return (float(m.group(1)) * scale, float(m.group(2)) * scale)
    m = re.search(r"(\d+(?:\.\d+)?)\s*\+", t)
    if m:
        return (float(m.group(1)) * scale, float("inf"))
    m = re.search(r"(\d+(?:\.\d+)?)", t)
    if m:
        v = float(m.group(1)) * scale
        return (v, v)
    return None


def _question_target(question: str) -> tuple[str, float] | None:
    '''(unit, value) the user configured for this question's topic, if any.'''
    q = _norm_text(question)
    if "notice" in q:
        try:
            return ("days", float(notice_period))
        except (TypeError, ValueError):
            return None
    if "experience" in q or "expertise" in q or re.search(r"\byears?\b", q):
        try:
            return ("years", float(years_of_experience))
        except (TypeError, ValueError):
            return None
    if any(k in q for k in ("ctc", "salary", "compensation", "lpa", "lakh", "package")):
        value = current_ctc if any(k in q for k in ("current", "present", "drawing")) else desired_salary
        try:
            lakhs = float(value) / 100000.0 if float(value) >= 1000 else float(value)
        except (TypeError, ValueError):
            return None
        return ("lakhs", lakhs)
    return None


def _best_numeric_option(question: str, options: list[str]) -> str | None:
    '''Pick the option whose numeric range best fits the configured value.'''
    target = _question_target(question)
    if not target:
        return None
    unit, value = target
    ranges: list[tuple[str, tuple[float, float]]] = []
    for opt in options:
        rng = _parse_option_range(opt, unit)
        if rng is not None:
            ranges.append((opt, rng))
    if not ranges:
        return None

    # A range that contains the configured value wins.
    for opt, (lo, hi) in ranges:
        if lo <= value <= hi:
            return opt

    # Notice period: never claim a shorter notice than the real one —
    # take the smallest option at or above the target, else the longest.
    if unit == "days" and "notice" in _norm_text(question):
        above = [(opt, lo) for opt, (lo, hi) in ranges if lo >= value]
        if above:
            return min(above, key=lambda x: x[1])[0]
        return max(ranges, key=lambda x: x[1][1])[0]

    # Otherwise: closest option by midpoint.
    def mid(rng: tuple[float, float]) -> float:
        hi = rng[1] if rng[1] != float("inf") else rng[0] + 1.0
        return (rng[0] + hi) / 2.0

    return min(ranges, key=lambda x: abs(mid(x[1]) - value))[0]


def _match_answer_to_option(answer: str, options: list[str]) -> str | None:
    '''Map a free-form answer onto one of the visible options.'''
    a = _norm_text(answer)
    if not a:
        return None
    normed = [(_norm_text(opt), opt) for opt in options]
    for o, orig in normed:
        if o == a:
            return orig
    if a in YES_VARIANTS or a in NO_VARIANTS:
        want = YES_VARIANTS if a in YES_VARIANTS else NO_VARIANTS
        for o, orig in normed:
            if o in want:
                return orig
        return None
    # Answer appears inside exactly one option ("40" → "40 days").
    hits = [orig for o, orig in normed if a and a in o]
    if len(hits) == 1:
        return hits[0]
    # Option appears inside the answer ("1.5 month" inside a longer AI reply).
    hits = [orig for o, orig in normed if o and o in a]
    if len(hits) == 1:
        return hits[0]
    m = re.search(r"\d+(?:\.\d+)?", a)
    if m:
        num = m.group(0)
        hits = [orig for o, orig in normed if num in o]
        if len(hits) == 1:
            return hits[0]
    return None


def _options_look_yes_no(options: list[str]) -> bool:
    vals = {_norm_text(o) for o in options}
    return bool(vals) and vals <= (YES_VARIANTS | NO_VARIANTS)


# --------------------------------------------------------------------------- #
# DOM interaction                                                               #
# --------------------------------------------------------------------------- #

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


def _get_visible_options(modal: WebElement, question: str = "") -> list[str]:
    '''Collect the visible answer options: labels, option-like leaves and the
    text next to each radio/checkbox input (Naukri renders options as
    input + sibling text without <label for=…>).'''
    options: list[str] = []
    blocked = {"save", "next", "continue", "submit", "cancel", "skip", "apply", "close", "edit", "select"}
    q_norm = _norm_text(question)

    def add(text: str) -> None:
        t = re.sub(r"\s+", " ", (text or "")).strip()
        if not t or len(t) > 60 or len(t.split()) > 8:
            return
        n = _norm_text(t)
        if (n in blocked or n == q_norm or "?" in t
                or "recruiter" in n or n.endswith("questions") or n.endswith("question")):
            return
        if t not in options:
            options.append(t)

    for xpath in [".//label", ".//span", ".//div", ".//li", ".//p", ".//option"]:
        try:
            for el in modal.find_elements(By.XPATH, xpath):
                if not el.is_displayed():
                    continue
                if el.find_elements(By.XPATH, ".//*"):
                    continue  # leaves only: skip wrappers that contain the whole list
                add(el.text)
        except Exception:
            continue

    for inp in modal.find_elements(By.XPATH, ".//input[@type='checkbox' or @type='radio']"):
        try:
            add(inp.find_element(By.XPATH, "./..").text)
        except Exception:
            continue
    return options


def resolve_answer(
    question: str, work_location: str, use_ai: bool, ai_client, ai_provider: str,
    job_description: str, options: list[str] | None = None,
) -> str:
    '''Resolve the answer for a question. When `options` is provided (a
    selectable question), the answer is always mapped onto one of them so the
    option can actually be clicked.'''
    options = [o.strip() for o in (options or []) if o and o.strip()]
    base = _resolve_base_answer(question, work_location, use_ai, ai_client, ai_provider, job_description)
    if not options:
        return base

    matched = _match_answer_to_option(base, options)
    if matched:
        return matched

    numeric = _best_numeric_option(question, options)
    if numeric:
        return numeric

    if _options_look_yes_no(options):
        return default_yes_no_answer

    return ""


def _resolve_base_answer(
    question: str, work_location: str, use_ai: bool, ai_client, ai_provider: str,
    job_description: str, options: list[str] | None = None,
) -> str:
    global _answer_was_ai
    _answer_was_ai = False
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
        ai_ans = _ai_answer(ai_client, ai_provider, question, job_description, options=options)
        if ai_ans:
            _answer_was_ai = True
            return ai_ans.lower() if ai_ans.lower() in ("yes", "no") else ai_ans

    # Yes/no question heuristic
    if any(w in q_lower for w in ["are you", "do you", "will you", "have you", "willing"]):
        return default_yes_no_answer.lower()

    return ""


def _safe_click(element: WebElement) -> None:
    try:
        element.click()
    except Exception:
        try:
            element.parent.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
            element.parent.execute_script("arguments[0].click();", element)
        except Exception:
            pass


def _click_option(modal: WebElement, answer: str) -> bool:
    '''Click the option matching `answer`. Matching is done on normalised text
    in Python (not XPath) so case, spacing and quote characters in answers
    cannot break the lookup.'''
    answer_norm = _norm_text(answer)
    if not answer_norm:
        return False
    targets = {answer_norm}
    if answer_norm in YES_VARIANTS:
        targets |= YES_VARIANTS
    elif answer_norm in NO_VARIANTS:
        targets |= NO_VARIANTS

    def matches(text: str) -> bool:
        t = _norm_text(text)
        if not t:
            return False
        if t in targets:
            return True
        words = set(t.split())
        return any(target in words for target in targets)

    # 1) Native checkbox/radio: match via <label for=…>, ancestor <label>, or
    #    the text of the input's immediate container (Naukri's layout).
    for inp in modal.find_elements(By.XPATH, ".//input[@type='checkbox' or @type='radio']"):
        try:
            label_text = ""
            inp_id = inp.get_attribute("id")
            if inp_id:
                try:
                    label_text = modal.find_element(By.XPATH, f".//label[@for='{inp_id}']").text
                except Exception:
                    label_text = ""
            if not label_text:
                try:
                    ancestors = inp.find_elements(By.XPATH, "ancestor::label[1]")
                    label_text = ancestors[0].text if ancestors else ""
                except Exception:
                    label_text = ""
            if not label_text:
                try:
                    label_text = inp.find_element(By.XPATH, "./..").text
                except Exception:
                    label_text = ""
            if label_text and matches(label_text):
                try:
                    if not inp.is_selected():
                        _safe_click(inp)
                except Exception:
                    _safe_click(inp)
                buffer(1)
                return True
        except Exception:
            continue

    # 2) Custom-rendered options (clickable leaves whose text matches).
    for xpath in [".//label", ".//span", ".//div", ".//li", ".//button", ".//p"]:
        try:
            for el in modal.find_elements(By.XPATH, xpath):
                if not el.is_displayed():
                    continue
                text = el.text or ""
                if not text or len(text) > 60:
                    continue
                if not el.find_elements(By.XPATH, ".//*") and matches(text):
                    _safe_click(el)
                    buffer(1)
                    return True
        except Exception:
            continue

    return False


def _select_native_option(modal: WebElement, answer: str) -> bool:
    '''Choose `answer` in a native <select> dropdown inside the drawer.'''
    for sel_el in modal.find_elements(By.XPATH, ".//select"):
        try:
            if not sel_el.is_displayed():
                continue
            sel = Select(sel_el)
            opts = [o.text for o in sel.options]
            for opt_text in opts:
                if _norm_text(opt_text) == _norm_text(answer):
                    sel.select_by_visible_text(opt_text)
                    buffer(1)
                    return True
            for opt_text in opts:
                if _norm_text(answer) and _norm_text(answer) in _norm_text(opt_text):
                    sel.select_by_visible_text(opt_text)
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


def _wait_for_answer_selection(driver: WebDriver, modal: WebElement, answer: str) -> bool:
    '''Wait until the drawer registers the answer: a selected radio/checkbox,
    a filled text field, or a custom selected/active option chip.'''
    for _ in range(15):
        try:
            for inp in modal.find_elements(By.XPATH, ".//input[@type='checkbox' or @type='radio']"):
                if inp.is_selected():
                    return True
            for inp in modal.find_elements(
                By.XPATH,
                ".//input[not(@type='checkbox') and not(@type='radio') and not(@type='hidden')]",
            ):
                try:
                    if inp.is_displayed() and (inp.get_attribute("value") or "").strip():
                        return True
                except Exception:
                    continue
            for el in modal.find_elements(
                By.XPATH,
                ".//*[contains(@class,'selected') or contains(@class,'active') or contains(@class,'checked')]",
            ):
                try:
                    if el.is_displayed():
                        return True
                except Exception:
                    continue
        except Exception:
            # The drawer re-rendered after our click (React) — re-locate it.
            modal = _find_chat_modal(driver)
            if not modal:
                return True  # drawer closed: nothing left to verify
        time.sleep(0.2)
    return False


def _detect_question_control(modal: WebElement) -> str:
    try:
        if modal.find_elements(By.XPATH, ".//input[@type='radio']"):
            return "radio"
        if modal.find_elements(By.XPATH, ".//input[@type='checkbox']"):
            return "checkbox"
        if modal.find_elements(By.XPATH, ".//select"):
            return "select"
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
    last_question = ""
    repeat_count = 0
    global _answer_was_ai

    for step in range(MAX_STEPS):
        modal = _find_chat_modal(driver)
        if not modal:
            break

        question = ""
        for _ in range(10):
            try:
                question = _extract_question_text(driver, modal)
            except Exception:
                question = ""
            if question:
                break
            time.sleep(0.3)
        if not question:
            print_lg("Recruiter modal visible but question text not found.")
            break

        if _norm_text(question) == _norm_text(last_question):
            repeat_count += 1
            if repeat_count >= 3:
                print_lg(f'Question "{question}" did not advance after answering; stopping.')
                unknown.append(question)
                break
        else:
            repeat_count = 0
            last_question = question

        control_type = _detect_question_control(modal)
        # Options only matter for selectable questions; a text question's
        # surrounding labels are noise and must not constrain the answer.
        options: list[str] = []
        if control_type in ("radio", "checkbox", "select", "unknown control"):
            try:
                options = _get_visible_options(modal, question)
            except Exception:
                options = []

        answer = resolve_answer(
            question, work_location, use_ai, ai_client, ai_provider,
            job_description, options=options,
        )

        if not answer:
            _log_unknown_question(question, options)
            if pause_at_unknown_naukri_question and not skip_alerts:
                try:
                    import pyautogui
                    manual = pyautogui.prompt(
                        f'Naukri question (answer will be saved for future runs):\n{question}\n'
                        f'Options: {options if options else "free text"}',
                        "Unknown Naukri Question",
                    )
                    if manual is not None and manual.strip():
                        answer = manual.strip()
                        custom_naukri_answers[question] = answer
                except Exception:
                    pass
            if not answer:
                answer = _ask_and_remember_answer(
                    question, options,
                    ai_client=ai_client, ai_provider=ai_provider, use_ai=use_ai,
                    job_description=job_description,
                )
                if answer and options:
                    answer = _match_answer_to_option(answer, options) or answer
        if not answer:
            if options and _options_look_yes_no(options):
                answer = default_yes_no_answer.lower()
                print_lg(f'AI and config both failed — using default: "{answer}"')
            else:
                print_lg(f'No answer available for recruiter question: "{question}"')
                unknown.append(question)
                break

        if _answer_was_ai and answer:
            # Review log: every AI-sourced answer (matched onto its option)
            # lands in the dashboard's AI Answers page for your feedback.
            record_ai_answer(question, answer, options)
            _answer_was_ai = False

        print_lg(f'Naukri Q [{control_type}]: "{question}" -> "{answer}"' + (f' | options: {options}' if options else ''))

        clicked = _select_native_option(modal, answer) if control_type == "select" else False
        if not clicked:
            clicked = _click_option(modal, answer)
        if not clicked and control_type not in ("radio", "checkbox", "select"):
            clicked = _fill_text_input(modal, answer)

        if not clicked:
            print_lg(f'Could not select/type recruiter answer: "{answer}"')
            unknown.append(question)
            break
        print_lg(f'Recruiter answer entered: "{answer}"; waiting for the drawer to register it.')

        # A native <select> has no "selected" CSS state the waiter can detect
        # reliably, so a successful selection is taken as registered.
        if control_type != "select" and not _wait_for_answer_selection(driver, modal, answer):
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
