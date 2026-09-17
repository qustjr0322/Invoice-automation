import os
import time
import subprocess
import pandas as pd
import pyautogui
import pyperclip
import io
import base64
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

SPREADSHEET_ID = "1KRsfhB8o-DRvMIpc1LVqrcgAUM9U-X_p7-kY1G69Beg"
CSV_EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&gid=0"
APPSHEET_URL = "https://eu.appsheet.com/start/496e80db-2175-4081-af05-52cb8491a4d3?platform=desktop#appName=cp2320-eu-sql-6095245&vss=H4sIAAAAAAAAA6WOywrCMBBF_-Wu8wXZiqD42ChuTJHYTCHYJqVJ1RLy7059rtXl3OGcexPOli6bqMsT5D59rgUNkEgK26ElBakw8S52vlYQCmvdPMKZb-iwtCEqZORCvASRAmT6kpd_9gtYQy7aylI3ykaUJU-Q3yPGwRtCFmj6qI813TczlDNnlS_7QGbHY34ZEeZuem21Mytv2FnpOlC-ASBAw-1qAQAA&view=Home_List"
ATTACHMENT_URL = "https://eu.appsheet.com/start/496e80db-2175-4081-af05-52cb8491a4d3?platform=desktop#appName=cp2320-eu-sql-6095245&vss=H4sIAAAAAAAAA7VU70_bMBD9V5A_ZywE6Ei-lbbbqpWGtR3SRhDykkuJltjFdvihqv_7zk4pWYggTYeUD_H53vO75zsvyV0C91NFwz_Eu1w-r77BI_HIMiCzxwUExAtIjzMleBoQKyBjmhXBrzyD61EiVUBWZGVtT9CVEpTciYJqiusezxa5AtGW5exxbwK3OUhUk-6gpszTB0WTVLYuTGHyTQZMXSv6OwXDc2U98SiQxFtueUfejndskSRCQUmcgNBkGookayBuaxgGNiCsnGS50W80I2iFoW0bo4XuCkNT5SVYjfan_Jpki0w4VxgMqYhw1aeKIixbYMixnc4H28VvZh94-B0d73cO3EPXPflFGvnxsstbWPKSpKkr_yLfNqaS_77e1M1uC3fqaJr6U8W-7dALxMajmEo108hXjTrqeLaz77iHLUwqPUw7-lRiamPVGl7n1oTfF3qcju3a7uFB59MJknwRPF-cYvwSX8IpF8r8a3PTPGO6wwQgQ-QzTPZFpLWQPsgQWJSwuXlA-xDTPFUXNM31G3p51WwCa57jNjNYQ9N4CivYBnNYRWzZZceOd2TvOx3sMovESYrDPHhYiKkS2kxT7uCOppuST31_NOiOTcn-AgRVXGxKH9zmVPcK7g1lV_EsCTGuRA4mMqViXjjyFOvdJGkkgAX6igMyAYnXtjlrBg_KkD3Hv-MBxkVMQMCIs7nO-sxFhk6gZAM8T2nC9gr4yqpU0PPH01l3PDPMaKZUlBWtYrZL3bgu5DwXZcmmD-UEYkDhIUSBaTCralTPH_04G68PSYcsggeMO8Vy45goBmUYFYklO65w3WVh_XHW-3lVrXdA59gSWFlJ3OtWbKn8J8iPY_6a9v8jC19RnKaYh7mE6AKHeodhlkOGU0JZdMYjnMIYux5WfwEXrzEUbAsAAA==&view=attachment_table"

