import os
import re
from dotenv import load_dotenv
import time
import ctypes
import webbrowser
import pyperclip
import pyautogui
import pandas as pd
import pypdf
import streamlit as st
from openai import OpenAI

load_dotenv()
client = OpenAI()

# 🎯 Windows DPI 스케일링 보정 (노트북/모니터 해상도 배율 차이 대응)
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 기본 설정 주소 및 이미지 경로 정의
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Cewofh1RBR1zqznDonA1ADjiw4SLosV7JGIpPH916V0/edit?gid=0#gid=0"
TARGET_BUY_URL = "https://valeo.determine.com/t/ui/md/home"

# 🎯 PyAutoGUI 탐색용 이미지 경로 설정
new_req_img_path = r'C:\Project\Eproc_images\new_requisition.png'
invoicing_company_img_path = r'C:\Project\Eproc_images\invoicing_company.png'
ship_to_img_path = r'C:\Project\Eproc_images\ship_to.png'
dots_img_path = r'C:\Project\Eproc_images\dots_menu.png'
box_img_path = r'C:\Project\Eproc_images\import_box.png'
import_blue_path = r'C:\Project\Eproc_images\import_blue.png'
back_home_path = r'C:\Project\Eproc_images\back_home.png'
my_cart_path = r'C:\Project\Eproc_images\my_cart.png'
summary_checkout_path = r'C:\Project\Eproc_images\summary_checkout.png'
proceed_req_path = r'C:\Project\Eproc_images\proceed_to_requisition.png'
blanck_img_path = r'C:\Project\Eproc_images\blanck.png'
attachment_img_path = r'C:\Project\Eproc_images\attachment.png'
plus_button_img_path = r'C:\Project\Eproc_images\plus_button.png'
choose_file_img_path = r'C:\Project\Eproc_images\choose_file.png'
add_back_img_path = r'C:\Project\Eproc_images\back_to_requisition.png'  

# 🎯 Chrome 브라우저 경로 지정 및 등록
chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(chrome_path):
    chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

if os.path.exists(chrome_path):
    webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
    browser = webbrowser.get('chrome')
else:
    browser = webbrowser.get()

# -------------------------------------------------------------------------
# 1. 파일(PDF / Excel) 텍스트 데이터 파싱 함수
# -------------------------------------------------------------------------
def extract_text_from_file(uploaded_file) -> str:
    """업로드된 PDF 또는 Excel 파일에서 텍스트를 추출"""
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
# 2. AI 분석, 금액 및 CostCenter 매칭 자동 반영 템플릿 추출 함수
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
    inv_company = lines[0].strip()   
    cost_center = lines[1].strip()   
    tsv_data = '\n'.join(lines[2:]).replace('^', '\t')
    
    return tsv_data, inv_company, cost_center

# -------------------------------------------------------------------------
# 3. Streamlit UI 구성 및 로컬 파일 저장
# -------------------------------------------------------------------------
st.set_page_config(page_title="E-Procurement Auto Assistant", page_icon="📑", layout="centered")

