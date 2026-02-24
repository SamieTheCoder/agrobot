import re
import os
import time
import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, StaleElementReferenceException,
    NoSuchElementException, ElementNotInteractableException
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Required columns for validation ──────────────────────────────────────────
REQUIRED_COLUMNS = [
    'ProductName', 'ProductCIBCode', 'ProductRegDate',
    'InsecticideRegistrationValidUpto', 'ManufacturerName',
    'PrincipalCerificateNo', 'PrincipleCertificateIssueDate',
    'PrincipleCertificateValidUpto', 'RegistrationNo', 'Password'
]

# ── Web field ID → Excel column name ─────────────────────────────────────────
FIELD_MAPPINGS = {
    'ProductName':             'ProductName',
    'ProductCIBCode':          'ProductCIBCode',
    'ProductRegDate':          'ProductRegDate',
    'ProductImpterManurName':  'ManufacturerName',
    'PrincipleCertNo':         'PrincipalCerificateNo',
    'PrincipleCertIssueDate':  'PrincipleCertificateIssueDate',
    'PrincipleCertValidUpto':  'PrincipleCertificateValidUpto',
    'ProductValidityDate':     'InsecticideRegistrationValidUpto',
}


def strip_html(value: str) -> str:
    """Strip HTML tags — handles <span> copy-paste artifacts from web."""
    if not isinstance(value, str):
        return value
    return re.sub(r'<[^>]+>', '', value).strip()


def validate_excel(file_path: str):
    """
    Validate file and extract credentials.
    Returns: (df, reg_no, password, error_message)
    On success: error_message is None
    On failure: df/reg_no/password are None
    """
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return None, None, None, f"Cannot read Excel file: {e}"

    if df.empty:
        return None, None, None, "Excel file has no data rows."

    # Check all required columns exist
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        return None, None, None, f"Missing required columns:\n" + "\n".join(f"  • {c}" for c in missing)

    # Strip HTML from all string columns upfront
    for col in df.columns:
        df[col] = df[col].apply(lambda x: strip_html(x) if isinstance(x, str) else x)

    # Extract credentials from first row that has them
    reg_no, password = None, None
    for _, row in df.iterrows():
        if pd.notna(row.get('RegistrationNo')) and str(row['RegistrationNo']).strip() not in ('', 'nan'):
            reg_no = str(row['RegistrationNo']).strip()
        if pd.notna(row.get('Password')) and str(row['Password']).strip() not in ('', 'nan'):
            password = str(row['Password']).strip()
        if reg_no and password:
            break

    if not reg_no:
        return None, None, None, "RegistrationNo not found in any row."
    if not password:
        return None, None, None, "Password not found in any row."

    return df, reg_no, password, None


def get_chrome_driver() -> webdriver.Chrome:
    """Headless Chrome — works in Docker on Oracle server."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-images")
    options.page_load_strategy = 'eager'
    return webdriver.Chrome(options=options)


class RobustElementHandler:
    def __init__(self, driver, default_timeout=30):
        self.driver = driver
        self.default_timeout = default_timeout

    def safe_find_element(self, locator, timeout=None, retries=3):
        timeout = timeout or self.default_timeout
        for attempt in range(retries):
            try:
                return WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located(locator)
                )
            except (TimeoutException, NoSuchElementException):
                if attempt == retries - 1:
                    raise
                time.sleep(1)

    def safe_click(self, locator, timeout=None, retries=3):
        timeout = timeout or self.default_timeout
        for attempt in range(retries):
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable(locator)
                )
                el.click()
                return True
            except (StaleElementReferenceException, ElementNotInteractableException, TimeoutException):
                if attempt == retries - 1:
                    raise
                time.sleep(1)

    def safe_send_keys(self, locator, text, clear_first=True, timeout=None, retries=3):
        timeout = timeout or self.default_timeout
        for attempt in range(retries):
            try:
                el = WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable(locator)
                )
                if clear_first:
                    el.clear()
                    time.sleep(0.1)
                el.send_keys(str(text))
                return True
            except (StaleElementReferenceException, ElementNotInteractableException, TimeoutException):
                if attempt == retries - 1:
                    raise
                time.sleep(1)

    def wait_for_page_load(self, timeout=30):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(0.5)
            return True
        except TimeoutException:
            logger.warning("Page load timeout")
            return False


def process_file(file_path: str, progress_callback=None):
    """
    Run full automation for one Excel file.

    progress_callback(current: int, total: int, product_name: str)
        Called after each row attempt (success or fail).

    Returns:
        (success_count: int, error_list: list[str])

    Raises:
        ValueError  — validation failed (before browser opens)
        Exception   — login/page failure
    """
    df, reg_no, password, error = validate_excel(file_path)
    if error:
        raise ValueError(error)

    total_rows = len(df)
    success_count = 0
    error_list = []

    driver = get_chrome_driver()
    handler = RobustElementHandler(driver)

    try:
        # ── Navigate & Login ──────────────────────────────────────────────────
        driver.get("https://onlinedbtagriservice.bihar.gov.in/Licence/LicenceForm/ProductDetails")
        handler.wait_for_page_load()

        handler.safe_find_element((By.ID, "loginForm"))
        handler.safe_send_keys((By.ID, "RegistrationNo"), reg_no)
        handler.safe_send_keys((By.ID, "Password"), password)
        handler.safe_click((By.CSS_SELECTOR, "#loginForm > form > button:nth-child(4)"))

        # ── Wait for post-login form ──────────────────────────────────────────
        handler.wait_for_page_load()
        handler.safe_find_element((By.ID, 'ProductCIBCode'), timeout=45)

        add_btn = (By.CSS_SELECTOR, "div.col-sm-8 button.btn.btn-primary.btn-block")

        # ── Process each row ──────────────────────────────────────────────────
        for idx, row in df.iterrows():
            product_name = str(row.get('ProductName', f'Row {idx + 1}'))
            try:
                for web_field, excel_col in FIELD_MAPPINGS.items():
                    val = row.get(excel_col)
                    field_value = str(val) if pd.notna(val) else ""
                    if field_value and field_value.lower() != 'nan':
                        handler.safe_send_keys((By.ID, web_field), field_value, timeout=10)

                handler.safe_click(add_btn, timeout=10)
                time.sleep(0.4)
                success_count += 1

            except Exception as row_err:
                msg = f"Row {idx + 1} ({product_name}): {row_err}"
                error_list.append(msg)
                logger.error(msg)

            finally:
                if progress_callback:
                    progress_callback(idx + 1, total_rows, product_name)

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return success_count, error_list
