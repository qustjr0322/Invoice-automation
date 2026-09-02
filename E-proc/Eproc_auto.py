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

# 🎯 Windows DPI 스케일링 보정
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# 기본 설정 주소 및 이미지 경로 정의
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Cewofh1RBR1zqznDonA1ADjiw4SLosV7JGIpPH916V0/edit?gid=0#gid=0"
TARGET_BUY_URL = "https://valeo.determine.com/t/ui/md/home"

new_req_img_path = r'C:\Project\Eproc_images\new_requisition.png'
invoicing_company_img_path = r'C:\Project\Eproc_images\invoicing_company.png'
ship_to_img_path = r'C:\Project\Eproc_images\ship_to.png'  # 🎯 Ship To 이미지 경로 추가

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
def analyze_invoice_by_price(invoice_text: str, sheet_url: str):
    """고정 지출 템플릿 매칭 + 금액/CostCenter 매칭 규칙 반영 후 (TSV, InvoicingCompany, CostCenter) 반환"""
    
    sheet_id = sheet_url.split('/d/')[1].split('/')[0]
    gid = sheet_url.split('gid=')[1].split('#')[0] if 'gid=' in sheet_url else '0'
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    
    df = pd.read_csv(export_url)
    sheet_csv_text = df.to_csv(index=False, sep='\t')
    
    prompt = f"""
너는 구매 포털 데이터 등록 자동화 매니저야.

[구글 시트 템플릿 DB]:
{sheet_csv_text}

[읽어온 견적서/고지서 파일 내용]:
{invoice_text}

[지시사항]:
1. [읽어온 견적서/고지서 파일 내용]의 서비스 품목/제공업체명 및 최종 청구 금액(숫자)을 확인해.
2. [구글 시트 템플릿 DB]에서 해당 서비스 항목과 가장 일치하는 템플릿 행(Row)을 선택해.
3. 💡 **[금액 수정 규칙]**: 
   - 견적서의 청구 금액과 템플릿의 'Unit price'가 다르다면, **템플릿의 'Unit price' 자리에 실제 견적서의 청구 금액(숫자)을 대신 넣어줘.**
   - 금액이 동일하면 기존 템플릿 금액을 그대로 유지해.
4. 💡 **[Cost Center 매칭 규칙]**:
   - Cost Center가 **OJ1060** 이면 Invoicing Company는 **A13**
   - Cost Center가 **OM1060** 이면 Invoicing Company는 **T58**
   - Cost Center가 **OO1063**, **OO1090**, **YQ1060** 중 하나이면 Invoicing Company는 **Valeo**
5. 선택(및 수정)한 행의 26개 컬럼 헤더(1행)와 데이터(2행)를 탭 구분자(\\t)로 연결된 2줄의 TSV 텍스트로 구성해줘.
6. ⚠️ **[출력 형식 규칙]**:
   - 첫 번째 줄: 판단된 Invoicing Company 단어만 출력 (예: A13 또는 T58 또는 Valeo)
   - 두 번째 줄: 해당 항목의 Cost Center 코드 단어만 출력 (예: OJ1060, OM1060 등)
   - 세 번째 줄 이후: 26개 컬럼 헤더 및 데이터 TSV 2줄
   - 마크다운 코드블록(```), 큰따옴표(\"\"\"), 부연설명은 일절 출력하지 말 것.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )
    
    raw_result = response.choices[0].message.content
    clean_text = re.sub(r'"""|```tsv|```', '', raw_result).strip()
    
    lines = clean_text.split('\n')
    inv_company = lines[0].strip()   # 첫 줄: A13, T58, Valeo 중 하나
    cost_center = lines[1].strip()   # 두 번째 줄: Cost Center 코드
    tsv_data = '\n'.join(lines[2:]).strip()  # 세 번째 줄부터 TSV 데이터
    
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

st.sidebar.header("📁 견적서 파일 첨부")
uploaded_file = st.sidebar.file_uploader("PDF 또는 Excel 파일을 올려주세요", type=["pdf", "xlsx", "xls"])

user_text_input = st.chat_input("또는 견적서 텍스트를 직접 입력하세요...")

invoice_content = None
source_name = None