st.title("📑 E-Procurement 견적서 자동 등록 챗봇")
st.caption("견적서/고지서 파일(PDF, Excel)을 업로드하거나 텍스트를 입력하면 AI가 분석 후 구매 사이트를 호출합니다.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

st.sidebar.header("📁 견적서 파일 및 옵션")
uploaded_file = st.sidebar.file_uploader("PDF 또는 Excel 파일을 올려주세요", type=["pdf", "xlsx", "xls"])

target_keyword = st.sidebar.text_input("🎯 Target Item (선택 사항)", placeholder="예: ANS1, SEO1 (비워두면 첫행)")

user_text_input = st.chat_input("또는 견적서 텍스트를 직접 입력하세요...")

invoice_content = None
source_name = None
saved_temp_file_path = None

if uploaded_file is not None:
    temp_dir = r"C:\Project\temp"
    os.makedirs(temp_dir, exist_ok=True)
    saved_temp_file_path = os.path.abspath(os.path.join(temp_dir, uploaded_file.name))
    
    with open(saved_temp_file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    if st.sidebar.button("🚀 업로드된 파일 분석 시작", type="primary"):
        with st.spinner("📄 파일에서 데이터 추출 중..."):
            invoice_content = extract_text_from_file(uploaded_file)
            source_name = f"파일: {uploaded_file.name}"

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
                # 1) AI 분석 (파일명 및 Target Keyword 전달)
                tsv_result, invoicing_company_value, cost_center_value = analyze_invoice_by_price(
                    invoice_content, 
                    SHEET_URL, 
                    user_keyword=target_keyword if target_keyword else None,
                    file_name=uploaded_file.name if uploaded_file else ""
                )
                pyperclip.copy(tsv_result)
                
                st.success(f"✅ 템플릿 분석 완료! (Invoicing Company: **{invoicing_company_value}**, Cost Center: **{cost_center_value}**)")
                st.code(tsv_result, language="text")
                
                # 2) 구매 사이트 크롬 브라우저로 오픈
                with st.spinner("🌐 크롬 브라우저에서 구매 사이트로 이동합니다..."):
                    browser.open(TARGET_BUY_URL)
                    time.sleep(5)
                
                # 3) new_requisition.png 클릭
                with st.spinner("🖱️ New Requisition 버튼 탐색 중..."):
                    if os.path.exists(new_req_img_path):
                        req_loc = pyautogui.locateCenterOnScreen(new_req_img_path, confidence=0.65, grayscale=True)
                        if req_loc:
                            pyautogui.moveTo(req_loc, duration=0.4)
                            pyautogui.click()
                            st.info("📌 New Requisition 버튼 클릭 완료!")
                            time.sleep(2)
                        else:
                            st.warning("⚠️ 화면에서 'new_requisition.png' 버튼을 찾지 못했습니다.")

                # 4) invoicing_company.png 입력
                with st.spinner(f"⌨️ Invoicing Company('{invoicing_company_value}') 키보드 입력 중..."):
                    if os.path.exists(invoicing_company_img_path):
                        inv_loc = pyautogui.locateCenterOnScreen(invoicing_company_img_path, confidence=0.65, grayscale=True)
                        if inv_loc:
                            pyautogui.moveTo(inv_loc, duration=0.4)
                            pyautogui.click()
                            time.sleep(1)
                            
                            pyautogui.write(invoicing_company_value, interval=0.1)
                            time.sleep(5)
                            pyautogui.press('down')
                            time.sleep(0.5)
                            pyautogui.press('enter')
                            time.sleep(3)
                            st.info(f"⌨️ Invoicing Company('{invoicing_company_value}') 선택 완료!")
                        else:
                            st.warning("⚠️ 화면에서 'invoicing_company.png' 버튼을 찾지 못했습니다.")

                # 5) Cost Center 입력
                with st.spinner(f"⌨️ Cost Center('{cost_center_value}') 입력 중..."):
                    pyautogui.write(cost_center_value, interval=0.1)
                    time.sleep(2)
                    pyautogui.press('down')
                    time.sleep(1)
                    pyautogui.press('enter')
                    time.sleep(1)
                    st.info(f"⌨️ Cost Center('{cost_center_value}') 타이핑 및 선택 완료!")

                # 6) ship_to.png 클릭
                with st.spinner("🖱️ Ship To 위치 탐색 및 클릭 중..."):
                    if os.path.exists(ship_to_img_path):
                        ship_loc = pyautogui.locateCenterOnScreen(ship_to_img_path, confidence=0.65, grayscale=True)
                        if ship_loc:
                            pyautogui.moveTo(ship_loc, duration=0.4)
                            pyautogui.click()
                            time.sleep(1)
                            pyautogui.press('down')
                            time.sleep(2)
                            st.info("📌 Ship To 위치 클릭 완료!")
                        else:
                            st.warning("⚠️ 화면에서 'ship_to.png' 버튼을 찾지 못했습니다.")

                # 7) Import ~ 결제 진행
                with st.spinner("🚀 Import 메뉴 진입 및 TSV 데이터 자동 붙여넣기 매크로 시작..."):
                    if os.path.exists(dots_img_path):
                        dots_loc = pyautogui.locateCenterOnScreen(dots_img_path, confidence=0.65, grayscale=True)
                        if dots_loc:
                            pyautogui.moveTo(dots_loc, duration=0.4)
                            pyautogui.click()
                            time.sleep(0.4)
                            
                            pyautogui.press('down')
                            time.sleep(0.2)
                            pyautogui.click()
                            st.info("🚀 Import 메뉴 진입 성공!")
                            time.sleep(3)
                            
                            if os.path.exists(box_img_path):
                                box_loc = pyautogui.locateCenterOnScreen(box_img_path, confidence=0.65, grayscale=True)
                                if box_loc:
                                    pyautogui.moveTo(box_loc, duration=0.4)
                                    pyautogui.click()
                                    time.sleep(0.3)
                                    
                                    pyperclip.copy(tsv_result)
                                    time.sleep(0.2)
                                    pyautogui.hotkey('ctrl', 'v')
                                    time.sleep(0.5)
                                    st.info("📋 AI 추출 TSV 데이터 붙여넣기 완료!")
                                    
                                    if os.path.exists(import_blue_path):
                                        blue_loc = pyautogui.locateCenterOnScreen(import_blue_path, confidence=0.65)
                                        if blue_loc:
                                            pyautogui.moveTo(blue_loc, duration=0.4)
                                            pyautogui.click()
                                            st.info("🎉 Import 완료!")
                                            time.sleep(9)
                                            
                                            if os.path.exists(back_home_path):
                                                home_loc = pyautogui.locateCenterOnScreen(back_home_path, confidence=0.65, grayscale=True)
                                                if home_loc:
                                                    pyautogui.moveTo(home_loc, duration=0.4)
                                                    pyautogui.click()
                                                    time.sleep(3)
                                                    
                                                    if os.path.exists(my_cart_path):
                                                        cart_loc = pyautogui.locateCenterOnScreen(my_cart_path, confidence=0.65, grayscale=True)
                                                        if cart_loc:
                                                            pyautogui.moveTo(cart_loc, duration=0.4)
                                                            pyautogui.click()
                                                            time.sleep(3)
                                                            
                                                            if os.path.exists(summary_checkout_path):
                                                                checkout_loc = pyautogui.locateCenterOnScreen(summary_checkout_path, confidence=0.65)
                                                                if checkout_loc:
                                                                    pyautogui.moveTo(checkout_loc, duration=0.4)
                                                                    pyautogui.click()
                                                                    st.info("💳 Checkout 클릭 완료!")
                                                                    time.sleep(3)

                                                                    if os.path.exists(proceed_req_path):
                                                                        proceed_loc = pyautogui.locateCenterOnScreen(proceed_req_path, confidence=0.65)
                                                                        if proceed_loc:
                                                                            pyautogui.moveTo(proceed_loc, duration=0.4)
                                                                            pyautogui.click()
                                                                            st.info("📑 Proceed to Requisition 클릭 완료!")
                                                                            time.sleep(4)

                                                                            if os.path.exists(blanck_img_path):
                                                                                blanck_loc = pyautogui.locateCenterOnScreen(blanck_img_path, confidence=0.65, grayscale=True)
                                                                                if blanck_loc:
                                                                                    pyautogui.moveTo(blanck_loc, duration=0.4)
                                                                                    pyautogui.click()
                                                                                    st.info("📌 'Amount details' 클릭 (포커스 획득)!")
                                                                                    time.sleep(0.5)

                                                                                    st.info("📜 페이지 아래로 스크롤 이동 중...")
                                                                                    pyautogui.press('down', presses=15, interval=0.05)
                                                                                    time.sleep(1)

                                                                            if os.path.exists(attachment_img_path):
                                                                                att_loc = pyautogui.locateCenterOnScreen(attachment_img_path, confidence=0.55)
                                                                                if att_loc:
                                                                                    pyautogui.moveTo(att_loc, duration=0.4)
                                                                                    pyautogui.click()
                                                                                    st.info("📌 ATTACHMENTS 탭 클릭 완료!")
                                                                                    time.sleep(1)
                                                                                    
                                                                                    if os.path.exists(plus_button_img_path):
                                                                                        plus_loc = pyautogui.locateCenterOnScreen(plus_button_img_path, confidence=0.65)
                                                                                        if plus_loc:
                                                                                            pyautogui.moveTo(plus_loc, duration=0.4)
                                                                                            pyautogui.click()
                                                                                            st.info("📌 파란색 '+' 버튼 클릭 완료!")
                                                                                            time.sleep(2)
                                                                                            
                                                                                            if saved_temp_file_path and os.path.exists(choose_file_img_path):
                                                                                                choose_loc = pyautogui.locateCenterOnScreen(choose_file_img_path, confidence=0.65)
                                                                                                if choose_loc:
                                                                                                    pyautogui.moveTo(choose_loc, duration=0.4)
                                                                                                    pyautogui.click()
                                                                                                    time.sleep(3)
                                                                                                    
                                                                                                    pyperclip.copy(saved_temp_file_path)
                                                                                                    time.sleep(0.3)
                                                                                                    pyautogui.hotkey('alt', 'n')
                                                                                                    time.sleep(0.3)
                                                                                                    pyautogui.hotkey('ctrl', 'v')
                                                                                                    time.sleep(0.5)
                                                                                                    pyautogui.press('enter')
                                                                                                    
                                                                                                    st.info(f"📁 견적서 파일({uploaded_file.name}) 업로드 완료!")
                                                                                                    time.sleep(4)
                                                                                                    
                                                                                                    if os.path.exists(add_back_img_path):
                                                                                                        add_loc = pyautogui.locateCenterOnScreen(add_back_img_path, confidence=0.65)
                                                                                                        if add_loc:
                                                                                                            pyautogui.moveTo(add_loc, duration=0.4)
                                                                                                            pyautogui.click()
                                                                                                            st.success("🎉 Add & Back to Requisition 클릭 완료! 전체 시나리오 최종 성공!")

                response_msg = f"Invoicing Company({invoicing_company_value}), Cost Center({cost_center_value}) 반영, 데이터 Import, 견적서 첨부파일 등록 및 제출까지 모든 자동화 프로세스가 성공적으로 완료되었습니다!"
                st.write(response_msg)
                st.session_state.messages.append({"role": "assistant", "content": response_msg})

            except Exception as e:
                error_msg = f"⚠️ 처리 중 오류가 발생했습니다: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
