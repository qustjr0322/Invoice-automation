import os
import re
from dotenv import load_dotenv
import time
import ctypes
import pyautogui
import webbrowser
import pyperclip
import pandas as pd
import pypdf
import streamlit as st
from openai import OpenAI

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

load_dotenv()
client = OpenAI()

# 🎯 Windows DPI 스케일링 보정
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

SHEET_URL = "https://docs.google.com/spreadsheets/d/1Cewofh1RBR1zqznDonA1ADjiw4SLosV7JGIpPH916V0/edit?gid=0#gid=0"
TARGET_BUY_URL = "https://valeo.determine.com/t/ui/md/home"

# 🎯 코드 → (Invoicing Company, Cost Center) 매핑 테이블 (여기 새로 추가)
CODE_MAP = {
    "ANY1": ("KJ03", "OO2144"),
    "H77":  ("KJ03", "OO2144"),
    "OO2144": ("KJ03", "OO2144"),
    "YQ1060": ("KJ03", "OO2144"),
    "OO1063": ("KJ03", "OO2144"),
    "OO1090": ("KJ03", "OO2144"),
    "ANS1": ("T58", "OM1060"),
    "OM1060": ("T58", "OM1060"),
    "KYO1": ("A13", "OJ1060"),
    "OJ1060": ("A13", "OJ1060"),
}

def resolve_company_and_cc(file_name: str, invoice_text: str):
    """파일명+본문에서 코드를 찾아 회사/코스트센터를 결정론적으로 반환"""
    combined = f"{file_name} {invoice_text}"
    for code, (company, cc) in CODE_MAP.items():
        if code in combined:
            return company, cc
    return None, None

# -------------------------------------------------------------------------
# 1. 파일(PDF / Excel) 텍스트 데이터 파싱 함수
# -------------------------------------------------------------------------
def extract_text_from_file(uploaded_file) -> str:
    file_type = uploaded_file.name.split('.')[-1].lower()
    extracted_text = ""

    if file_type in ['pdf']:
        reader = pypdf.PdfReader(uploaded_file)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
                
    elif file_type in ['xlsx', 'xls']:
        excel_data = pd.read_excel(uploaded_file, sheet_name=None)
        for sheet_name, df in excel_data.items():
            extracted_text += f"\n--- Sheet: {sheet_name} ---\n"
            extracted_text += df.to_string(index=False) + "\n"

    return extracted_text.strip()

