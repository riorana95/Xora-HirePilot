'''
Develop by Rana Rahul

Naukri login — email/password auto-login with headless support.
'''

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.secrets import username, password
from modules.helpers import is_headless, manual_login_retry, print_lg, buffer
from modules.naukri.dom_helpers import find_first, click_first
from modules.naukri import selectors as S


def is_logged_in_naukri(driver: WebDriver) -> bool:
    try:
        if "nlogin" in driver.current_url.lower() and "login" in driver.current_url.lower():
            return False
        for xpath in S.LOGGED_IN_INDICATORS:
            try:
                el = driver.find_element(By.XPATH, xpath)
                if el.is_displayed():
                    return True
            except Exception:
                continue
        if "mnjuser" in driver.current_url or "homepage" in driver.current_url:
            return True
        login_el = find_first(driver, S.LOGIN_BUTTON, timeout=2)
        return login_el is None
    except Exception:
        return False


def _try_email_password_login(driver: WebDriver) -> bool:
    '''Attempt to login with email and password from config/secrets.py.'''
    if not username or not password:
        print_lg("No email/password configured in config/secrets.py. Skipping email login.")
        return False

    try:
        # Find and fill email
        email_el = find_first(driver, S.EMAIL_INPUT, timeout=5)
        if not email_el:
            print_lg("Email input field not found on login page.")
            return False
        email_el.clear()
        email_el.send_keys(username)
        print_lg(f"Entered email: {username}")
        buffer(1)

        # Find and fill password
        pass_el = find_first(driver, S.PASSWORD_INPUT, timeout=3)
        if not pass_el:
            print_lg("Password input field not found on login page.")
            return False
        pass_el.clear()
        pass_el.send_keys(password)
        print_lg("Entered password.")
        buffer(1)

        # Click login button
        if click_first(driver, S.LOGIN_SUBMIT, timeout=3):
            print_lg("Clicked Login button. Waiting for login to complete...")
            buffer(5)
            return is_logged_in_naukri(driver)
        else:
            print_lg("Login submit button not found.")
            return False

    except Exception as e:
        print_lg(f"Email/password login failed: {e}")
        return False


def _try_google_sign_in(driver: WebDriver) -> None:
    clicked = click_first(driver, S.GOOGLE_SIGN_IN, timeout=5)
    if clicked:
        print_lg("Clicked Google sign-in. Complete authentication in the browser if prompted.")
        buffer(3)
        return
    if is_headless():
        print_lg("Google sign-in button not found in headless mode.")
    else:
        print_lg("Please sign in to Naukri using Google in the browser window.")


def login_naukri(driver: WebDriver, skip_alerts: bool = False) -> None:
    driver.get(S.HOME_URL)
    buffer(2)
    if is_logged_in_naukri(driver):
        print_lg("Already logged in to Naukri.")
        return

    driver.get(S.LOGIN_URL)
    buffer(3)
    if is_logged_in_naukri(driver):
        print_lg("Logged in to Naukri after redirect.")
        return

    # Try email/password login first (works in headless)
    if _try_email_password_login(driver):
        print_lg("Naukri login successful via email/password!")
        return

    # Fall back to Google sign-in
    _try_google_sign_in(driver)
    manual_login_retry(lambda: is_logged_in_naukri(driver), limit=3)

    if is_logged_in_naukri(driver):
        print_lg("Naukri login successful!")
    else:
        print_lg("Naukri login could not be confirmed. Continuing anyway — apply may fail.")
