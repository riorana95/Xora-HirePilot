'''
Offline verification of the Naukri questionnaire fix.

Part A: pure-logic unit tests of option parsing / matching (no selenium).
Part B: fake-DOM end-to-end simulation reproducing the exact EPAM failure
        recorded in logs/log.txt:
        Naukri Q [radio]: "What is your Notice Period?" -> "40"
        Could not select/type recruiter answer: "40"
        The fake DOM answers the same XPath queries the real modules issue
        (evaluated with lxml), so the real selectors and the real flow run.
'''

import sys
import types
from pathlib import Path

PROJECT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, PROJECT)


# --------------------------------------------------------------------------- #
# Stub selenium + pyautogui so the project modules import without a browser.   #
# --------------------------------------------------------------------------- #
def _install_stubs() -> None:
    class _By:
        XPATH = "xpath"

    def mod(name: str, **attrs):
        m = types.ModuleType(name)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[name] = m
        return m

    mod("selenium")
    mod("selenium.webdriver")
    mod("selenium.webdriver.common")
    mod("selenium.webdriver.common.by", By=_By)
    mod("selenium.webdriver.remote")
    mod("selenium.webdriver.remote.webdriver", WebDriver=object)
    mod("selenium.webdriver.remote.webelement", WebElement=object)
    mod("selenium.webdriver.support")
    class _Wait:
        def __init__(self, driver, timeout=0):
            self.driver = driver

        def until(self, method):
            return method(self.driver)

    class _EC:
        @staticmethod
        def presence_of_element_located(locator):
            by, xp = locator

            def _predicate(driver):
                return driver.find_element(by, xp)

            return _predicate

    mod("selenium.webdriver.support.ui", Select=object, WebDriverWait=_Wait)
    ec = mod("selenium.webdriver.support.expected_conditions", EC=_EC)
    # `from selenium.webdriver.support import expected_conditions` needs the
    # attribute present on the parent package too.
    sys.modules["selenium.webdriver.support"].expected_conditions = ec
    pyautogui = mod("pyautogui", alert=lambda *a, **k: None, prompt=lambda *a, **k: None)
    pyautogui.alert = lambda *a, **k: None


_install_stubs()

from lxml import etree  # noqa: E402

from modules.naukri import questionnaire as Q  # noqa: E402
from modules.naukri import selectors as S  # noqa: E402

# Speed the test up and keep the project log file clean.
Q.buffer = lambda *a, **k: None
Q.print_lg = lambda *a, **k: None

EPAM_OPTIONS = ["2 weeks", "3 weeks", "1 month", "1.5 month", "2 months", "3 months"]

RESULTS: list[tuple[str, bool, str]] = []


def check(name: str, got, expected) -> None:
    ok = got == expected
    RESULTS.append((name, ok, f"got={got!r} expected={expected!r}"))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> got={got!r} expected={expected!r}"))


