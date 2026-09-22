'''
Develop by Rana Rahul

Naukri DOM helper utilities.
'''

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from modules.helpers import print_lg


def find_first(driver: WebDriver, xpaths: list[str], timeout: float = 5.0, parent: WebElement | None = None) -> WebElement | None:
    root = parent if parent else driver
    for xpath in xpaths:
        try:
            if parent:
                el = root.find_element(By.XPATH, xpath)
                if el.is_displayed():
                    return el
            else:
                el = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                if el.is_displayed():
                    return el
        except Exception:
            continue
    return None


def find_all(driver: WebDriver, xpaths: list[str], parent: WebElement | None = None) -> list[WebElement]:
    root = parent if parent else driver
    for xpath in xpaths:
        try:
            elements = root.find_elements(By.XPATH, xpath)
            if elements:
                return elements
        except Exception:
            continue
    return []


def find_child_text(card: WebElement, xpaths: list[str], default: str = "Unknown") -> str:
    for xpath in xpaths:
        try:
            el = card.find_element(By.XPATH, xpath)
            text = el.text.strip()
            if text:
                return text
        except Exception:
            continue
    return default


def find_child_attr(card: WebElement, xpaths: list[str], attr: str = "href", default: str = "") -> str:
    for xpath in xpaths:
        try:
            el = card.find_element(By.XPATH, xpath)
            value = el.get_attribute(attr)
            if value:
                return value
        except Exception:
            continue
    return default


def click_first(driver: WebDriver, xpaths: list[str], timeout: float = 5.0) -> bool:
    el = find_first(driver, xpaths, timeout)
    if el:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            return True
        except Exception as e:
            print_lg(f"Click failed: {e}")
    return False
