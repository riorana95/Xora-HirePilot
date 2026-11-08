'''Integration-style check: simulate the runNaukriBot job-loop decision logic
(pagination guard + retry cap + skip dedupe) against a scripted sequence of
search pages, using the real runNaukriBot module with stubbed browser/Chrome.

Reproduces the production pathology from the shipped logs:
  - the same page served forever (pagination stuck) -> old bot re-scanned it
    endlessly;
  - a job that always fails -> old bot retried it 73 times;
  - skipped jobs -> old bot wrote a CSV row per skip per cycle.
'''

import sys
import types
from pathlib import Path

PROJECT = str(Path(__file__).resolve().parent.parent)
sys.path.insert(0, PROJECT)


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
    mod("selenium.common")
    mod("selenium.common.exceptions", SessionNotCreatedException=type("E", (Exception,), {}), WebDriverException=type("E", (Exception,), {}))
    mod("selenium.webdriver")
    mod("selenium.webdriver.common")
    mod("selenium.webdriver.common.by", By=_By)
    mod("selenium.webdriver.common.action_chains", ActionChains=object)
    mod("selenium.webdriver.common.keys", Keys=object)
    mod("selenium.webdriver.remote")
    mod("selenium.webdriver.remote.webdriver", WebDriver=object)
    mod("selenium.webdriver.remote.webelement", WebElement=object)
    mod("selenium.webdriver.chrome")
    mod("selenium.webdriver.chrome.options", Options=object)
    mod("selenium.webdriver.chrome.service", Service=object)
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
            return lambda driver: driver.find_element(by, xp)
    mod("selenium.webdriver.support.ui", Select=object, WebDriverWait=_Wait)
    ec = mod("selenium.webdriver.support.expected_conditions", EC=_EC)
    sys.modules["selenium.webdriver.support"].expected_conditions = ec
    pyautogui = mod("pyautogui")
    pyautogui.alert = lambda *a, **k: None
    pyautogui.confirm = lambda *a, **k: True
    pyautogui.prompt = lambda *a, **k: None
    mod("undetected_chromedriver")
    # Stub the whole AI layer: runNaukriBot imports these at module load when
    # use_AI is on, and we only test the job-loop logic, not the AI plumbing.
    mod("openai", OpenAI=object)
    mod("modules.ai.openaiConnections",
        ai_create_openai_client=lambda *a, **k: None,
        ai_extract_skills=lambda *a, **k: "",
        ai_close_openai_client=lambda *a, **k: None)
    mod("modules.ai.deepseekConnections",
        deepseek_create_client=lambda *a, **k: None,
        deepseek_extract_skills=lambda *a, **k: "")
    mod("modules.ai.geminiConnections",
        gemini_create_client=lambda *a, **k: None,
        gemini_extract_skills=lambda *a, **k: "")


_install_stubs()

# Heavyweight imports the bot pulls in at module load: stub them before import
sys.modules["selenium.webdriver.support.ui"].Select = object

import runNaukriBot as BOT  # noqa: E402

BOT.buffer = lambda *a, **k: None
BOT.print_lg = lambda *a, **k: None

RESULTS = []


def check(name, got, expected):
    ok = got == expected
    RESULTS.append((name, ok))
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  -> got={got!r} expected={expected!r}"))


# --------------------------------------------------------------------------- #
# Scripted world                                                               #
# --------------------------------------------------------------------------- #
class FakeJob:
    def __init__(self, job_id, title, company, exp="3-5 years"):
        self.job_id, self.title, self.company = job_id, title, company
        self.location, self.experience, self.salary = "Bengaluru", exp, ""
        self.job_link = f"https://www.naukri.com/{job_id}"


PAGE_1 = [FakeJob("j-always-fails", "Fail", "F"), FakeJob("j-succeeds", "OK", "O")]
PAGE_2 = [FakeJob("j-skip", "Python Dev", "S")]          # skipped by title keyword
PAGE_STUCK = PAGE_1                                       # pagination stops moving

# The page sequence served to the bot: 1, 2, then the same page forever.
PAGES = [PAGE_1, PAGE_2] + [PAGE_STUCK] * 10

state = {
    "page_idx": 0,
    "ai_calls": 0,
    "fail_csv_rows": [],
    "skip_log_calls": [],
    "skip_csv_rows": [],
    "success_keys": set(),
}


class FakeDriver:
    current_url = "https://www.naukri.com/search"
    current_window_handle = "w"

    def get(self, url):
        pass


class FakeChrome:
    driver = FakeDriver()