# --------------------------------------------------------------------------- #
# Part A — pure logic                                                          #
# --------------------------------------------------------------------------- #
def test_pure_logic() -> None:
    print("\n=== A. pure logic ===")

    # Range parsing (unit conversion to days)
    check("parse '1.5 month' as days", Q._parse_option_range("1.5 month", "days"), (45.0, 45.0))
    check("parse '2 weeks' as days", Q._parse_option_range("2 weeks", "days"), (14.0, 14.0))
    check("parse '3-5 years' as days", Q._parse_option_range("3-5 years", "days"), (1095.0, 1825.0))
    check("parse 'Immediate' as days", Q._parse_option_range("Immediate", "days"), (0.0, 0.0))
    check("parse '5+ years' as years", Q._parse_option_range("5+ years", "years"), (5.0, float("inf")))
    check("parse '10-15 Lacs' as lakhs", Q._parse_option_range("10-15 Lacs", "lakhs"), (10.0, 15.0))

    # THE original failure: resolve the notice-period answer onto the options
    # (config has notice_period = 40 days)
    check(
        "resolve notice 40d vs EPAM options -> '1.5 month'",
        Q.resolve_answer("What is your Notice Period?", "", False, None, "openai", "", options=EPAM_OPTIONS),
        "1.5 month",
    )
    check(
        "resolve notice 40d vs 15/30/60/90 days -> '60'",
        Q.resolve_answer("What is your Notice Period?", "", False, None, "openai", "", options=["15 days", "30 days", "60 days", "90 days"]),
        "60 days",
    )

    saved_notice = Q.notice_period
    try:
        Q.notice_period = 20
        check(
            "resolve notice 20d vs 15/30/60 -> '30 days' (never understate)",
            Q.resolve_answer("What is your notice period?", "", False, None, "openai", "", options=["15 days", "30 days", "60 days"]),
            "30 days",
        )
        Q.notice_period = 10
        check(
            "resolve notice 10d vs 'Immediate/15/30' -> '15'",
            Q.resolve_answer("Notice period?", "", False, None, "openai", "", options=["Immediate", "15", "30"]),
            "15",
        )
    finally:
        Q.notice_period = saved_notice
    check(
        "resolve experience 4y vs ranges -> '3-5 years'",
        Q.resolve_answer("How many years of experience do you have?", "", False, None, "openai", "", options=["0-1 year", "1-3 years", "3-5 years", "5-7 years"]),
        "3-5 years",
    )
    check(
        "resolve current CTC 15 vs ranges -> '10-15 Lacs'",
        Q.resolve_answer("What is your current CTC?", "", False, None, "openai", "", options=["5-10 Lacs", "10-15 Lacs", "15-25 Lacs"]),
        "10-15 Lacs",
    )
    check(
        "relocate question mapped onto Yes/No options -> 'Yes'",
        Q.resolve_answer("Are you willing to relocate to Hyderabad?", "", False, None, "openai", "", options=["Yes", "No"]),
        "Yes",
    )
    check(
        "custom answer substring 'micr' -> 'yes' mapped onto options",
        Q.resolve_answer("Do you have microservices experience?", "", False, None, "openai", "", options=["Yes", "No"]),
        "Yes",
    )
    check(
        "text question (no options) still returns raw notice days",
        Q.resolve_answer("What is your notice period in days?", "", False, None, "openai", "", options=None),
        "40",
    )
    check(
        "yes/no options with no configured answer -> default",
        Q.resolve_answer("Are you comfortable working in night shifts?", "", False, None, "openai", "", options=["yes", "no"]),
        "yes",
    )
    check(
        "plural/singular option match '1.5 months'",
        Q._match_answer_to_option("1.5 month", ["1.5 months", "2 months"]),
        "1.5 months",
    )
    check(
        "AI free-text answer mapped onto option",
        Q._match_answer_to_option("I would say 3 weeks is my notice period", EPAM_OPTIONS),
        "3 weeks",
    )


# --------------------------------------------------------------------------- #
# Part B — fake DOM end-to-end                                                 #
# --------------------------------------------------------------------------- #
class FakeElement:
    def __init__(self, node, dom: "FakeDom", is_input: bool = False):
        self.node = node
        self.dom = dom
        self.is_input = is_input

    # --- xpath ---
    def find_elements(self, by, xpath):
        if by != "xpath":
            return []
        try:
            nodes = self.node.xpath(xpath)
        except Exception:
            return []
        out = []
        for n in nodes:
            if isinstance(n, etree._Element):  # noqa: SLF001
                out.append(FakeElement(n, self.dom, is_input=(n.tag == "input")))
        return out

    def find_element(self, by, xpath):
        els = self.find_elements(by, xpath)
        if not els:
            raise RuntimeError(f"no match for {xpath}")
        return els[0]

    # --- attributes / text ---
    def get_attribute(self, name):
        return self.node.get(name)

    @property
    def text(self):
        return " ".join(" ".join(self.node.itertext()).split())

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def is_selected(self):
        return self.dom.selected_inputs.get(self.node.get("id"))

    # --- interaction ---
    def click(self):
        if self.is_input:
            self.dom.selected_inputs[self.node.get("id")] = True
            # the option text is the input's container row text
            row_text = FakeElement(self.node.getparent(), self.dom).text
            self.dom.log.append(("click-input", self.node.get("id"), row_text))
        else:
            self.dom.log.append(("click", self.node.get("id") or self.node.tag, self.text))
            if self.node.tag == "button" and self.text.strip().lower() == "save":
                self.dom.on_drawer_save()

    def send_keys(self, value):
        self.dom.log.append(("type", self.node.get("name") or self.node.get("id"), value))

    def clear(self):
        pass