# -------------------------------------------------------------------------
# 2. AI 분석 함수 (Invoicing Company 오염 철벽 정제)
# -------------------------------------------------------------------------
def analyze_invoice_by_price(invoice_text: str, sheet_url: str, user_keyword: str = None, file_name: str = ""):
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    gid = sheet_url.split('gid=')[1].split('#')[0] if 'gid=' in sheet_url else '0'
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    df = pd.read_csv(export_url)
    sheet_csv_text = df.to_csv(index=False, sep='^')
    
    prompt = f"""
너는 구매 포털 데이터 등록 자동화 매니저야.
아래 지시사항을 '절대적'으로 준수해.

[구글 시트 템플릿 DB]:
{sheet_csv_text}

[업로드된 파일 이름]:
{file_name}

[읽어온 파일 본문 내용]:
{invoice_text}

[타겟 매칭 키워드]:
{user_keyword if user_keyword else "없음"}

[지시사항]
1. 🎯 **[핵심 키워드 자동 추출]**:
   - [업로드된 파일 이름]과 본문에서 1) **통신사**(LG, KT, SK 등)와 2) **사이트/품목 코드**(ANY1, ANS1, H77, KYO1, SEO1 등)를 무조건 찾아내.
   - 예: 파일명이 'LG - ANY1'이라면 통신사는 'LG', 코드는 'ANY1'이야.

2. 🎯 **[템플릿 단일 행 선택 (철벽 교차 검증)]**:
   - [구글 시트 템플릿 DB]에서 위에서 찾은 **'통신사'와 '사이트/품목 코드'가 모두 포함된 단 1개의 행**을 찾아!
   - 🚨 주의: 파일명이 LG ANY1인데 DB에서 KT나 ANS1 항목을 고르면 절대 안 돼! 반드시 통신사와 코드가 일치해야 해.
   - 마지막으로, 선택된 행의 'Unit price' 숫자가 파일의 공급가액(VAT 제외)과 일치하는지 확인해.

3. 🚨 **[Invoicing Company / Cost Center 강제 매칭 그룹]**:
   - 매칭된 코드(ANY1, H77, OO2144, YQ1060, OO1063, OO1090) 👉 Invoicing Company: **KJ03**, Cost Center: **OO2144** (또는 DB 원본 CC 유지)
   - 매칭된 코드(ANS1, OM1060) 👉 Invoicing Company: **T58**, Cost Center: **OM1060**
   - 매칭된 코드(KYO1, OJ1060) 👉 Invoicing Company: **A13**, Cost Center: **OJ1060**

4. 🚨 **[포맷 무결성 철벽 방어 (가장 중요!)]**:
   - 제공된 템플릿 DB의 컬럼 구분자는 `^` 기호로 되어 있어.
   - 출력할 때 절대 띄어쓰기(스페이스)나 탭을 임의로 쓰지 말고, 원본 그대로 `^` 기호를 사용해서 26개 칸을 완벽히 유지해! 빈 칸도 `^^` 처럼 기호를 유지해.

5. ⚠️ **[출력 형식 규칙]**:
   - 첫 번째 줄: Invoicing Company (A13, T58, KJ03)
   - 두 번째 줄: Cost Center 코드
   - 세 번째 줄: 26개 컬럼 헤더(1행) ➔ 반드시 `^` 기호로 연결
   - 네 번째 줄: 데이터(2행) ➔ 반드시 `^` 기호로 연결
   - 마크다운이나 부연설명은 일절 출력하지 마.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    raw_result = response.choices[0].message.content
    clean_text = re.sub(r'```tsv\n|```\n|```|"""', '', raw_result).strip('\r\n')
    
    lines = clean_text.split('\n')
    tsv_data = '\n'.join(lines[2:]).replace('^', '\t')
    
    # 🚨 GPT 출력은 신뢰하지 않고, 파이썬 룰로만 100% 결정론적으로 매칭
    inv_company, cost_center = resolve_company_and_cc(file_name, invoice_text)
    
    if inv_company is None:
        raise ValueError(
            f"⚠️ 코드 매칭 실패: 파일명({file_name}) / 본문에서 등록된 사이트 코드를 찾을 수 없습니다. "
            f"CODE_MAP에 해당 코드를 추가해주세요."
        )
    
    return tsv_data, inv_company, cost_center

# -------------------------------------------------------------------------
# 3. Streamlit UI 구성
# -------------------------------------------------------------------------
st.set_page_config(page_title="E-Procurement Auto Assistant", page_icon="📑", layout="centered")