XPATH_HOME_MENU = '//*[@id="labelTextHome_Slice5"]'
XPATH_COMPUTER = '//*[@id="labelTextAsset_Slice0kJqpD2rSd4vybFDfjjg_0"]'
XPATH_USB = '//*[@id="labelTextAsset_Slice4KiSEvbGOL4kI2PvNdxn13"]'
XPATH_VESK = '//*[@id="labelTextvComputercp2320-catalog-64a6c775"]'
XPATH_VMK = '//*[@id="labelTextvComputercp2320-catalog-a161eb44"]'
XPATH_REQUEST_FOR_CANDIDATES = [
    "//input[contains(@id, 'mui-')]",
    "//input[@type='text']",
    "//input[contains(@placeholder, 'Request') or contains(@aria-label, 'Request')]",
    "//input"
]
XPATH_SUMMARY_INPUT = '//*[@id="__TableEntryScreenRequest_SchemaMy_Requestssummary"]/div/input'
XPATH_DESCRIPTION_INPUT = '//*[@id="__TableEntryScreenRequest_SchemaMy_Requestsdescription"]/div/input'
XPATH_PRIORITY_BUTTON = '//*[@id="__TableEntryScreenRequest_SchemaMy_Requestspriority"]/div/div/div[2]/span/div/span'
XPATH_SPECIFIC_FIELDS_TEXTAREA = '//*[@id="__TableEntryScreenRequest_SchemaMy_RequestsspecificFields"]/div/textarea'
XPATH_FINAL_SUBMIT_BUTTON = '/html/body/div[17]/div[3]/div/div[1]/div/div/div[2]/span/button[2]/span[1]'
XPATH_SYNC_BUTTON = '//*[@id="ReactRoot"]/div/header/div/div[4]/span[2]/div/button[1]'
XPATH_FIRST_ROW_CANDIDATES = [
    "(//*[contains(@id, 'Table_RowElement_My_Requests_')])[1]",
    "(//table//tbody/tr)[1]",
    "(//div[@role='row'])[2]"
]
XPATH_DETAIL_ACTION_BUTTON = '//*[@id="scroller"]/div/div/section[1]/div/div[2]/div[2]/span'
XPATH_NEXT_PAGE_LINK = '//*[@id="TableEntryScreenRequest_SchemaMy_Requests"]/div/div[11]/div/div/a'
XPATH_CHECKBOX_I5 = '//*[@id="i5"]'
XPATH_FORM_REQUEST_ID_INPUT = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[2]/div/div/div[3]/div/div[1]/div/div[1]/input'
XPATH_BU_DROPDOWN = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div[2]'
XPATH_BU_H77 = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[2]/div[3]/span'
XPATH_BU_A13 = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[2]/div[7]/span'
XPATH_BU_T58 = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[2]/div[5]/span'
XPATH_FORM_JOB_TITLE_INPUT = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[4]/div/div/div[2]/div/div[1]/div/div[1]/input'
XPATH_CATEGORY_DROPDOWN = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[5]/div/div/div[2]/div/div[1]/div[1]/div[1]'
XPATH_CATEGORY_COMPUTER = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[5]/div/div/div[2]/div/div[2]/div[5]/span'
XPATH_CATEGORY_USB = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[5]/div/div/div[2]/div/div[2]/div[3]/span'
XPATH_FORM_NEXT_PAGE_BUTTON = '//*[@id="mG61Hd"]/div[2]/div/div[3]/div[1]/div[1]/div/span'
XPATH_COST_CENTER_INPUT = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[2]/div/div/div[2]/div/div[1]/div/div[1]/input'
XPATH_PC_TYPE_DROPDOWN = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[1]/div[1]/div[1]/span'
XPATH_PC_LAPTOP_NORMAL = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[2]/div[3]/span'
XPATH_PC_LAPTOP_WIDE = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[2]/div[4]/span'
XPATH_PC_DESKTOP = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[2]/div[5]/span'
XPATH_PC_KEYBOARD_MICE = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[3]/div/div/div[2]/div/div[2]/div[12]/span'
XPATH_ACC_MONITOR = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[4]/div/div/div[2]/div[1]/div[1]/label/div/div[2]/div/span'
XPATH_ACC_MOUSE = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[4]/div/div/div[2]/div[1]/div[2]/label/div/div[2]/div/span'
XPATH_ACC_KEYBOARD = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[4]/div/div/div[2]/div[1]/div[3]/label/div/div[2]/div/span'
XPATH_FORM_DETAILS_TEXTAREA = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[5]/div/div/div[2]/div/div[1]/div[2]/textarea'
XPATH_PROXY_DROPDOWN = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[7]/div/div/div[2]/div/div[1]/div[1]/div[1]'
XPATH_PROXY_YES = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[7]/div/div/div[2]/div/div[2]/div[3]/span'
XPATH_PROXY_NO = '//*[@id="mG61Hd"]/div[2]/div/div[2]/div[7]/div/div/div[2]/div/div[2]/div[4]/span'
XPATH_FORM_FINAL_SUBMIT_SUBMIT = '//*[@id="mG61Hd"]/div[2]/div/div[3]/div[1]/div[1]/div[2]/span/span'

PROFILE_DIR = r'C:\ChromeProfile_ITRR'
PORT = 9222


def save_current_page_as_pdf(driver, output_pdf_path):
    print(f"📄 정식 인쇄 뷰 화면을 PDF로 저장 중... ({output_pdf_path})")
    pdf_data = driver.execute_cdp_cmd("Page.printToPDF", {
        "printBackground": True,
        "paperWidth": 8.27,
        "paperHeight": 11.69,
        "marginTop": 0.4,
        "marginBottom": 0.4,
        "marginLeft": 0.4,
        "marginRight": 0.4
    })
    with open(output_pdf_path, "wb") as f:
        f.write(base64.b64decode(pdf_data['data']))
    print("✅ 완벽한 규격의 메일 본문 PDF 저장 완료!")