class FakeDom:
    '''Stages: each stage is a full-page HTML doc. Clicking the drawer's Save
    button advances to the next stage (the next recruiter question).'''

    STAGES = [
        # Stage 1 — the exact EPAM notice-period question that failed
        """
        <html><body>
          <div id="jobPage"><button id="cardSave">Save</button></div>
          <div class="chatbot-widget chatbot_open" role="dialog" id="drawer">
            <div class="chatbot_header">Recruiter's questions</div>
            <div class="chatbot_message">What is your Notice Period?</div>
            <div class="chatbot_options">
              <div class="chatbot_optionRow"><input type="radio" id="np1" name="notice"/><span>2 weeks</span></div>
              <div class="chatbot_optionRow"><input type="radio" id="np2" name="notice"/><span>3 weeks</span></div>
              <div class="chatbot_optionRow"><input type="radio" id="np3" name="notice"/><span>1 month</span></div>
              <div class="chatbot_optionRow"><input type="radio" id="np4" name="notice"/><span>1.5 month</span></div>
              <div class="chatbot_optionRow"><input type="radio" id="np5" name="notice"/><span>2 months</span></div>
              <div class="chatbot_optionRow"><input type="radio" id="np6" name="notice"/><span>3 months</span></div>
            </div>
            <div class="chatbot_footer"><button class="chatbot_saveBtn" type="button">Save</button></div>
          </div>
        </body></html>
        """,
        # Stage 2 — a yes/no relocate question
        """
        <html><body>
          <div id="jobPage"><button id="cardSave">Save</button></div>
          <div class="chatbot-widget chatbot_open" role="dialog" id="drawer">
            <div class="chatbot_header">Recruiter's questions</div>
            <div class="chatbot_message">Are you willing to relocate to Hyderabad?</div>
            <div class="chatbot_options">
              <div class="chatbot_optionRow"><input type="radio" id="rl1" name="relocate"/><span>Yes</span></div>
              <div class="chatbot_optionRow"><input type="radio" id="rl2" name="relocate"/><span>No</span></div>
            </div>
            <div class="chatbot_footer"><button class="chatbot_saveBtn" type="button">Save</button></div>
          </div>
        </body></html>
        """,
        # Stage 3 — drawer closed, application submitted
        """
        <html><body>
          <div id="jobPage"><button id="cardSave">Save</button><span>Applied</span></div>
        </body></html>
        """,
    ]

    def __init__(self):
        self.stage = 0
        self.log: list[tuple] = []
        self.selected_inputs: dict[str, bool] = {}
        self._parse()

    def _parse(self):
        parser = etree.HTMLParser()
        self.tree = etree.fromstring(self.STAGES[self.stage], parser)

    def on_drawer_save(self):
        if self.stage < len(self.STAGES) - 1:
            self.stage += 1
            self.selected_inputs = {}
            self._parse()

    def root(self):
        return self.tree


class FakeDriver:
    def __init__(self, dom: FakeDom):
        self.dom = dom

    def _query(self, xpath):
        try:
            nodes = self.dom.root().xpath(xpath)
        except Exception:
            return []
        return [FakeElement(n, self.dom, is_input=(n.tag == "input"))
                for n in nodes if isinstance(n, etree._Element)]  # noqa: SLF001

    def find_element(self, by, xpath):
        els = self._query(xpath)
        if not els:
            raise RuntimeError(f"no match for {xpath}")
        return els[0]

    def find_elements(self, by, xpath):
        return self._query(xpath)

    def execute_script(self, script, *args):
        return ""


def test_end_to_end() -> None:
    print("\n=== B. fake-DOM end-to-end (EPAM reproduction) ===")
    dom = FakeDom()
    driver = FakeDriver(dom)

    # Option extraction sanity on the live fake drawer (stage 1).
    modal = driver.find_element("xpath", "//div[@role='dialog']")
    opts = Q._get_visible_options(modal, "What is your Notice Period?")
    check("extracted options from drawer", sorted(opts), sorted(EPAM_OPTIONS))
    check("question text extracted from drawer",
          Q._extract_question_text(driver, modal), "What is your Notice Period?")

    answered, unknown = Q.handle_recruiter_questionnaire(
        driver, work_location="Bengaluru", job_description="Java microservices",
        ai_client=None, ai_provider="gemini", use_ai=False, skip_alerts=True,
    )

    check("no unknown questions", unknown, [])
    check("two questions answered", len(answered), 2)

    by_q = {q: a for (q, a, _kind) in answered}
    check(
        "notice period answered with '1.5 month' (option, not '40')",
        by_q.get("What is your Notice Period?"),
        "1.5 month",
    )
    check(
        "relocate answered with 'Yes' (option, not raw 'yes')",
        by_q.get("Are you willing to relocate to Hyderabad?"),
        "Yes",
    )

    input_clicks = [e for e in dom.log if e[0] == "click-input"]
    check(
        "clicked the 1.5-month radio input (np4), not another",
        [(c[1], c[2]) for c in input_clicks],
        [("np4", "1.5 month"), ("rl1", "Yes")],
    )
    page_save_clicks = [e for e in dom.log if e[0] == "click" and e[1] == "button" and e[2] == "Save"]
    check(
        "clicked the drawer Save (advanced through 2 stages)",
        len(page_save_clicks), 2,
    )
    check(
        "card Save behind the drawer never clicked",
        any(c[1] == "cardSave" for c in dom.log), False,
    )
    check("flow reached final stage (drawer closed)", dom.stage, 2)


