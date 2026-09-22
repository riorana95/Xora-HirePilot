'''
Develop by Rana Rahul

Auto LinkedIn Job Applier
'''

import os

from modules.helpers import get_bot_profile_directory, make_directories
from config.settings import run_in_background, stealth_mode, disable_extensions, safe_mode, file_name, failed_file_name, logs_folder_path, generated_resume_path
from config.questions import default_resume_path
if stealth_mode:
    import undetected_chromedriver as uc
else:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from modules.helpers import critical_error_log, print_lg
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException

options = None
driver = None
actions = None
wait = None


def _apply_chrome_options(chrome_options) -> None:
    if run_in_background:
        chrome_options.add_argument("--headless=new")
    if disable_extensions:
        chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--no-default-browser-check")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--remote-debugging-port=0")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    # Anti-detection for headless mode
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    if run_in_background:
        chrome_options.add_argument("--no-sandbox")


def _clear_chrome_profile_lock(profile_dir: str) -> None:
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        path = os.path.join(profile_dir, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def createChromeSession(is_retry: bool = False):
    make_directories([
        file_name, failed_file_name, logs_folder_path + "/screenshots",
        logs_folder_path + "/screenshots/naukri", default_resume_path, generated_resume_path + "/temp",
    ])

    chrome_options = uc.ChromeOptions() if stealth_mode else Options()
    _apply_chrome_options(chrome_options)

    print_lg("IF YOU HAVE MORE THAN 10 TABS OPENED, PLEASE CLOSE OR BOOKMARK THEM! Or it's highly likely that application will just open browser and not do anything!")

    # Always use a dedicated bot profile — avoids crash when your normal Chrome is open
    profile_dir = get_bot_profile_directory()
    if is_retry:
        profile_dir = profile_dir + "-retry"
    os.makedirs(profile_dir, exist_ok=True)
    _clear_chrome_profile_lock(profile_dir)
    if is_retry or safe_mode:
        print_lg(f"Using dedicated bot profile: {profile_dir}")
    else:
        print_lg(f"Using dedicated bot profile (log in once here — Google/Naukri session is saved): {profile_dir}")
    chrome_options.add_argument(f"--user-data-dir={profile_dir}")

    if stealth_mode:
        print_lg("Downloading Chrome Driver... This may take some time. Undetected mode requires download every run!")
        web_driver = uc.Chrome(options=chrome_options)
    else:
        web_driver = webdriver.Chrome(options=chrome_options)

    web_driver.maximize_window()
    web_wait = WebDriverWait(web_driver, 10)
    web_actions = ActionChains(web_driver)
    return chrome_options, web_driver, web_actions, web_wait


def init_chrome_session(force: bool = False) -> None:
    '''Create Chrome session lazily (call from bot main(), not at Flask import).'''
    global options, driver, actions, wait
    if driver is not None and not force:
        try:
            _ = driver.current_url
            return
        except WebDriverException:
            driver = None

    try:
        options, driver, actions, wait = createChromeSession()
    except SessionNotCreatedException as e:
        critical_error_log("Failed to create Chrome Session, retrying", e)
        options, driver, actions, wait = createChromeSession(True)
    except Exception as e:
        msg = (
            "Chrome failed to start. Try:\n"
            "1. Close all Chrome windows\n"
            "2. Set safe_mode = True in config/settings.py\n"
            "3. Update Google Chrome and chromedriver"
        )
        if isinstance(e, TimeoutError):
            msg = "Couldn't download Chrome-driver. Set stealth_mode = False in config!"
        print_lg(msg)
        critical_error_log("In Opening Chrome", e)
        from pyautogui import alert
        alert(msg, "Error in opening chrome")
        raise