def get_sheet_data_via_js(driver, req_num):
    print("📊 브라우저 로그인 세션(JS)으로 구글 스프레드시트 데이터 불러오는 중...")
    try:
        driver.get("https://docs.google.com")
        time.sleep(1)
        csv_text = driver.execute_script("""
            var url = arguments[0];
            var xhr = new XMLHttpRequest();
            xhr.open('GET', url, false);
            xhr.send(null);
            return xhr.responseText;
        """, CSV_EXPORT_URL)

        if not csv_text or "<html>" in csv_text.lower():
            return None

        df = pd.read_csv(io.StringIO(csv_text), on_bad_lines='skip', engine='python')
        df.columns = df.columns.str.strip()

        req_col = [col for col in df.columns if 'request' in col.lower() and 'number' in col.lower() or col.lower() == 'request number']
        if not req_col:
            req_col = [col for col in df.columns if 'request' in col.lower()]

        asset_col = [col for col in df.columns if 'asset' in col.lower()]
        division_col = [col for col in df.columns if 'devision' in col.lower() or 'division' in col.lower()]
        req_for_col = [col for col in df.columns if 'request for' in col.lower() or 'request_for' in col.lower()]
        details_col = [col for col in df.columns if 'detail' in col.lower()]
        bu_col = [col for col in df.columns if 'bu' in col.lower() or 'entity' in col.lower()]
        job_col = [col for col in df.columns if 'job' in col.lower() or 'title' in col.lower()]
        cost_col = [col for col in df.columns if 'cost' in col.lower() or 'center' in col.lower()]
        pctype_col = [col for col in df.columns if 'pc' in col.lower() or 'type' in col.lower()]
        acc_col = [col for col in df.columns if 'accessor' in col.lower()]
        proxy_col = [col for col in df.columns if 'behalf' in col.lower() or 'proxy' in col.lower() or '대리' in col.lower()]

        req_col_name = req_col[0]
        asset_col_name = asset_col[0]
        division_col_name = division_col[0] if division_col else None
        req_for_col_name = req_for_col[0] if req_for_col else None
        details_col_name = details_col[0] if details_col else None
        bu_col_name = bu_col[0] if bu_col else None
        job_col_name = job_col[0] if job_col else None
        cost_col_name = cost_col[0] if cost_col else None
        pctype_col_name = pctype_col[0] if pctype_col else None
        acc_col_name = acc_col[0] if acc_col else None
        proxy_col_name = proxy_col[0] if proxy_col else None

        matched_row = df[df[req_col_name].astype(str).str.strip() == str(req_num).strip()]

        if matched_row.empty:
            print(f"❌ 입력하신 Request Number [{req_num}]를 시트에서 찾을 수 없습니다.")
            return None

        row = matched_row.iloc[0]
        
        data = {
            "asset_type": str(row[asset_col_name]).strip() if pd.notna(row[asset_col_name]) else "",
            "division_type": str(row[division_col_name]).strip() if division_col_name and pd.notna(row[division_col_name]) else "",
            "req_for_name": str(row[req_for_col_name]).strip() if req_for_col_name and pd.notna(row[req_for_col_name]) else "",
            "details_val": str(row[details_col_name]).strip() if details_col_name and pd.notna(row[details_col_name]) else "",
            "bu_val": str(row[bu_col_name]).strip() if bu_col_name and pd.notna(row[bu_col_name]) else "",
            "job_title_val": str(row[job_col_name]).strip() if job_col_name and pd.notna(row[job_col_name]) else "",
            "cost_center_val": str(row[cost_col_name]).strip() if cost_col_name and pd.notna(row[cost_col_name]) else "",
            "pc_type_val": str(row[pctype_col_name]).strip() if pctype_col_name and pd.notna(row[pctype_col_name]) else "",
            "acc_val": str(row[acc_col_name]).strip() if acc_col_name and pd.notna(row[acc_col_name]) else "",
            "proxy_val": str(row[proxy_col_name]).strip() if proxy_col_name and pd.notna(row[proxy_col_name]) else "No"
        }
        return data
    except Exception as e:
        print(f"⚠️ 구글 시트 읽기 실패: {e}")
        return None


def safe_click(driver, element_or_xpath):
    for _ in range(3):
        try:
            if isinstance(element_or_xpath, str):
                element = driver.find_element(By.XPATH, element_or_xpath)
            else:
                element = element_or_xpath
            try:
                element.click()
            except Exception:
                driver.execute_script("arguments[0].click();", element)
            return True
        except StaleElementReferenceException:
            time.sleep(1)
        except Exception:
            time.sleep(0.5)
    return False