if uploaded_file is not None:
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
    st.session_state.messages.append({"role": "user", "content": f"[{source_name}] 분석 요청"})
    st.chat_message("user").write(f"[{source_name}] 분석 요청")
    
    with st.chat_message("assistant"):
        with st.spinner("📊 템플릿 매칭, 변동 금액 및 CostCenter 규칙 검토 중..."):
            try:
                # 1) AI 분석, 변동 금액/CostCenter 수정 및 클립보드 복사
                tsv_result, invoicing_company_value, cost_center_value = analyze_invoice_by_price(invoice_content, SHEET_URL)
                pyperclip.copy(tsv_result)
                
                st.success(f"✅ 템플릿 분석 완료! (Invoicing Company: **{invoicing_company_value}**, Cost Center: **{cost_center_value}**)")
                st.code(tsv_result, language="text")
                
                # 2) 구매 사이트 크롬 브라우저로 오픈
                with st.spinner("🌐 크롬 브라우저에서 구매 사이트로 이동합니다..."):
                    browser.open(TARGET_BUY_URL)
                    time.sleep(5)  # 페이지 진입 및 로딩 대기
                
                # 3) new_requisition.png 클릭
                with st.spinner("🖱️ New Requisition 버튼 탐색 중..."):
                    if os.path.exists(new_req_img_path):
                        req_loc = pyautogui.locateCenterOnScreen(new_req_img_path, confidence=0.65, grayscale=True)
                        if req_loc:
                            pyautogui.moveTo(req_loc, duration=0.4)
                            pyautogui.click()
                            st.info("📌 New Requisition 버튼 클릭 완료!")
                            time.sleep(2)  # 페이지 전환 대기
                        else:
                            st.warning("⚠️ 화면에서 'new_requisition.png' 버튼을 찾지 못했습니다.")
                    else:
                        st.error(f"❌ 이미지 파일이 없습니다: {new_req_img_path}")

                # 4) invoicing_company.png 이미지 찾아 클릭 -> 텍스트 직접 타이핑 -> Down + Enter
                with st.spinner(f"⌨️ Invoicing Company('{invoicing_company_value}') 키보드 입력 중..."):
                    if os.path.exists(invoicing_company_img_path):
                        inv_loc = pyautogui.locateCenterOnScreen(invoicing_company_img_path, confidence=0.65, grayscale=True)
                        if inv_loc:
                            pyautogui.moveTo(inv_loc, duration=0.4)
                            pyautogui.click()
                            time.sleep(1)  # 입력창 활성화 대기
                            
                            # 타이핑 방식 (TSV 클립보드 원본 안전하게 보존)
                            pyautogui.write(invoicing_company_value, interval=0.1)
                            time.sleep(5)
                            pyautogui.press('down')
                            time.sleep(0.5)
                            pyautogui.press('enter')
                            time.sleep(3)
                            
                            st.info(f"⌨️ Invoicing Company('{invoicing_company_value}') 선택 완료!")
                        else:
                            st.warning("⚠️ 화면에서 'invoicing_company.png' 버튼을 찾지 못했습니다.")
                    else:
                        st.error(f"❌ 이미지 파일이 없습니다: {invoicing_company_img_path}")

                # 5) Cost Center 입력
                with st.spinner(f"⌨️ Cost Center('{cost_center_value}') 입력 중..."):
                    pyautogui.write(cost_center_value, interval=0.1)
                    time.sleep(2)
                    pyautogui.press('down')
                    time.sleep(1)
                    pyautogui.press('enter')
                    time.sleep(1)
                    
                    st.info(f"⌨️ Cost Center('{cost_center_value}') 타이핑 및 선택 완료!")

                # 🎯 6) ship_to.png 클릭 추가
                with st.spinner("🖱️ Ship To 위치 탐색 및 클릭 중..."):
                    if os.path.exists(ship_to_img_path):
                        ship_loc = pyautogui.locateCenterOnScreen(ship_to_img_path, confidence=0.65, grayscale=True)
                        if ship_loc:
                            pyautogui.moveTo(ship_loc, duration=0.4)
                            pyautogui.click()
                            time.sleep(1)
                            pyautogui.press('down')
                            time.sleep(1)
                            st.info("📌 Ship To 위치 클릭 완료!")
                            
                        else:
                            st.warning("⚠️ 화면에서 'ship_to.png' 버튼을 찾지 못했습니다.")
                    else:
                        st.error(f"❌ 이미지 파일이 없습니다: {ship_to_img_path}")

                response_msg = f"Invoicing Company({invoicing_company_value}), Cost Center({cost_center_value}) 입력 및 Ship To 클릭까지 완료했습니다!"
                st.write(response_msg)
                st.session_state.messages.append({"role": "assistant", "content": response_msg})

            except Exception as e:
                error_msg = f"⚠️ 처리 중 오류가 발생했습니다: {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
