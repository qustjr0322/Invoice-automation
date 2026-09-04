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
    "OO2144": ("KJ03", "OO2144"),
    "YQ1060": ("KJ03", "YQ1060"),
    "OO1063": ("KJ03", "OO1063"),
    "OO1090": ("KJ03", "OO1090"),
    "ANS1": ("T58", "OM1060"),
    "OM1060": ("T58", "OM1060"),
    "KYO1": ("A13", "OJ1060"),
    "OJ1060": ("A13", "OJ1060"),
    "SEO1": ("KJ03", "OO1063"),
    "SEO3" : ("KJ03", "YQ1060")
}

def resolve_company_and_cc(file_name: str, invoice_text: str, tsv_data: str, user_keyword: str = None):
    """🚨 계급(우선순위) 기반 철벽 매칭 시스템"""
    # 1순위: 유저가 명시한 키워드 (절대 권력)
    if user_keyword:
        kw = user_keyword.upper()
        for code, (comp, cc) in CODE_MAP.items():
            if code in kw: return comp, cc
            
    # 2순위: AI가 분석해 낸 TSV 표 결과물
    for code, (comp, cc) in CODE_MAP.items():
        if code in tsv_data.upper(): return comp, cc
        
    # 3순위: 업로드된 파일명
    for code, (comp, cc) in CODE_MAP.items():
        if code in file_name.upper(): return comp, cc
        
    # 4순위: 견적서 본문 텍스트
    for code, (comp, cc) in CODE_MAP.items():
        if code in invoice_text.upper(): return comp, cc
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
1. 🎯 **[본문 내 전체 항목 코드 식별 - 단일 아님, 전체 스캔]**:
   - 견적서/파일 본문을 스캔해서 등장하는 **모든 사이트/품목 코드**(예: SEO1, SEO3, ANY1, KYO1 등)를 빠짐없이 리스트업해.
   - 만약 [타겟 매칭 키워드]가 "없음"이 아니라면, 그 키워드가 포함하는 코드(들)만 대상으로 삼고 나머지는 무시해. "없음"이면 본문에서 발견되는 코드를 전부 대상으로 삼아.
   - 🚨 코드가 여러 개면(SEO1, SEO3처럼) **각각을 완전히 독립적인 개별 항목으로 취급**해. 하나로 합치거나 대표 코드 하나만 고르지 마.

2. 🎯 **[코드별 템플릿 행 매칭 (문자열 완전 동일성 강제)]**:
   - 1번에서 확정된 코드 **하나하나에 대해** [구글 시트 템플릿 DB]에서 글자 하나까지 100% 동일한 코드가 포함된 행을 찾아.
   - 🚨🚨 **[접두사 유사 = 다른 코드]**: "SEO1"과 "SEO3"처럼 앞부분이 같아도 끝자리가 다르면 완전히 별개의 코드다. 절대 서로의 대체나 중복으로 착각해서 하나를 빼먹거나 합치지 마.
   - 🚨🚨 **[동일 코드라도 Short description 포맷이 다르면 별개 항목 — 절대 함께 매칭 금지]**:
     - 같은 코드(예: ANS1)를 포함하더라도, Short description의 **괄호 구성 형태**가 다르면 서로 완전히 다른 항목이다. 
     - 예시: "ANAM IT support service fee (ANS1)"는 괄호 안에 코드만 단독으로 들어있는 **표준 포맷**이고, "ANAM IT support service fee(출장비)-ANS1"는 괄호 안에 "출장비"(다른 단어)가 들어가고 그 뒤에 "-ANS1"이 붙은 **변형/추가 항목**이다. 이 둘은 코드 문자열이 겹치더라도 서로 다른 항목이므로 절대 함께 추출하지 마.
     - 판단 기준: Short description에서 코드가 **괄호 안에 단독으로("(코드)")** 들어있는 표준 포맷 행만 매칭 대상으로 삼아라. 코드 앞뒤에 "출장비", "택배비", 기타 한글/영문 수식어가 붙어 코드가 변형된 형태로 등장하는 행은, [타겟 매칭 키워드]나 견적서 본문이 그 변형 항목을 명시적으로 요구하지 않는 한 **절대 매칭하지 마라.**
   - 🚨 **[연속 행 묶음]**: 특정 코드 하나가 DB에서 빈 줄 없이 연달아 중복되어 있다면(완전히 동일한 코드이고, 완전히 동일한 Short description 포맷일 때만) 그 연속 블록 전체를 그 코드의 결과로 추출해.
   - 판단 순서: ① 코드별로 완전 일치 행 탐색 → ② Short description 포맷이 표준 단독 괄호 형태인지 확인(변형 항목이면 제외) → ③ 남은 행들 중에서만 연속 중복 여부 확인. 코드 간에 절대 섞지 마.