BOT.chrome = FakeChrome
BOT.critical_error_log = lambda *a, **k: None
BOT.navigate_to_search = lambda *a, **k: None
BOT.apply_naukri_filters = lambda *a, **k: None
BOT.log_search = lambda *a, **k: None
BOT.is_logged_in_naukri = lambda *a, **k: True
BOT.login_naukri = lambda *a, **k: None
BOT.get_job_listings = lambda driver: PAGES[state["page_idx"]]


def _advance_page(driver):
    state["page_idx"] += 1
    return True


BOT.go_to_next_page = _advance_page
BOT.return_to_search_results = lambda driver, url: None
BOT.get_job_description = lambda driver: "Some job description text"
BOT.max_applications_per_search = 50
BOT.failed_job_retry_limit = 2
BOT.randomize_search_order = False
BOT.search_locations = ["Bengaluru"]
BOT.click_gap = 0
BOT.randomly_answered_questions = set()


def fake_apply(driver, work_location, description, **kwargs):
    class R:
        success = False
        apply_type = "naukri"
        error = "Apply button not found"
        application_link = "Pending"
        resume = "Pending"
        questions = set()
        unknown_questions = []
    return R()


BOT.apply_from_detail_page = fake_apply


def fake_screenshot(driver, platform, job_id, failed_at):
    return f"{job_id}.png"


BOT.screenshot = fake_screenshot
BOT.failed_job = lambda *a, **k: state["fail_csv_rows"].append(a[1])
BOT.skipped_job = lambda *a, **k: state["skip_csv_rows"].append(a[1])
BOT.log_failed = lambda jid, *a, **k: None
BOT.log_skipped = lambda jid, *a, **k: state["skip_log_calls"].append(jid)
BOT.submitted_job = lambda *a, **k: None
BOT.log_applied = lambda *a, **k: None
BOT.get_applied_job_keys = lambda platform=None: set()
BOT.get_failed_job_counts = lambda platform=None: state["fail_csv_rows_by_id"]()


def _counts_by_id():
    counts = {}
    for jid in state["fail_csv_rows"]:
        counts[jid] = counts.get(jid, 0) + 1
    return counts


state["fail_csv_rows_by_id"] = _counts_by_id


class FakeSkills:
    pass


BOT._extract_skills = lambda desc: (state.__setitem__("ai_calls", state["ai_calls"] + 1) or "skills")


# one successful job to exercise the success path + post-success AI extraction
def fake_apply_mixed(driver, work_location, description, **kwargs):
    class R:
        success = True
        apply_type = "naukri"
        error = ""
        application_link = "https://www.naukri.com/applied"
        resume = "resume.pdf"
        questions = {("What is your Notice Period?", "1.5 month", "checkbox")}
        unknown_questions = []
    return R()


# ---- run the loop ----
BOT.apply_to_naukri_jobs(["Full Stack"], skip_alerts=True)

check("pagination loop guard stopped the stuck-page rescan",
      state["page_idx"] <= 3, True)
check("always-failing job attempted at most retry_limit times",
      _counts_by_id().get("j-always-fails", 0) <= BOT.failed_job_retry_limit, True)
check("skipped job logged to activity log once, not per rescan",
      len(state["skip_log_calls"]), 1)
check("skipped job persisted to skipped-jobs CSV once (with reason)",
      len(state["skip_csv_rows"]), 1)
check("no AI skill-extraction call was wasted on failed/skipped jobs",
      state["ai_calls"], 0)

# ---- second run: persistent failure memory ----
state["fail_csv_rows_by_id"] = _counts_by_id  # as if the CSV now holds history
BOT.get_failed_job_counts = lambda platform=None: _counts_by_id()
state["page_idx"] = 0
BOT.apply_to_naukri_jobs(["Full Stack"], skip_alerts=True)
check("after persistence, the failed job is not attempted again",
      _counts_by_id().get("j-always-fails", 0) <= BOT.failed_job_retry_limit, True)

# ---- third run: success path with a fresh job (AI extraction after apply) ----
BOT.apply_from_detail_page = fake_apply_mixed
state["page_idx"] = 0
state["fail_csv_rows"] = []  # fresh history so the retry cap does not block it
BOT.get_job_listings = lambda driver: [FakeJob("j-new", "Fresh Role", "N")]
BOT.apply_to_naukri_jobs(["Full Stack"], skip_alerts=True)
check("successful apply triggers exactly one AI extraction",
      state["ai_calls"], 1)

failed = [n for n, ok in RESULTS if not ok]
print(f"\nTOTAL: {len(RESULTS)}  passed: {len(RESULTS)-len(failed)}  failed: {len(failed)}")
sys.exit(1 if failed else 0)