def test_selectors() -> None:
    print("\n=== C. selector regression ===")
    parser = etree.HTMLParser()

    walkin = etree.fromstring(
        "<html><body><div class='jd'><button id='cta'>I'm interested</button></div></body></html>", parser
    )
    matched = any(walkin.xpath(xp) for xp in S.APPLY_BUTTON)
    check("APPLY_BUTTON now matches walk-in 'I'm interested' button", matched, True)

    dialog = etree.fromstring(
        "<html><body><div role='dialog'><form><input type='text'/></form></div></body></html>", parser
    )
    matched = any(dialog.xpath(xp) for xp in S.FORM_CONTAINER)
    check("FORM_CONTAINER matches dialog-wrapped form", matched, True)

    plain = etree.fromstring(
        "<html><body><div><button id='cta'>Submit profile</button><button>Save</button></div></body></html>", parser
    )
    apply_now = etree.fromstring(
        "<html><body><button class='applyBtn'>Apply</button></div></body></html>", parser
    )
    check("APPLY_BUTTON still matches classic 'Apply' button", any(apply_now.xpath(xp) for xp in S.APPLY_BUTTON), True)
    check("APPLY_BUTTON does not match unrelated buttons", any(plain.xpath(xp) for xp in S.APPLY_BUTTON), False)


def test_native_select() -> None:
    print("\n=== D. native <select> dropdown question ===")
    stages = [
        """
        <html><body>
          <div class="chatbot-widget chatbot_open" role="dialog" id="drawer">
            <div class="chatbot_message">What is your total years of experience?</div>
            <select id="exp">
              <option value="">Select</option>
              <option value="1">0-1 year</option>
              <option value="2">1-3 years</option>
              <option value="3">3-5 years</option>
              <option value="4">5-7 years</option>
            </select>
            <div class="chatbot_footer"><button class="chatbot_saveBtn">Save</button></div>
          </div>
        </body></html>
        """,
        "<html><body><span>Applied</span></body></html>",
    ]

    selected: dict[str, str] = {}
    advanced = {"save": False, "stage": 0}
    tree_holder = {"tree": etree.fromstring(stages[0], etree.HTMLParser())}

    def on_save():
        advanced["save"] = True
        advanced["stage"] = 1
        tree_holder["tree"] = etree.fromstring(stages[1], etree.HTMLParser())

    class SelDriver(FakeDriver):
        def __init__(self):
            self.dom = types.SimpleNamespace(selected_inputs={}, log=[], on_drawer_save=on_save)

        def _query(self, xpath):
            return [FakeElement(n, self.dom, n.tag == "input")
                    for n in (tree_holder["tree"].xpath(xpath) or []) if isinstance(n, etree._Element)]  # noqa: SLF001

        def execute_script(self, script, *args):
            return ""

    # Patch Select so the real _select_native_option code path runs.
    class FakeSelect:
        def __init__(self, el):
            self.el = el

        @property
        def options(self):
            return self.el.find_elements("xpath", ".//option")

        def select_by_visible_text(self, text):
            selected["value"] = text

    real_select = Q.Select
    Q.Select = FakeSelect
    try:
        driver = SelDriver()
        answered, unknown = Q.handle_recruiter_questionnaire(
            driver, work_location="", use_ai=False, skip_alerts=True,
        )
    finally:
        Q.Select = real_select

    check("select question answered with '3-5 years'", selected.get("value"), "3-5 years")
    check("select question has no unknown", unknown, [])
    check("select flow answered one question", len(answered), 1)
    check("drawer Save clicked after selecting", advanced["save"], True)
    check("drawer closed after Save", advanced["stage"], 1)


def test_config_save_guard() -> None:
    print("\n=== E. config save guard (current_experience=0 regression) ===")
    from modules.config_manager import _normalize_updates, _coerce_numeric

    # The production bug: dashboard sent "" or null for a numeric field.
    out = _normalize_updates("search_naukri", {"current_experience": ""})
    check("empty current_experience is dropped", "current_experience" in out, False)
    out = _normalize_updates("search_naukri", {"current_experience": None})
    check("null current_experience is dropped", "current_experience" in out, False)
    out = _normalize_updates("search_naukri", {"current_experience": "abc"})
    check("garbage current_experience is dropped", "current_experience" in out, False)
    out = _normalize_updates("search_naukri", {"current_experience": "5"})
    check("numeric string is coerced", out.get("current_experience"), 5)
    out = _normalize_updates("search_naukri", {"current_experience": 5})
    check("real number passes through", out.get("current_experience"), 5)
    out = _normalize_updates("search_naukri", {"notice_period": 0})
    check("legitimate 0 is kept (notice_period can be 0)", out.get("notice_period"), 0)
    check("_coerce_numeric('') is None", _coerce_numeric(""), None)
    check("_coerce_numeric('40') is 40", _coerce_numeric("40"), 40)
    check("_coerce_numeric(True) is None (bool is not a count)", _coerce_numeric(True), None)
    # a non-numeric field must be untouched by the guard
    out = _normalize_updates("naukri_questions", {"willing_to_relocate": "Yes"})
    check("non-numeric fields unaffected", out.get("willing_to_relocate"), "Yes")