3. 🚨 **[Cost Center — DB 원본 값 절대 유지, 그룹 기본값으로 덮어쓰기 금지]**:
   - 각 코드로 찾은 템플릿 행의 **Cost Center 값은 해당 행에 원래 적혀있던 DB 원본 값을 그대로 사용**해. 
   - 아래 그룹 매핑은 오직 **Invoicing Company를 결정할 때만** 사용하고, Cost Center 컬럼 자체를 그룹 기본값으로 바꿔치기하지 마:
     - 코드(ANY1, H77, OO2144, YQ1060, OO1063, OO1090 등)가 속한 행 👉 Invoicing Company: **KJ03** / Cost Center는 그 행의 DB 원본값 그대로(OO1063이면 OO1063, YQ1060이면 YQ1060 등 각자 다르게 유지)
     - 코드(ANS1, OM1060) 👉 Invoicing Company: **T58** / Cost Center는 DB 원본값 유지
     - 코드(KYO1, OJ1060) 👉 Invoicing Company: **A13** / Cost Center는 DB 원본값 유지
   - 🚨 즉 같은 Invoicing Company 그룹 안에서도, 코드마다 Cost Center가 다를 수 있다는 걸 명심해. 절대 한 그룹이라고 해서 모든 행에 동일한 CC를 강제하지 마.

4. 🎯 **[다중 항목 결과 병합 - 한 줄이 아니라 코드 개수만큼의 줄]**:
   - 1번에서 식별된 코드가 N개라면, 최종 데이터는 **N개의 행**으로 구성해. (SEO1, SEO3 두 개면 데이터 2줄)
   - 각 행은 자신이 매칭된 템플릿 행의 모든 컬럼 값(Short description, Technology, Supplier, Unit price, Cost Center 등)을 그대로 반영해야 해.
   - 모든 코드의 Invoicing Company가 동일한 그룹으로 판정되면 헤더의 Invoicing Company는 한 번만 표기하고, 데이터 행들만 아래에 쭉 나열해.
   - 🚨 **[내부 검증용, 출력 절대 금지]**: 추출한 모든 템플릿 행의 'Unit price' 합계가 견적서 본문에 적힌 전체 항목의 공급가액 합계(VAT 제외)와 일치하는지 **너 스스로 속으로만 계산해서 확인**해. 이 검증 과정, 계산 결과, 합계 숫자는 **최종 답변에 절대 텍스트로 출력하지 마.** 오직 6번 출력 형식에 정의된 줄들만 출력해.

5. 🚨 **[포맷 무결성 철벽 방어]**:
   - 템플릿 DB의 컬럼 구분자는 `^` 기호야.
   - 출력할 때 띄어쓰기(스페이스)나 탭을 임의로 쓰지 말고 원본 그대로 `^` 기호로 26개 칸을 유지해. 빈 칸도 `^^`처럼 기호를 유지해.

6. ⚠️ **[출력 형식 규칙 - 이 형식 외 그 어떤 텍스트도 절대 출력 금지]**:
   - 첫 번째 줄: Invoicing Company (A13, T58, KJ03) — 그룹이 같으면 한 번만
   - 두 번째 줄: 26개 컬럼 헤더(1행) ➔ 반드시 `^` 기호로 연결
   - 세 번째 줄부터: 코드별 데이터 행 ➔ 각 행 반드시 `^` 기호로 연결, 코드 개수만큼 줄 생성 (각 행의 Cost Center는 DB 원본값 그대로 개별 반영)
   - 🚨🚨 **[절대 출력 금지 목록]**: 아래와 같은 문구/텍스트는 어떤 형태로든 절대 출력하지 마.
     - "Unit price 합계", "합계: OOO KRW" 등 금액 합산 결과
     - "반영 완료!", "매칭 완료!", "확인 완료!" 등 작업 완료 알림 문구
     - "템플릿 분석 완료", "검토 중..." 등 진행 상태 멘트
     - 그 외 위 4개 줄(Invoicing Company / 헤더 / 데이터 행들) 이외의 모든 부연 설명, 인사말, 마무리 멘트
   - 위 4개 항목(Invoicing Company, 헤더, 데이터 행)을 제외한 어떤 줄도 답변에 포함되면 안 돼. 검증은 네 머릿속에서만 하고, 결과 텍스트에는 절대 드러내지 마.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    raw_result = response.choices[0].message.content
    clean_text = re.sub(r'```tsv\n|```[a-zA-Z]*\n|```|"""', '', raw_result).strip('\r\n')

    lines = clean_text.split('\n')

    # 실제 헤더 줄("Purchase item"으로 시작)을 찾아서 그 줄부터 끝까지를 원본 그대로 확정
    header_idx = next((i for i, line in enumerate(lines) if line.strip().startswith('Purchase item')), None)

    if header_idx is None:
        tsv_data = clean_text.replace('^', '\t')
    else:
        tsv_data = '\n'.join(lines[header_idx:]).replace('^', '\t')

    # 🚨 파이썬 철벽 방어 맵으로 최종 확정
    inv_company, cost_center = resolve_company_and_cc(file_name, invoice_text, tsv_data, user_keyword)

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
                            tsv_lines = tsv_result.split('\n')  # ← tsv_result 원본은 그대로, 새 리스트만 생성
                            headers = tsv_lines[0].split('\t')
                            desc_idx = next(i for i, h in enumerate(headers) if 'Short description' in h)
                            short_desc = tsv_lines[1].split('\t')[desc_idx].strip()  # ← strip()은 short_desc 복사본에만 적용, tsv_result엔 영향 없음
                        except Exception as e:
                            print(f"⚠️ short_desc 추출 실패: {e}")
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