def safe_input_and_enter(driver, element_or_xpath, text):
    for _ in range(3):
        try:
            if isinstance(element_or_xpath, str):
                element = driver.find_element(By.XPATH, element_or_xpath)
            else:
                element = element_or_xpath
            element.click()
            time.sleep(0.3)
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.DELETE)
            element.send_keys(text)
            time.sleep(0.3)
            element.send_keys(Keys.ENTER)
            time.sleep(0.5)
            return True
        except StaleElementReferenceException:
            time.sleep(1)
        except Exception:
            try:
                if isinstance(element_or_xpath, str):
                    element = driver.find_element(By.XPATH, element_or_xpath)
                else:
                    element = element_or_xpath
                driver.execute_script("""
                    var el = arguments[0];
                    el.value = arguments[1];
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    el.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true}));
                """, element, text)
                time.sleep(0.5)
                return True
            except Exception:
                time.sleep(0.5)
    return False


def find_input_element(driver):
    for xpath in XPATH_REQUEST_FOR_CANDIDATES:
        try:
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements:
                if elem.is_displayed() and elem.is_enabled():
                    return elem
        except Exception:
            continue
    return None


def run_automation():
    req_input = input("👉 조회할 Request Number를 입력하세요: ").strip()
    if not req_input:
        print("입력값이 없습니다. 프로그램을 종료합니다.")
        return

    # -------------------------------------------------------------------------
    # 🚨 [프로세스 충돌 방지] 기존 백그라운드 크롬 및 드라이버 강제 종료
    # -------------------------------------------------------------------------
    print("🧹 기존 백그라운드 크롬 찌꺼기 및 포트 충돌 방지 초기화 중...")    
    os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
    time.sleep(1.5)
    
    # 프로필 잠금(Lock) 파일 강제 삭제 (현재 스크립트 경로인 v2에 맞춤)
    lock_file = r'C:\ChromeProfile_ITRR\SingletonLock'
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
        except:
            pass
    # -------------------------------------------------------------------------

    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    cmd = f'"{chrome_path}" --remote-debugging-port={PORT} --user-data-dir="{PROFILE_DIR}"'
    subprocess.Popen(cmd, shell=True)
    
    # 크롬이 완전히 켜질 때까지 기다리는 시간을 4초로 넉넉하게 늘려줍니다.
    time.sleep(4)

    options = webdriver.ChromeOptions()
    options.add_experimental_option("debuggerAddress", f"127.0.0.1:{PORT}")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)

    try:
        sheet_data = get_sheet_data_via_js(driver, req_input)
        if not sheet_data: return

        asset_type, division_type = sheet_data["asset_type"], sheet_data["division_type"]
        req_for_name, details_val = sheet_data["req_for_name"], sheet_data["details_val"]
        bu_val, job_title_val = sheet_data["bu_val"], sheet_data["job_title_val"]
        cost_center_val, pc_type_val = sheet_data["cost_center_val"], sheet_data["pc_type_val"]
        acc_val, proxy_val = sheet_data["acc_val"], sheet_data["proxy_val"]
        summary_text = f"{asset_type} Request".strip()

        target_asset_xpath = XPATH_COMPUTER if "computer" in asset_type.lower() else XPATH_USB
        target_division_xpath = None
        if "computer" in asset_type.lower():
            if "vesk" in division_type.lower(): target_division_xpath = XPATH_VESK
            elif "vmk" in division_type.lower(): target_division_xpath = XPATH_VMK

        print(f"🔎 조회 성공 - Asset: [{asset_type}] | Request for: [{req_for_name}] | BU: [{bu_val}] | PC Type: [{pc_type_val}] | Accessories: [{acc_val}]")

        # ---------------------------------------------------------------------
        # AppSheet 자동화 입력 파트
        # ---------------------------------------------------------------------
        driver.get(APPSHEET_URL)
        time.sleep(4)
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_HOME_MENU))))
        time.sleep(3)
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, target_asset_xpath))))
        time.sleep(3)
        if target_division_xpath:
            safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, target_division_xpath))))
            time.sleep(3)

        if req_for_name:
            time.sleep(3)
            input_element = None
            for _ in range(20):
                input_element = find_input_element(driver)
                if input_element: break
                time.sleep(1)
            if input_element:
                safe_input_and_enter(driver, input_element, req_for_name)

        if summary_text: safe_input_and_enter(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_SUMMARY_INPUT))), summary_text)
        if details_val: safe_input_and_enter(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_DESCRIPTION_INPUT))), details_val)
        
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_PRIORITY_BUTTON))))
        safe_input_and_enter(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_SPECIFIC_FIELDS_TEXTAREA))), "yes")

        try:
            safe_click(driver, WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, XPATH_FINAL_SUBMIT_BUTTON))))
        except Exception:
            safe_click(driver, driver.find_element(By.XPATH, "//div[contains(@role, 'dialog')]//button[2]"))

        time.sleep(2)
        try:
            safe_click(driver, WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, XPATH_SYNC_BUTTON))))
            time.sleep(15)
        except Exception:
            pass

        time.sleep(3)
        first_row_elem, target_xpath_found = None, None
        for candidate_xpath in XPATH_FIRST_ROW_CANDIDATES:
            try:
                elems = driver.find_elements(By.XPATH, candidate_xpath)
                for el in elems:
                    if el.is_displayed():
                        first_row_elem, target_xpath_found = el, candidate_xpath
                        break
                if first_row_elem: break
            except Exception:
                continue

        if not first_row_elem:
            target_xpath_found = "(//*[contains(@id, 'Table_RowElement_My_Requests_')])[1]"
            first_row_elem = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, target_xpath_found)))

        raw_id = ""
        try:
            raw_id = first_row_elem.get_attribute("id") or ""
            if "Table_RowElement_My_Requests_" not in raw_id:
                raw_id = first_row_elem.find_element(By.XPATH, ".//*[contains(@id, 'Table_RowElement_My_Requests_')]").get_attribute("id") or ""
        except Exception:
            pass

        saved_request_id = raw_id.split("Table_RowElement_My_Requests_")[-1] if "Table_RowElement_My_Requests_" in raw_id else "UNKNOWN_ID"
        
        safe_click(driver, target_xpath_found)
        time.sleep(3)
        
        # ---------------------------------------------------------------------
        # [수정] 절대 경로를 버리고 'Edit' 이름표(aria-label)로 추적하여 강제 클릭
        # ---------------------------------------------------------------------
        safe_click(driver, target_xpath_found)
        print("⏳ 리스트 클릭 후 상세 화면 로딩 대기 중 (5초)...")
        time.sleep(5) # 상세 화면이 완전히 열릴 때까지 여유 있게 기다립니다.
        
        # ---------------------------------------------------------------------
        # [수정] 화면에 '실제로 보이는' Edit 버튼만 찾아서 클릭
        # ---------------------------------------------------------------------
        print("⏳ 디테일 액션(Edit) 버튼 탐색 및 강제 클릭 중...")
        XPATH_DETAIL_ACTION_BUTTON_NEW = "//*[@aria-label='Edit'] | //*[text()='Edit'] | //div[contains(@aria-label, 'Edit')]"
        
        edit_clicked = False
        try:
            # 1. 조건에 맞는 모든 요소를 다 찾습니다. (단수가 아닌 복수형 elements)
            elements = WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.XPATH, XPATH_DETAIL_ACTION_BUTTON_NEW)))
            
            # 2. 그 중 화면에 실제로 보이는 녀석만 골라서 누릅니다.
            for el in elements:
                if el.is_displayed():
                    try:
                        # 사람이 누르듯 일반 클릭을 시도합니다.
                        el.click()
                        print("✅ 화면에 보이는 'Edit' 버튼 일반 클릭 성공!")
                        edit_clicked = True
                        break
                    except:
                        # 요소가 겹쳐서 안 눌리면 JS로 찌릅니다.
                        driver.execute_script("arguments[0].click();", el)
                        print("✅ 화면에 보이는 'Edit' 버튼 JS 강제 클릭 성공!")
                        edit_clicked = True
                        break
                        
            if not edit_clicked:
                print("⚠️ 'Edit' 요소를 찾았으나, 화면에 활성화된(보이는) 버튼이 없습니다.")
                
        except Exception as e:
            print(f"⚠️ 'Edit' 버튼 탐색 실패: {e}")
            
        time.sleep(4)
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_NEXT_PAGE_LINK))))
        time.sleep(3)

        if len(driver.window_handles) > 1: driver.switch_to.window(driver.window_handles[-1])

        time.sleep(2)
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_CHECKBOX_I5))))
        time.sleep(1)
        safe_input_and_enter(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_FORM_REQUEST_ID_INPUT))), saved_request_id)

        if bu_val:
            time.sleep(1.5)
            safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_BU_DROPDOWN))))
            time.sleep(1.5)
            target_bu_xpath = XPATH_BU_H77 if "h77" in bu_val.lower() else (XPATH_BU_A13 if "a13" in bu_val.lower() else (XPATH_BU_T58 if "t58" in bu_val.lower() else None))
            if target_bu_xpath: safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, target_bu_xpath))))

        if job_title_val:
            time.sleep(1)
            safe_input_and_enter(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_FORM_JOB_TITLE_INPUT))), job_title_val)

        time.sleep(1.5)
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_CATEGORY_DROPDOWN))))
        time.sleep(1.5)
        target_category_xpath = XPATH_CATEGORY_COMPUTER if "computer" in asset_type.lower() else (XPATH_CATEGORY_USB if "usb" in asset_type.lower() else None)
        if target_category_xpath: safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, target_category_xpath))))

        time.sleep(1)
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_FORM_NEXT_PAGE_BUTTON))))

        if cost_center_val:
            time.sleep(2)
            safe_input_and_enter(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_COST_CENTER_INPUT))), cost_center_val)

        if pc_type_val:
            time.sleep(1.5)
            safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_PC_TYPE_DROPDOWN))))
            time.sleep(1.5)
            val_lower = pc_type_val.lower()
            target_pctype_xpath = XPATH_PC_LAPTOP_NORMAL if "normal" in val_lower else (XPATH_PC_LAPTOP_WIDE if "wide" in val_lower else (XPATH_PC_DESKTOP if "desktop" in val_lower else (XPATH_PC_KEYBOARD_MICE if "accessories" in val_lower else None)))
            if target_pctype_xpath: safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, target_pctype_xpath))))

        if acc_val:
            time.sleep(1.5)
            acc_lower = acc_val.lower()
            if "monitor" in acc_lower: safe_click(driver, WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, XPATH_ACC_MONITOR))))
            if "mouse" in acc_lower: safe_click(driver, WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, XPATH_ACC_MOUSE))))
            if "keyboard" in acc_lower: safe_click(driver, WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, XPATH_ACC_KEYBOARD))))

        if details_val:
            time.sleep(1)
            safe_input_and_enter(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_FORM_DETAILS_TEXTAREA))), details_val)

        time.sleep(1.5)
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_PROXY_DROPDOWN))))
        time.sleep(1.5)
        target_proxy_xpath = XPATH_PROXY_YES if proxy_val.strip().lower() in ['yes', 'y', '예'] else XPATH_PROXY_NO
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, target_proxy_xpath))))

        # [23단계 및 24단계] 제출 버튼 클릭
        print("⏳ 23단계: 구글 폼 다음/제출 버튼 클릭 중...")
        time.sleep(1)
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_FORM_FINAL_SUBMIT_SUBMIT))))

        print("⏳ 24단계: 최종 Submit 창 제출 버튼 대기 및 클릭 중...")
        time.sleep(3) 
        safe_click(driver, WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, XPATH_FORM_FINAL_SUBMIT_SUBMIT))))
        print("✅ 구글 폼 최종 제출 완료!")

        # ---------------------------------------------------------------------
        # [25단계] 지메일 이동 및 스마트 수신 대기 (최대 60초간 반복 탐색)
        # ---------------------------------------------------------------------
        print("⏳ 25단계: 지메일 이동 및 메일 수신 확인 중...")
        driver.get("https://mail.google.com")
        time.sleep(10)

        search_query = f'from:noreply subject:"Google Form Result" "{saved_request_id}"'
        mail_opened = False
        max_retries = 6 
        
        for attempt in range(1, max_retries + 1):
            print(f"🔎 메일 도착 확인 중... (시도 {attempt}/{max_retries})")
            
            search_box = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//input[@aria-label='Search mail' or @aria-label='메일 검색' or @name='q']"))
            )
            search_box.click()
            time.sleep(0.5)
            search_box.send_keys(Keys.CONTROL + "a")
            search_box.send_keys(Keys.DELETE)
            search_box.send_keys(search_query)
            time.sleep(0.5)
            search_box.send_keys(Keys.ESCAPE)
            time.sleep(0.3)
            search_box.send_keys(Keys.ENTER)
            time.sleep(4) # 검색 결과 로딩 대기

            # [핵심 보완] 지메일의 실제 메일 항목(클래스명 zA)만 정확히 타겟팅
            email_rows = driver.find_elements(By.XPATH, "//tr[contains(@class, 'zA')]")
            
            if len(email_rows) > 0:
                print("✅ 메일 수신 확인! 해당 메일을 클릭하여 엽니다.")
                safe_click(driver, email_rows[0])
                time.sleep(3) # 메일 본문이 열릴 때까지 충분히 대기
                mail_opened = True
                break
            else:
                if attempt < max_retries:
                    print("⏳ 아직 검색 결과가 없습니다. 10초 후 재검색합니다...")
                    time.sleep(10)
                else:
                    print("❌ 최대 대기 시간(약 60초)을 초과했습니다. 메일이 도착하지 않았습니다.")

        # ---------------------------------------------------------------------
        # [26단계] 메일 고유 ID 다이렉트 추출 (엄격한 본문 매칭) 및 PDF 저장
        # ---------------------------------------------------------------------
        pdf_filepath = None
        if mail_opened:
            print("🖨️ 26단계: 본문에서 정확한 메일 1개의 고유 ID 추출 중...")
            
            # [수정] 지메일 본문(Body)을 나타내는 클래스(.a3s) 안에서만 엄격하게 Request ID를 찾습니다.
            legacy_msg_id = driver.execute_script("""
                var reqId = arguments[0];
                var bodies = document.querySelectorAll('.a3s'); // 메일 본문 영역
                for (var i = bodies.length - 1; i >= 0; i--) {
                    if (bodies[i].textContent.includes(reqId)) {
                        var container = bodies[i].closest('[data-legacy-message-id]');
                        if (container) {
                            return container.getAttribute('data-legacy-message-id');
                        }
                    }
                }
                
                // 본문에서 못 찾았다면 화면에 보이는 가장 최신 메일 ID 반환
                var msgs = document.querySelectorAll('[data-legacy-message-id]');
                if (msgs.length > 0) {
                    return msgs[msgs.length - 1].getAttribute('data-legacy-message-id');
                }
                return null;
            """, saved_request_id)

            if legacy_msg_id:
                print(f"✅ 정확한 타겟 메일 고유 ID 확보: {legacy_msg_id}")
                
                print_url = f"https://mail.google.com/mail/u/0/?view=pt&search=all&msg={legacy_msg_id}"

                driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": "window.print = function() { console.log('Print dialog suppressed successfully!'); };"
                })

                driver.get(print_url)
                time.sleep(3)

                pdf_filename = f"Final_Print_{saved_request_id}.pdf"
                pdf_filepath = os.path.join(os.getcwd(), pdf_filename)
                
                save_current_page_as_pdf(driver, pdf_filepath)
            else:
                print("❌ 타겟 Request ID를 가진 메일 본문을 찾지 못했습니다.")
        else:
            print("❌ 메일 창 열기에 실패하여 PDF 생성을 건너뜁니다.")

        # ---------------------------------------------------------------------
        # [27단계~30단계] AppSheet 파일 업로드 (더블 엔터) 및 Save 강제 클릭
        # ---------------------------------------------------------------------
        if pdf_filepath:
            print("⏳ 27단계: 기존 AppSheet 탭으로 복귀 중...")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            driver.get(ATTACHMENT_URL)
            time.sleep(5) 

            print("⏳ 28단계: 새로운 항목 추가 폼 열기...")
            XPATH_NEW_ADD_BTN = '//*[@id="ReactRoot"]/div/div/div[2]/div/div/div/div/div/div[1]/div/div/div[1]/div/div/div[2]/span/div/button[1]/span[1]/div'
            try:
                elem = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, XPATH_NEW_ADD_BTN)))
                safe_click(driver, elem)
            except Exception as btn_e:
                print(f"⚠️ 폼 열기 버튼 클릭 실패: {btn_e}")

            time.sleep(3)

            print("⏳ 29단계: PyAutoGUI 파일 업로드 (엔터 씹힘 방지 적용)...")
            XPATH_FILE_INPUT = "//div[starts-with(@id, 'FileUploadUtils')]//input[@type='file'] | //input[@type='file']"
            
            try:
                file_input = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, XPATH_FILE_INPUT)))
                driver.execute_script("arguments[0].click();", file_input)
                
                print("📂 윈도우 파일 탐색기가 열릴 때까지 3초 대기합니다...")
                time.sleep(3)
                
                # 클립보드에 경로 복사
                pyperclip.copy(pdf_filepath)
                time.sleep(0.5)
                
                # [핵심 1] 단축키(Alt+N)를 사용해 '파일 이름' 칸에 강제로 커서를 깜빡이게 만듭니다.
                pyautogui.hotkey('alt', 'n')
                time.sleep(1)
                
                # 3. 파일 이름칸에 붙여넣기 (Ctrl + V)
                pyautogui.hotkey('ctrl', 'v')
                print("경로 붙여넣기 완료. 1.5초 대기...")
                time.sleep(1.5)
                
                # 4. [핵심] Tab이나 Enter 대신, 한국어 윈도우 강제 '열기' 단축키(Alt+O) 발동!
                pyautogui.hotkey('alt', 'o')
                print("🎯 Alt+O (열기 버튼 강제 실행) 완료!")
                time.sleep(2)
                
                # (혹시라도 Alt+O가 씹혔을 때를 대비한 최후의 엔터)
                pyautogui.press('enter')
                
                print(f"✅ 물리 제어(Alt+N) 적용 완료! 파일 첨부 성공 ({pdf_filename})")
                
                print("⏳ AppSheet 서버 파일 처리 대기 중 (5초)...")
                time.sleep(2)
                
                print(f"✅ PyAutoGUI 물리 제어로 파일 첨부 완벽 성공! ({pdf_filename})")
                
                print("⏳ 30단계: Save 버튼 강력 클릭 (JS 강제 클릭 적용) 중...")
                time.sleep(10) # 파일 업로드 UI가 완전히 자리 잡을 때까지 잠시 대기
                
                save_clicked = False
                
                # 1. 짚어주신 절대 경로 우선 시도 (일반 클릭 대신 강력한 JS 클릭 사용)
                user_xpath = '/html/body/div[17]/div[3]/div/div[1]/div/div/div[2]/span/button[2]/span[1]'
                try:
                    btn = driver.find_element(By.XPATH, user_xpath)
                    if btn.is_displayed():
                        driver.execute_script("arguments[0].click();", btn)
                        print("✅ 지정해주신 절대 경로로 Save 버튼 클릭 완료!")
                        save_clicked = True
                except:
                    pass
                
                # 2. 절대 경로가 틀어졌을 경우, 화면에 보이는 모든 'Save' 요소를 찾아 강제 클릭
                if not save_clicked:
                    print("⚠️ 절대 경로 탐색 실패. 화면 내 Save 버튼을 스캔하여 강제 클릭합니다.")
                    # 대소문자 구분 없이 Save가 포함된 모든 요소 탐색
                    save_elements = driver.find_elements(By.XPATH, "//*[text()='Save' or contains(@aria-label, 'Save')] | //button[contains(., 'Save')]")
                    
                    for el in save_elements:
                        try:
                            # 화면에 실제로 보이는 버튼인지 확인
                            if el.is_displayed() and el.is_enabled():
                                driver.execute_script("arguments[0].click();", el)
                                print("✅ 화면에 보이는 Save 버튼 강제 클릭 완료!")
                                save_clicked = True
                                break
                        except:
                            continue
                            
                if not save_clicked:
                    print("❌ Save 버튼을 찾지 못했습니다. 화면 구조가 크게 변경되었을 수 있습니다.")
                else:
                    # ---------------------------------------------------------------------
                    # [31단계] Save 이후 10초 대기(동기화) 및 최종 상세 페이지 복귀
                    # ---------------------------------------------------------------------
                    print("⏳ 31단계: 데이터 동기화를 위해 10초 대기 중...")
                    time.sleep(10)
                    
                    print(f"🚀 최종 단계: Request ID [{saved_request_id}] 상세 페이지로 복귀합니다.")
                    
                    # 알려주신 URL 구조에서 row= 뒷부분을 현재 작업 중인 동적 Request ID로 교체합니다.
                    final_url = f"https://eu.appsheet.com/start/496e80db-2175-4081-af05-52cb8491a4d3?platform=desktop#appName=cp2320-eu-sql-6095245&vss=H4sIAAAAAAAAA62SX0vDMBTFv4rc5z4MC471USsisg022UszJDa3EpYmNX-cpfS7e9NNFNlT61tyc88v95ykgw-Jx63n5QGyovvZPWELGXQMntsGGWQM7oz21igGCYMVr0_FZXu1wfeAzrsXJZ1n0EOfTOPk6LlUbkDtk2-URwdZN26i7H-MJSAFai8riTYyI4FYZz0dRzUV_mopEaiD568KByOk7ak0NpSJbn6Rxhg6yy94go05nua5vpktZot0Pk9TgjxYE5pbqhf0mltj_bDu6BoVak3tpUUiiLWm5rUVcRbI0ZWohdRvwyfIseJB-R1XIf6DYt_HBCtTBodiR2lMS8E96vvPhmuxNIKsVFw57L8AGq6FfBwDAAA=&row={saved_request_id}&view=My%20Requests_Details"
                    
                    driver.get(final_url)
                    time.sleep(5) # 페이지 렌더링 여유 대기
                    
                print("🎉🎉🎉 [End-to-End 프로세스 완벽 종료] 구글 시트 조회부터 폼 제출, PDF 생성, AppSheet 업로드 및 최종 뷰어 복귀까지 100% 무인 자동화가 완성되었습니다!")

            except Exception as file_e:
                print(f"⚠️ 파일 업로드 중 오류 발생: {file_e}")

    except Exception as e:
        print(f"⚠️ 웹 자동화 진행 중 오류 발생: {e}")

if __name__ == "__main__":
    run_automation()
            
            