def test_retry_cap_logic() -> None:
    print("\n=== F. failed-job retry cap ===")
    from modules.jobs_logger import get_failed_job_counts
    import csv as _csv
    import tempfile
    import os as _os

    # Build a small failed-jobs CSV like the real one
    tmpdir = tempfile.mkdtemp()
    csv_path = _os.path.join(tmpdir, "failed.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = _csv.writer(f)
        w.writerow(["Job ID", "Platform", "Job Link", "Resume Tried", "Date listed",
                    "Date Tried", "Assumed Reason", "Stack Trace", "External Job link", "Screenshot Name"])
        w.writerow(["job-a", "Naukri"] + ["x"] * 8)
        w.writerow(["job-a", "Naukri"] + ["x"] * 8)
        w.writerow(["job-b", "Naukri"] + ["x"] * 8)
        w.writerow(["job-c", "LinkedIn"] + ["x"] * 8)
        w.writerow(["", "Naukri"] + ["x"] * 8)

    import modules.jobs_logger as jl
    saved = jl.failed_file_name
    jl.failed_file_name = csv_path
    try:
        counts = get_failed_job_counts("Naukri")
    finally:
        jl.failed_file_name = saved
    check("failed counts: job-a tried twice", counts.get("job-a"), 2)
    check("failed counts: job-b once", counts.get("job-b"), 1)
    check("failed counts: LinkedIn job excluded", "job-c" in counts, False)
    check("failed counts: blank id ignored", "" in counts, False)

    # The retry decision as implemented in runNaukriBot
    failed_counts = {"job-a": 2, "job-b": 1}
    session_failed_counts = {"job-b": 1}
    retry_limit = 2

    def should_retry(job_id: str) -> bool:
        total = failed_counts.get(job_id, 0) + session_failed_counts.get(job_id, 0)
        return not (retry_limit > 0 and total >= retry_limit)

    check("job-a (2 failures) is given up", should_retry("job-a"), False)
    check("job-b (1+1 failures) is given up", should_retry("job-b"), False)
    check("job-c (0 failures) is retried", should_retry("job-c"), True)


def test_unknown_question_log() -> None:
    print("\n=== G. unknown-question log dedupe + BOM ===")
    import tempfile
    import os as _os

    tmpdir = tempfile.mkdtemp()
    log_path = _os.path.join(tmpdir, "unknown.jsonl")
    saved_path = Q.UNKNOWN_LOG
    Q.UNKNOWN_LOG = Path(log_path)
    try:
        Q._log_unknown_question("What is your notice period?", ["15 days", "30 days"])
        Q._log_unknown_question("What is your notice period?", ["15 days", "30 days"])  # duplicate
        Q._log_unknown_question("Are you willing to relocate?", [])
        with open(log_path, "rb") as f:
            raw = f.read()
        check("log has no BOM", raw.startswith(b"{"), True)
        lines = [l for l in raw.decode("utf-8").splitlines() if l.strip()]
        check("duplicate question logged once", len(lines), 2)

        # BOM-tolerant read, as in app.py
        import json as _json
        with open(log_path, "a", encoding="utf-8") as f:
            pass
        entries = []
        with open(log_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip().lstrip("\ufeff")
                if line:
                    entries.append(_json.loads(line))
        check("all entries parse after utf-8-sig read", len(entries), 2)

        # simulate the shipped file that starts with a BOM
        with open(log_path, "wb") as f:
            f.write(b"\xef\xbb\xbf" + raw)
        entries = []
        with open(log_path, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip().lstrip("\ufeff")
                if line:
                    entries.append(_json.loads(line))
        check("BOM'd first line still parses", len(entries), 2)
    finally:
        Q.UNKNOWN_LOG = saved_path


def test_skill_mismatch_filter() -> None:
    print("\n=== H. skill-mismatch filter ===")
    import modules.naukri.skip_rules as sr
    import config.search_naukri as cfg

    saved_req, saved_poss = cfg.required_skills, cfg.possessed_skills
    try:
        cfg.required_skills = ["Angular", "React", "Vue"]
        cfg.possessed_skills = ["Angular", "TypeScript"]
        sr.required_skills = cfg.required_skills
        sr.possessed_skills = cfg.possessed_skills

        # JD mentions 2 watched skills, one missing -> skip with names
        skip, reason, msg = sr.should_skip_job("Acme", "We need React and Vue experience here",
                                               "2-4 years", set(), title="Frontend Dev")
        check("missing-skill JD is skipped", skip, True)
        check("reason is Skill mismatch", reason, "Skill mismatch")
        check("message names the missing skills", "React" in msg and "Vue" in msg, True)
        check("message does not name possessed skill", "Angular" not in msg, True)

        # JD mentions only one watched skill (incidental) -> no skill skip
        skip, reason, msg = sr.should_skip_job("Acme", "Our Angular team also uses Java, Spring, AWS",
                                               "2-4 years", set(), title="Dev")
        check("single incidental mention not rejected", skip, False)

        # JD mentions two watched skills, both possessed -> no skill skip
        skip, reason, msg = sr.should_skip_job("Acme", "Angular and TypeScript required for this role",
                                               "2-4 years", set(), title="Dev")
        check("all-possessed JD not rejected", skip, False)

        # filter disabled entirely
        cfg.required_skills = []
        sr.required_skills = []
        skip, reason, msg = sr.should_skip_job("Acme", "React and Vue required",
                                               "2-4 years", set(), title="Dev")
        check("empty required_skills disables filter", skip, False)

        # no description (job-card-only check) never triggers skill skip
        cfg.required_skills = ["React", "Vue"]
        sr.required_skills = cfg.required_skills
        skip, reason, msg = sr.should_skip_job("Acme", "", "2-4 years", set(), title="Dev")
        check("no description -> no skill skip", skip, False)
    finally:
        cfg.required_skills, cfg.possessed_skills = saved_req, saved_poss
        sr.required_skills, sr.possessed_skills = saved_req, saved_poss


def test_history_csvs() -> None:
    print("\n=== I. history CSVs (migration + genuine failures) ===")
    import tempfile
    import os as _os
    import csv as _csv
    import modules.jobs_logger as jl

    tmpdir = tempfile.mkdtemp()

    # --- old-format failed CSV (no Title/Company, with skip noise rows) ---
    failed_path = _os.path.join(tmpdir, "failed.csv")
    old_header = ["Job ID", "Platform", "Job Link", "Resume Tried", "Date listed",
                  "Date Tried", "Assumed Reason", "Stack Trace", "External Job link", "Screenshot Name"]
    with open(failed_path, "w", encoding="utf-8", newline="") as f:
        w = _csv.writer(f)
        w.writerow(old_header)
        w.writerow(["job-f1", "Naukri", "u1", "r", "d", "t", "Apply button not found", "st", "Pending", "s.png"])
        w.writerow(["job-s1", "Naukri", "u2", "N/A", "Unknown", "t", "Experience too high", "msg", "Skipped", "N/A"])  # old skip noise
        w.writerow(["job-s2", "Naukri", "u3", "N/A", "Unknown", "t", "Excluded title keyword", "msg", "Skipped", "N/A"])  # old skip noise
        w.writerow(["job-f2", "Naukri", "u4", "r", "d", "t", "Unanswered recruiter question", "st", "Pending", "s.png"])

    saved = jl.failed_file_name, jl.skipped_file_name
    jl.failed_file_name = failed_path
    jl.skipped_file_name = _os.path.join(tmpdir, "skipped.csv")
    try:
        counts = jl.get_failed_job_counts("Naukri")
        check("genuine failures counted (noise excluded)", counts, {"job-f1": 1, "job-f2": 1})

        # New-format header check after migration
        with open(failed_path, encoding="utf-8-sig", newline="") as f:
            header = next(_csv.reader(f))
        check("failed CSV migrated with Title/Company",
              "Title" in header and "Company" in header, True)

        # Row content preserved through migration
        with open(failed_path, encoding="utf-8-sig", newline="") as f:
            rows = list(_csv.DictReader(f))
        check("migration preserved job ids", {r["Job ID"] for r in rows}, {"job-f1", "job-s1", "job-s2", "job-f2"})
        check("migration preserved reasons", rows[0]["Assumed Reason"], "Apply button not found")

        # failed_job writes Title/Company now
        jl.failed_job("Naukri", "job-f3", "u5", "r", "Unknown",
                      "Submit failed", "err", "Pending", "s.png",
                      title="Dev", company="Acme")
        with open(failed_path, encoding="utf-8-sig", newline="") as f:
            rows = list(_csv.DictReader(f))
        last = rows[-1]
        check("new failed row has Title", last["Title"], "Dev")
        check("new failed row has Company", last["Company"], "Acme")

        # skipped_job writes a full reason row
        jl.skipped_job("Naukri", "job-k1", "Python Dev", "S", "Bengaluru",
                       "3-5 years", "Full Stack", "Excluded title keyword",
                       'Excluded title keyword "python"', "u6")
        with open(jl.skipped_file_name, encoding="utf-8-sig", newline="") as f:
            rows = list(_csv.DictReader(f))
        check("skipped CSV row written with reason", rows[0]["Reason"], "Excluded title keyword")
        check("skipped CSV row has detail", "python" in rows[0]["Detail"], True)
        check("skipped CSV row has company", rows[0]["Company"], "S")
    finally:
        jl.failed_file_name, jl.skipped_file_name = saved


def test_ascii_safe_logger() -> None:
    print("\n=== J. charmap-proof print_lg ===")
    # Simulate a cp1252-style console: encoding that cannot represent unicode.
    import io
    import modules.helpers as helpers

    captured = io.StringIO()
    real_stdout, sys.stdout = sys.stdout, captured
    try:
        # Force the UnicodeEncodeError path that crashed on Windows.
        class Narrow(io.TextIOWrapper):
            def write(self, s):
                return super().write(s)

        # Directly exercise the fallback helper
        safe = helpers._console_safe('Q: "notice period" -> 40 [ok]')
        check("ASCII-safe fallback keeps ASCII text", safe, 'Q: "notice period" -> 40 [ok]')
        safe2 = helpers._console_safe("Rupee \u20b9 and arrow \u2192")
        check("non-ASCII replaced, not raised", safe2.startswith("Rupee "), True)
        check("replacement char present", "?" in safe2, True)
    finally:
        sys.stdout = real_stdout


def test_ai_answers_log() -> None:
    print("\n=== K. AI answers review log ===")
    import tempfile
    import json as _json
    import modules.naukri.ai_answers_log as aal

    tmpdir = tempfile.mkdtemp()
    log_path = Path(tmpdir) / "ai.jsonl"
    saved = aal.AI_ANSWERS_LOG
    aal.AI_ANSWERS_LOG = log_path
    try:
        aal.record_ai_answer("Are you ok with 6-day weeks?", "Yes", ["Yes", "No"])
        aal.record_ai_answer("Are you ok with 6-day weeks?", "Yes")  # repeat occurrence
        aal.record_ai_answer("Willing to relocate?", "No")
        aal.record_ai_answer("", "x")  # empty question ignored
        aal.record_ai_answer("Q", "")  # empty answer ignored

        answers = aal.get_ai_answers()
        check("deduped to 2 questions", len(answers), 2)
        by_q = {a["question"]: a for a in answers}
        check("occurrences counted", by_q["Are you ok with 6-day weeks?"]["count"], 2)
        check("defaults to pending feedback", by_q["Willing to relocate?"]["feedback"], "pending")

        ok = aal.set_feedback("Willing to relocate?", "correct")
        check("feedback write reports change", ok, True)
        check("feedback persisted", aal.get_ai_answers() and {a["question"]: a for a in aal.get_ai_answers()}["Willing to relocate?"]["feedback"], "correct")

        check("bad feedback value rejected", aal.set_feedback("Willing to relocate?", "maybe"), False)

        aal.set_keyword("Willing to relocate?", "relocate")
        kw = {a["question"]: a for a in aal.get_ai_answers()}["Willing to relocate?"]
        check("keyword pair remembered", kw["keyword"], "relocate")

        # decided feedback survives a new occurrence
        aal.record_ai_answer("Willing to relocate?", "No")
        kw = {a["question"]: a for a in aal.get_ai_answers()}["Willing to relocate?"]
        check("decided feedback not reset by new occurrence", kw["feedback"], "correct")
        check("count grew to 2", kw["count"], 2)
    finally:
        aal.AI_ANSWERS_LOG = saved

    # seed_from_log_txt parses the Gemini ask/answer pairs from log.txt
    log_txt = Path(tmpdir) / "log.txt"
    log_txt.write_text(
        "Navigating to search\n"
        "Asking Gemini to answer Naukri question: No, I will not attend\n"
        "Calling Gemini API (models/gemini-3.6-flash)...\n"
        'Gemini answered: "Yes, I will attend"\n'
        "Unrelated line\n"
        "Asking Gemini to answer Naukri question: Are you a team player?\n"
        'Gemini answered: "Yes"\n',
        encoding="utf-8",
    )
    aal.AI_ANSWERS_LOG = log_path.parent / "ai2.jsonl"
    try:
        seeded = aal.seed_from_log_txt(log_txt)
        check("seeded 2 questions from log.txt", seeded, 2)
        seeded_answers = {a["question"]: a for a in aal.get_ai_answers()}
        check("seeded answer text", seeded_answers.get("No, I will not attend", {}).get("answer"), "Yes, I will attend")
        check("seed counts occurrences", seeded_answers.get("Are you a team player?", {}).get("count"), 1)

        # second seed is a no-op (JSONL already has content)
        check("re-seed skipped", aal.seed_from_log_txt(log_txt), 0)
    finally:
        aal.AI_ANSWERS_LOG = saved


def test_unknown_questions_marking() -> None:
    print("\n=== L. unknown-question answered marking (the 'still pending' fix) ===")
    import json as _json
    import app as flask_app

    client = flask_app.app.test_client()

    # Snapshot the real config/profile answer dicts so the test's POST restores
    # them afterwards (it writes through to config/naukri_questions.py and the
    # active profile file).
    from modules.config_manager import _read_module_values
    saved_answers = dict(_read_module_values("config.naukri_questions", ["custom_naukri_answers"]).get("custom_naukri_answers", {}))
    saved_log = flask_app.UNKNOWN_QUESTIONS_LOG
    import tempfile
    tmpdir = tempfile.mkdtemp()
    log_path = Path(tmpdir) / "uq.jsonl"
    log_path.write_text(
        _json.dumps({"question": "Do you have a laptop?", "options": ["yes", "no"], "time": "2026-11-08T09:00:00"}) + "\n"
        + _json.dumps({"question": "Are you a night owl?", "options": [], "time": "2026-11-08T09:01:00"}) + "\n",
        encoding="utf-8",
    )
    flask_app.UNKNOWN_QUESTIONS_LOG = log_path
    try:
        resp = client.post("/api/naukri/answer-questions", json={"answers": {"laptop": "yes"}})
        body = resp.get_json()
        check("save returns 200", resp.status_code, 200)
        check("row marked answered", body.get("questions_marked_answered"), 1)

        # GET now shows it as answered with the value
        resp = client.get("/api/naukri/unknown-questions")
        qs = {q["question"]: q for q in resp.get_json()["questions"]}
        check("laptop question now answered", qs["Do you have a laptop?"]["status"], "answered")
        check("saved answer visible", qs["Do you have a laptop?"]["existing_answer"], "yes")
        check("other question still pending", qs["Are you a night owl?"]["status"], "new")
    finally:
        flask_app.UNKNOWN_QUESTIONS_LOG = saved_log
        # Restore the real answer dicts (config file + module state).
        from modules.config_manager import save_config as _save
        _save({"naukri_questions": {"custom_naukri_answers": saved_answers}})
        import config.naukri_questions as _nq
        import importlib as _il
        _il.reload(_nq)
        try:
            # update_profile deep-merges, which cannot REMOVE the test's key;
            # write the profile file directly to restore the snapshot exactly.
            import json as _j
            from pathlib import Path as _P
            from modules.profile_manager import _profile_path as _pp
            _p = _pp("rahul")
            if _p.exists():
                _data = _j.loads(_p.read_text(encoding="utf-8"))
                _data.setdefault("qa", {})["custom_naukri_answers"] = saved_answers
                _p.write_text(_j.dumps(_data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


def test_naukri_search_link() -> None:
    print("\n=== M. expired-link fallback URL ===")
    import app as flask_app

    link = flask_app._naukri_search_link("Angular Developer")
    check("spaces become dashes", link, "https://www.naukri.com/angular-developer-jobs")
    link2 = flask_app._naukri_search_link("")
    check("empty title still yields a search", link2.endswith("-jobs"), True)
    check("url-encoded when needed", "%20" in flask_app._naukri_search_link("Dev (Remote)") or "(" not in flask_app._naukri_search_link("Dev (Remote)"), True)


def main() -> None:
    test_pure_logic()
    test_end_to_end()
    test_selectors()
    test_native_select()
    test_config_save_guard()
    test_retry_cap_logic()
    test_unknown_question_log()
    test_skill_mismatch_filter()
    test_history_csvs()
    test_ascii_safe_logger()
    test_ai_answers_log()
    test_unknown_questions_marking()
    test_naukri_search_link()
    failed = [r for r in RESULTS if not r[1]]
    print(f"\n{'='*60}\nTOTAL: {len(RESULTS)}  passed: {len(RESULTS)-len(failed)}  failed: {len(failed)}")
    if failed:
        for name, _, info in failed:
            print("  FAILED:", name, info)
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