st.title("📑 E-Procurement 견적서 자동 등록 챗봇")
st.caption("견적서/고지서 파일(PDF, Excel)을 업로드하거나 텍스트를 입력하면 AI가 분석 후 구매 사이트를 호출합니다.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

st.sidebar.header("📁 견적서 파일 및 옵션")
uploaded_files = st.sidebar.file_uploader("PDF 또는 Excel 파일을 올려주세요", type=["pdf", "xlsx", "xls"], accept_multiple_files=True)
target_keyword = st.sidebar.text_input("🎯 Target Item (선택 사항)", placeholder="예: ANS1, SEO1 (비워두면 첫행)")
user_text_input = st.chat_input("또는 견적서 텍스트를 직접 입력하세요...")

invoice_content = ""
source_name = ""
saved_temp_file_paths = []

if uploaded_files:
    temp_dir = r"C:\Project\temp"
    os.makedirs(temp_dir, exist_ok=True)
    
    if st.sidebar.button("🚀 업로드된 파일 분석 시작", type="primary"):
        with st.spinner("📄 파일에서 데이터 추출 중..."):
            file_names_str = ""
            for uploaded_file in uploaded_files:
                file_name, file_ext = os.path.splitext(uploaded_file.name)
                unique_file_name = f"{file_name}_{int(time.time())}{file_ext}"
                saved_path = os.path.abspath(os.path.join(temp_dir, unique_file_name))
                
                with open(saved_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                saved_temp_file_paths.append(saved_path)
                file_names_str += f"{uploaded_file.name} / "
                
                invoice_content += f"\n\n--- [파일명: {uploaded_file.name}] ---\n"
                invoice_content += extract_text_from_file(uploaded_file)
            
            source_name = f"다중 파일 ({len(uploaded_files)}개): {file_names_str}"

elif user_text_input:
    invoice_content = user_text_input
    source_name = "직접 입력한 텍스트"

# -------------------------------------------------------------------------
# 4. 분석 및 자동화 프로세스 수행
# -------------------------------------------------------------------------
if invoice_content:
    st.session_state.messages.append({"role": "user", "content": f"[{source_name}] 분석 요청 (키워드: {target_keyword if target_keyword else '기본'})"})
    st.chat_message("user").write(f"[{source_name}] 분석 요청 (키워드: {target_keyword if target_keyword else '기본'})")
    
    with st.chat_message("assistant"):
        with st.spinner("📊 템플릿 매칭, 변동 금액 및 CostCenter 규칙 검토 중..."):
            try:
                tsv_result, invoicing_company_value, cost_center_value = analyze_invoice_by_price(
                    invoice_content, 
                    SHEET_URL, 
                    user_keyword=target_keyword if target_keyword else None,
                    file_name=source_name
                )
                pyperclip.copy(tsv_result)
                
                st.success(f"✅ 템플릿 분석 완료! (Invoicing Company: **{invoicing_company_value}**, Cost Center: **{cost_center_value}**)")
                st.code(tsv_result, language="text")
                
                # 🚨 [프로세스 충돌 방지] 기존 백그라운드 크롬 드라이버 강제 종료
                os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
                time.sleep(1.0)
                
                # 프로필 잠금(Lock) 파일 강제 삭제
                lock_file = r'C:\ChromeProfile_Automation_v2\SingletonLock'
                if os.path.exists(lock_file):
                    try:
                        os.remove(lock_file)
                    except:
                        pass

                options = uc.ChromeOptions()
                options.add_argument(r'--user-data-dir=C:\ChromeProfile_Automation_v2')
                options.add_argument('--no-first-run')
                options.add_argument('--no-service-autorun')
                
                # 💡 [핵심 방어] Streamlit 통신 단절 및 메모리/포트 충돌 원천 차단
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--remote-debugging-port=0') # 고정 포트 대신 랜덤 포트 할당으로 충돌 방지

                try:
                    # 브라우저 실행 시 subprocess 모드 유지
                    driver = uc.Chrome(options=options, version_main=151, use_subprocess=True)
                except Exception as uc_e:
                    st.error("⚠️ 크롬을 제어할 수 없습니다. 열려있는 '구매 포털 크롬 창'이 있다면 모두 닫고 다시 시도해주세요!")
                    raise uc_e
                
                try:
                    driver.get(TARGET_BUY_URL)
                    print("🚀 프로세스 시작 및 SSO 로그인 대기 중 (최대 60초)...")

                    # 1. New Requisition 클릭 (SSO 딜레이를 고려하여 대기 시간을 60초로 대폭 연장)
                    new_req_xpath = '//*[@id="bpackLayout"]/div[1]/section/article[2]/div/div[1]/div[1]/button'
                    try:
                        iframe = WebDriverWait(driver, 60).until(
                            EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                        )
                        driver.switch_to.frame(iframe)

                        btn = WebDriverWait(driver, 20).until(
                            EC.element_to_be_clickable((By.XPATH, new_req_xpath))
                        )
                        time.sleep(1.0) # 화면 애니메이션 및 렌더링 안정화
                        btn.click()
                        print("⚡ 1단계: New Requisition 클릭 완료!")

                    except Exception as e:
                        print("⚠️ 최초 접속 지연 또는 SSO 튕김 발생. 타겟 URL로 재접속을 시도합니다...")
                        # 화면이 엉뚱한 메인 페이지로 갔다면 다시 타겟 URL 강제 이동
                        driver.get(TARGET_BUY_URL)
                        iframe = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
                        driver.switch_to.frame(iframe)
                        btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, new_req_xpath)))
                        time.sleep(1.0)
                        btn.click()
                        print("⚡ 1단계: 재접속 후 New Requisition 클릭 완료!")

                    # 2단계: Invoicing Company 입력
                    test_input_value = invoicing_company_value

                    try:
                        print("⌨️ 2단계: Invoicing Company 입력창 탐색 중...")
                        # 1단계 클릭 후 입력 폼 전체가 완전히 렌더링될 때까지 충분히 대기
                        time.sleep(2.5) 
                        
                        inv_xpath = '//label[contains(., "Invoicing")]/following::input[1]'
                        input_field = WebDriverWait(driver, 15).until(
                            EC.presence_of_element_located((By.XPATH, inv_xpath))
                        )

                        # 일반 클릭이 투명 막 등에 가려져 실패할 경우 자바스크립트로 강제 클릭 (절대 안 씹힘)
                        try:
                            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, inv_xpath))).click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", input_field)
                            
                        time.sleep(0.5)
                        # 기존 값 확실히 지우기
                        input_field.send_keys(Keys.CONTROL + "a")
                        input_field.send_keys(Keys.BACKSPACE)
                        time.sleep(0.5)
                        
                        input_field.send_keys(test_input_value)
                        print(f"⌨️ '{test_input_value}' 입력 완료! 목록 대기 중...")
                        time.sleep(3.5)
                        
                        input_field.send_keys(Keys.ARROW_DOWN)
                        time.sleep(0.5)
                        input_field.send_keys(Keys.ENTER)
                        time.sleep(2.0)
                        print("🎉 2단계: Invoicing Company 선택 완료!")

                    except Exception as e:
                        print(f"⚠️ 2단계 실패: {e}")

                    # 3단계: Ship to 버튼 클릭
                    try:
                        print("🖱️ 3단계: RECDPTIDcombo 버튼 탐색 중...")
                        combo_btn = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, '//button[@data-btname="RECDPTIDcombo"]'))
                        )
                        combo_btn.click()
                        time.sleep(1.5)
                        print("🎉 3단계: Ship to 버튼 클릭 성공!")

                    except Exception as e:
                        print(f"⚠️ 3단계 실패: {e}")

                    # 4. Cost Center 입력
                    test_cost_center = cost_center_value

                    try:
                        print("🖱️ 4단계: INVDPTIDcombo 콤보박스 버튼 탐색 중...")
                        time.sleep(1.0)
                        
                        combo_inv_xpath = '//button[@data-btname="INVDPTIDcombo"]'
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, combo_inv_xpath))
                        )
                        combo_inv_btn = driver.find_element(By.XPATH, combo_inv_xpath)
                        
                        try:
                            combo_inv_btn.click()
                        except Exception:
                            driver.execute_script("arguments[0].click();", combo_inv_btn)

                        print("🎉 4단계: Cost center 클릭 성공!")
                        time.sleep(0.8)

                        active_input = driver.switch_to.active_element
                        active_input.send_keys(test_cost_center)
                        print(f"⌨️ '{test_cost_center}' 입력 완료!")
                        
                        time.sleep(2.0)
                        active_input.send_keys(Keys.ARROW_DOWN)
                        time.sleep(0.5)
                        active_input.send_keys(Keys.ENTER)
                        time.sleep(2.5)
                        print("🎉 4단계: Cost Center 선택 완료!")

                    except Exception as e:
                        print(f"⚠️ 4단계 실패: {e}")

                    # 5. 점 3개 메뉴 클릭 후 -> Import 클릭
                    try:
                        print("🖱️ 5단계: 우측 상단 점 3개 메뉴 열기 시도...")
                        time.sleep(1.0)
                        
                        open_menu_script = """
                            const host = document.querySelector('newcart-dropdown-menu');
                            if (host && host.shadowRoot) {
                                const menuBtn = host.shadowRoot.querySelector('.newcart-dropdown-button');
                                if (menuBtn) {
                                    menuBtn.click();
                                    return "OPEN_SUCCESS";
                                }
                            }
                            return "FAIL";
                        """
                        
                        open_result = driver.execute_script(open_menu_script)
                        
                        if open_result == "OPEN_SUCCESS":
                            print("🔓 5단계: 점 3개 메뉴 클릭 완료! (메뉴 열림 대기 중...)")
                            time.sleep(1.0)
                            
                            click_import_script = """
                                const host = document.querySelector('newcart-dropdown-menu');
                                if (host && host.shadowRoot) {
                                    const importBtn = host.shadowRoot.querySelector('a[data-id="form_import"]');
                                    if (importBtn) {
                                        importBtn.click();
                                        return "IMPORT_SUCCESS";
                                    }
                                }
                                return "FAIL";
                            """
                            
                            import_result = driver.execute_script(click_import_script)
                            
                            if import_result == "IMPORT_SUCCESS":
                                print("🎉 5단계: Import 팝업 띄우기 최종 성공!")
                            else:
                                print("⚠️ 5단계: 메뉴는 열었으나 Import 버튼을 누르지 못했습니다.")
                        else:
                            print("⚠️ 5단계: 점 3개 메뉴 자체를 찾지 못했습니다 (NO_HOST).")

                    except Exception as e:
                        print(f"⚠️ 5단계 예외 발생: {e}")

                    # 6. Import 텍스트 에어리어(Textarea)에 템플릿 내용 붙여넣기
                    try:
                        print("⌨️ 6단계: 템플릿 입력창(Textarea) 탐색 중...")
                        time.sleep(1.5)

                        textarea_xpath = '//textarea'
                        textarea = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, textarea_xpath))
                        )
                        
                        template_text = tsv_result

                        textarea.click()
                        time.sleep(0.3)
                        textarea.send_keys(Keys.CONTROL + "a")
                        textarea.send_keys(Keys.BACKSPACE)
                        time.sleep(0.3)
                        
                        driver.execute_script("arguments[0].value = arguments[1];", textarea, template_text)
                        
                        textarea.send_keys(Keys.SPACE)
                        textarea.send_keys(Keys.BACKSPACE)
                        
                        print("🎉 6단계: 템플릿 데이터 붙여넣기 성공!")
                        time.sleep(1.0)

                    except Exception as e:
                        print(f"⚠️ 6단계 실패: {e}")

                    # 7. 템플릿 처리(Import) 버튼 클릭 및 동기화 대기 (파란색 Import 버튼)
                    try:
                        print("🖱️ 7단계: Import 완료(동기화) 버튼 탐색 중...")
                        sync_btn_xpath = '//*[@id="Edit"]/div[3]/div[1]/table/tbody/tr/td[3]/button'
                        sync_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, sync_btn_xpath)))
                        sync_btn.click()
                        print("🎉 7단계: 파란색 Import 버튼 클릭 성공! (처리 대기 중...)")
                        time.sleep(9.0)
                    except Exception as e:
                        print(f"⚠️ 7단계 일반 클릭 실패: {e}")
                        try:
                            sync_btn = driver.find_element(By.XPATH, sync_btn_xpath)
                            driver.execute_script("arguments[0].click();", sync_btn)
                            time.sleep(9.0)
                        except Exception as inner_e:
                            print(f"⚠️ 7단계 최종 실패: {inner_e}")

                    # 8. My Cart 버튼 클릭
                    try:
                        print("🖱️ 8단계: 다음 버튼(span) 탐색 중...")
                        time.sleep(1.0)
                        next_btn_xpath = '//*[@id="Edit"]/div[3]/div[2]/table/tbody/tr/td/button/span'
                        next_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, next_btn_xpath)))
                        next_btn.click()
                        print("🎉 8단계: My cart 버튼 클릭 성공!")
                        time.sleep(1.5)
                    except Exception as e:
                        print(f"⚠️ 8단계 실패: {e}")
                        try:
                            next_btn = driver.find_element(By.XPATH, next_btn_xpath)
                            driver.execute_script("arguments[0].click();", next_btn)
                            time.sleep(1.5)
                        except: pass

                    # 9. summary check 버튼 클릭
                    try:
                        print("🖱️ 9단계: 템플릿 입력 완료 버튼 탐색 중...")
                        time.sleep(1.0)
                        confirm_btn_xpath = '//*[@id="Edit"]/div[3]/div/div/div/div/div/div/div/div[3]/div/div/div/div[2]/div[2]/button'
                        confirm_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, confirm_btn_xpath)))
                        confirm_btn.click()
                        print("🎉 9단계: summary check 버튼 클릭 성공! (처리 대기 중...)")
                        time.sleep(3.0)
                    except Exception as e:
                        print(f"⚠️ 9단계 일반 클릭 실패: {e}")
                        try:
                            confirm_btn = driver.find_element(By.XPATH, confirm_btn_xpath)
                            driver.execute_script("arguments[0].click();", confirm_btn)
                            time.sleep(3.0)
                        except: pass

                    # 10. proceed to requisition 버튼 클릭 및 동기화 대기
                    try:
                        print("🖱️ 10단계: 팝업창 버튼 탐색 중...")
                        time.sleep(1.0)
                        popup_btn_xpath = '//*[@id="popForm_CART_POPUP"]/div[5]/div[1]/div/div/div[1]/div/div/div/div/button'
                        popup_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, popup_btn_xpath)))
                        popup_btn.click()
                        print("⚡ 10단계: proceed to requisition 버튼 클릭 성공! (동기화 진행 중...)")
                        time.sleep(2)
                    except Exception as e:
                        print(f"⚠️ 10단계 실패: {e}")
                        try:
                            popup_btn = driver.find_element(By.XPATH, popup_btn_xpath)
                            driver.execute_script("arguments[0].click();", popup_btn)
                            time.sleep(2)
                        except: pass

                    # 11. attachments 버튼 클릭
                    try:
                        print("🖱️ 11단계: 동기화 완료 후 다음 버튼 탐색 중...")
                        time.sleep(1.0)
                        next_action_btn_xpath = '//*[@id="Edit"]/div[3]/div[1]/table/tbody/tr/td[2]/button'
                        next_action_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, next_action_btn_xpath)))
                        next_action_btn.click()
                        print("🎉 11단계: attachments 버튼 클릭 성공!")
                        time.sleep(2.0)
                    except Exception as e:
                        print(f"⚠️ 11단계 실패: {e}")
                        try:
                            next_action_btn = driver.find_element(By.XPATH, next_action_btn_xpath)
                            driver.execute_script("arguments[0].click();", next_action_btn)
                            time.sleep(2.0)
                        except: pass

                    # 12. DOCSBLOCK 클릭 (문서/첨부 영역 오픈)
                    try:
                        print("🖱️ 12단계: DOCSBLOCK 요소를 탐색 중...")
                        time.sleep(1.0)
                        docsblock_xpath = '//*[@id="DOCSBLOCK"]'
                        docsblock_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, docsblock_xpath)))
                        docsblock_btn.click()
                        print("🎉 12단계: DOCSBLOCK 클릭 성공!")
                        time.sleep(1.5)
                    except Exception as e:
                        print(f"⚠️ 12단계 실패: {e}")
                        try:
                            docsblock_btn = driver.find_element(By.XPATH, docsblock_xpath)
                            driver.execute_script("arguments[0].click();", docsblock_btn)
                            time.sleep(1.5)
                        except: pass

                    # 13. DOCSBLOCK 내부 첨부/추가 버튼 클릭
                    try:
                        print("🖱️ 13단계: DOCSBLOCK 내부 버튼 탐색 중...")
                        time.sleep(1.0)
                        add_doc_btn_xpath = '//*[@id="DOCSBLOCK"]/div/div/div/div[4]/div[1]/table/tbody/tr/td/button'
                        add_doc_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, add_doc_btn_xpath)))
                        add_doc_btn.click()
                        print("🎉 13단계: 버튼 클릭 성공!")
                        time.sleep(1.5)
                    except Exception as e:
                        print(f"⚠️ 13단계 실패: {e}")
                        try:
                            add_doc_btn = driver.find_element(By.XPATH, add_doc_btn_xpath)
                            driver.execute_script("arguments[0].click();", add_doc_btn)
                            time.sleep(1.5)
                        except: pass

                    # 14. 파일 탐색(Browse) 버튼 클릭 및 파일 업로드(PyAutoGUI)
                    try:
                        print("🖱️ 14단계: 파일 탐색(Browse) 버튼 탐색 중...")
                        time.sleep(1.0)
                        browse_btn_xpath = '//*[starts-with(@id, "FILENAME") and contains(@id, "browse")]'
                        
                        browse_btn = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, browse_btn_xpath))
                        )
                        browse_btn.click()
                        print("🎉 14단계: Browse 버튼 클릭 성공! (윈도우 탐색기 팝업 대기)")
                        time.sleep(2.0) # 윈도우 창이 뜰 때까지 대기

                        # 🚨 [OS 팝업 제어] Streamlit에 업로드했던 첫 번째 파일 경로를 PyAutoGUI로 입력
                        if saved_temp_file_paths:
                            target_file_path = saved_temp_file_paths[0]
                            print(f"📂 파일 업로드 진행 중: {target_file_path}")
                            
                            pyperclip.copy(target_file_path)
                            time.sleep(0.5)
                            
                            # 한국어 윈도우 기준 '파일 이름(N)' 단축키인 Alt + N 누르기
                            pyautogui.hotkey('alt', 'n') 
                            time.sleep(0.3)
                            
                            # 경로 붙여넣기 및 엔터
                            pyautogui.hotkey('ctrl', 'v')
                            time.sleep(0.5)
                            pyautogui.press('enter')
                            
                            print("🎉 15단계: 윈도우 파일 첨부 완료!")
                            time.sleep(4.0)
                        else:
                            print("⚠️ 스트림릿에 업로드된 파일이 없어 첨부를 건너뜁니다.")

                    except Exception as e:
                        print(f"⚠️ 14단계 실패: {e}")
                        try:
                            browse_btn = driver.find_element(By.XPATH, browse_btn_xpath)
                            driver.execute_script("arguments[0].click();", browse_btn)
                            time.sleep(2.0)
                            
                            if saved_temp_file_paths:
                                pyperclip.copy(saved_temp_file_paths[0])
                                time.sleep(0.5)
                                pyautogui.hotkey('alt', 'n')
                                time.sleep(0.3)
                                pyautogui.hotkey('ctrl', 'v')
                                time.sleep(0.5)
                                pyautogui.press('enter')
                                time.sleep(2.0)
                        except: pass

                    # 15. 첨부 진행 후 Add & Back to requisition 버튼 클릭
                    try:
                        print("🖱️ 15단계: 첨부 완료 후 최종 버튼 탐색 중...")
                        # 🚨 파일 업로드 처리가 완료될 시간을 넉넉히 3초 대기합니다.
                        time.sleep(3.0) 
                        
                        final_btn_xpath = '//*[@id="Edit"]/div[3]/div[1]/table/tbody/tr/td[1]/button'
                        
                        final_btn = WebDriverWait(driver, 15).until(
                            EC.element_to_be_clickable((By.XPATH, final_btn_xpath))
                        )
                        final_btn.click()
                        print("🎉 15단계: Add & Back to requisition 버튼 클릭 성공!")
                        time.sleep(3.0) # 클릭 후 페이지 전환 대기
                        
                    except Exception as e:
                        print(f"⚠️ 15단계 일반 클릭 실패: {e}")
                        # 가려짐 이슈 방지용 강제 클릭 예비 로직
                        try:
                            final_btn = driver.find_element(By.XPATH, final_btn_xpath)
                            driver.execute_script("arguments[0].click();", final_btn)
                            print("🎉 15단계: 자바스크립트로 최종 버튼 클릭 성공!")
                            time.sleep(3.0)
                        except Exception as inner_e:
                            print(f"⚠️ 15단계 최종 실패: {inner_e}")

                    # 16. DESCRIPTION 입력 (규칙 적용 텍스트 합성)
                    try:
                        print("⌨️ 16단계: DESCRIPTION 입력창 탐색 중...")
                        time.sleep(1.5) # 15단계 버튼 클릭 후 화면/모달 로딩 대기
                        
                        # 1) TSV 데이터에서 'Short description' 텍스트만 추출
                        try:
                            headers = tsv_result.split('\n')[0].split('\t')
                            # 'Short description'이 포함된 헤더의 인덱스 찾기
                            desc_idx = next(i for i, h in enumerate(headers) if 'Short description' in h)
                            short_desc = tsv_result.split('\n')[1].split('\t')[desc_idx].strip()
                        except Exception:
                            # 만약 추출에 실패할 경우를 대비한 안전 기본값
                            short_desc = ""

                        # 2) 오늘 날짜(YYYY.MM) 가져오기 및 텍스트 합성
                        current_ym = time.strftime("%Y.%m")
                        description_text = f"Seokhoon Byun {short_desc}-{current_ym}"
                        
                        desc_xpath = '//*[@id="DESCRIPTION"]'
                        desc_input = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, desc_xpath))
                        )
                        
                        # 3) 입력창 초기화 및 합성된 텍스트 입력
                        desc_input.click()
                        time.sleep(0.3)
                        desc_input.send_keys(Keys.CONTROL + "a")
                        desc_input.send_keys(Keys.BACKSPACE)
                        time.sleep(0.3)
                        
                        desc_input.send_keys(description_text)
                        print(f"🎉 16단계: DESCRIPTION ('{description_text}') 입력 완료!")
                        time.sleep(2.0)
                        
                    except Exception as e:
                        print(f"⚠️ 16단계 일반 입력 실패: {e}")
                        # 가려짐 이슈 방지용 예비 로직
                        try:
                            desc_input = driver.find_element(By.XPATH, desc_xpath)
                            driver.execute_script("arguments[0].value = arguments[1];", desc_input, description_text)
                            # 값 변경 인식 이벤트 트리거
                            desc_input.send_keys(Keys.SPACE, Keys.BACKSPACE) 
                            print(f"🎉 16단계: 자바스크립트로 DESCRIPTION 입력 완료!")
                            time.sleep(2.0)
                        except Exception as inner_e:
                            print(f"⚠️ 16단계 최종 실패: {inner_e}")

                except Exception as fatal_e:
                    print(f"\n❌ 치명적 실행 오류 발생: {fatal_e}")

                response_msg = f"Invoicing Company({invoicing_company_value}), Cost Center({cost_center_value}) 반영 완료!"
                st.write(response_msg)
                st.session_state.messages.append({"role": "assistant", "content": response_msg})

            except Exception as e:
                error_msg = f"⚠️ 처리 중 오류가 발생했습니다: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
