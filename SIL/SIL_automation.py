import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import pandas as pd
from pypdf import PdfReader
import fitz  # PyMuPDF
import base64
import re
import time
import pyautogui
import pyperclip

# --- 셀레니움 관련 모듈 추가 ---
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

load_dotenv()

# 페이지 기본 설정
st.set_page_config(page_title="E-Procurement Auto Assistant", page_icon="📑", layout="centered")

# --- 1. 구글 시트 템플릿 읽기 ---
def get_template_data():
    try:
        sheet_id = '1j_uveQsax4_Lz_aoyhViSJk769W7lkZVyUZ107-9wcw'
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(csv_url)
        all_rows = [df.columns.tolist()] + df.fillna("").values.tolist()
        return all_rows
    except Exception as e:
        st.error(f"템플릿 데이터 읽기 오류: {e}")
        return None

# --- 2. 매크로 자동화 함수 (UC Chrome + PyAutoGUI) ---
def run_purchase_macro(supplier, comment_kw, invoice_no, date, GL_Account, amount, cost_center, internal_order, bu_code='A13', req_type='', category='', pdf_file_path=None):
    driver = None
    try:
        st.toast("🧹 기존 크롬 프로세스 정리 및 설정 중...", icon="🔄")
        os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")                
        time.sleep(1.0)
        
        profile_path = r'C:\ChromeProfile_Auto_SIL'
        lock_file = os.path.join(profile_path, 'SingletonLock')
        if os.path.exists(lock_file):
            try: os.remove(lock_file)
            except: pass

        options = uc.ChromeOptions()
        options.add_argument(f'--user-data-dir={profile_path}')
        options.add_argument('--profile-directory=Default')
        options.add_argument('--no-first-run')
        options.add_argument('--no-service-autorun')
        options.add_argument('--start-maximized') 
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--remote-debugging-port=0')

        try:
            driver = uc.Chrome(options=options, version_main=152, use_subprocess=True) 
        except Exception as uc_e:
            return False, f"⚠️ 크롬을 제어할 수 없습니다. 열려있는 '크롬 창'을 닫고 시도해주세요! (오류: {uc_e})"
        
        target_url = "https://financesscportal.appengine.valeo.com/request/new?form=11&detail=false"
        driver.get(target_url)
        
        print("🚀 프로세스 시작 및 SSO 로그인 대기 중...")
        st.toast("🌐 구매 포털 접속 중... SSO 인증을 대기합니다.", icon="🚀")

        wait = WebDriverWait(driver, 60)
        try:
            wait.until(EC.url_contains("financesscportal.appengine.valeo.com"))
            print("✅ SSO 통과 및 목적지 URL 진입 성공")
        except:
            return False, "❌ SSO 로그인 대기 시간 초과! 직접 화면에서 로그인을 완료해주거나 세션을 확인하세요."

        time.sleep(3)
        
        st.toast("⏳ 7초 안에 열린 창에서 'BU code' 입력칸을 클릭하세요!", icon="⚠️")
        time.sleep(7)

        # 1. BU Code 
        pyautogui.write(str(bu_code).lower() if bu_code else 'a13', interval=0.1) 
        pyautogui.press('tab', presses=1) 
        time.sleep(1.0)
        
        # 2. Overseas/Domestic
        pyautogui.write('d', interval=0.1) 
        pyautogui.press('tab', presses=1)
        time.sleep(1.0)
        
        # 3. Type 
        req_char = str(req_type)[0].lower() if req_type else 'd'
        pyautogui.write(req_char, interval=0.1) 
        pyautogui.press('enter', presses=1)
        time.sleep(0.2)
        pyautogui.press('tab', presses=1)
        time.sleep(1.0) 
        
        # 4. Category
        pyautogui.write(str(category) if category else 'IS', interval=0.1) 
        pyautogui.press('tab', presses=1)
        time.sleep(1.0)
        
        # 5. Request Comments 
        pyperclip.copy(str(comment_kw))
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.1)
        pyautogui.press('tab', presses=1) 
        time.sleep(0.3)

        # 6. Supplier Name 
        pyautogui.write(str(supplier), interval=0.05)
        time.sleep(2.0)
        pyautogui.press('down')
        time.sleep(0.2)
        pyautogui.press('enter')
        time.sleep(0.3)
        pyautogui.press('tab', presses=2) 
        time.sleep(0.3)

        # 7. Invoice Number
        pyautogui.write(str(invoice_no), interval=0.05)
        pyautogui.press('tab', presses=1)
        time.sleep(0.3)

        # 8. Invoice Date
        pyautogui.write(str(date), interval=0.05)
        pyautogui.press('tab', presses=2)
        time.sleep(0.3)

        # 9. Cost center 선택
        pyautogui.write('c', interval=0.1)
        pyautogui.press('tab', presses=6) 
        time.sleep(0.3)

        # 10. G/L Account Number
        pyautogui.write(str(GL_Account), interval=0.05)
        pyautogui.press('tab', presses=1)
        time.sleep(0.3)

        # 11. Amount
        pyautogui.write(str(amount), interval=0.05)
        pyautogui.press('tab', presses=1)
        time.sleep(0.3)

        # 12. Currency
        pyautogui.write('KRW', interval=0.1)
        pyautogui.press('tab', presses=1)
        time.sleep(0.3)

        # 13. Cost Center 값
        pyautogui.write(str(cost_center), interval=0.05)
        pyautogui.press('tab', presses=1)
        time.sleep(0.3)

        # 14. Internal Order
        pyautogui.write(str(internal_order), interval=0.05)
        pyautogui.press('tab', presses=2)
        time.sleep(0.3)

        # 15. Upload invoice
        pyautogui.press('enter', presses=2)
        time.sleep(2)

        if pdf_file_path and os.path.exists(pdf_file_path):
            abs_path = os.path.abspath(pdf_file_path)
            pyperclip.copy(abs_path)
            time.sleep(0.5)
            
            pyautogui.hotkey('alt', 'n')
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(0.8)

        print("✅ 진행 완료! 창을 닫지 않고 유지합니다.")
        # 🚨 finally 블록을 삭제하여 창이 안 닫히게 설정 됨
        return True, "✅ 구매 시스템 자동 입력 및 PDF 파일 업로드가 완료되었습니다! (직접 검토 후 제출해주세요)"

    except Exception as e:
        if driver:
            driver.quit()
        return False, f"❌ 매크로 오류 발생: {str(e)}"
    
    # finally 구문을 삭제하여 정상 완료 시 창을 열어둡니다.

# --- 3. UI 및 OpenAI 세팅 ---
with st.sidebar:
    st.header("📁 파일 업로드 및 분석")
    openai_api_key = os.getenv('OPENAI_API_KEY') 
    uploaded_file = st.file_uploader("인보이스(PDF)를 업로드하세요", type=["pdf"])
    st.markdown("---")
    
    # 💡 분석 시작 버튼 추가
    is_analyze_clicked = st.button("🚀 업로드된 파일 분석 시작", type="primary", use_container_width=True)

st.title("📑 인보이스 자동 추출 & 구매 등록 봇")
st.caption("사이드바에서 파일을 업로드하고 '분석 시작'을 누르거나 아래 채팅창에 입력하세요.")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "PDF를 업로드한 후 좌측의 **'🚀 분석 시작'** 버튼을 클릭하세요."}]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

def get_pdf_text(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text.strip()

# --- 4. 메인 처리 로직 (버튼 or 채팅 동시 지원) ---
user_text_input = st.chat_input("추가 요청사항을 입력하거나 텍스트를 붙여넣으세요...")

# 분석 버튼을 눌렀거나, 엔터를 쳤을 때 시작
if is_analyze_clicked or user_text_input:
    if not openai_api_key:
        st.info("API 키를 추가해주세요.")
        st.stop()

    client = OpenAI(api_key=openai_api_key)
    
    # 프롬프트 설정 (버튼 클릭시 기본 메세지 송출)
    prompt = user_text_input if user_text_input else "업로드된 파일 분석을 요청합니다."
    
    st.session_state.messages.append({"role": "user", "content": prompt}) 
    st.chat_message("user").write(prompt) 
    
    if uploaded_file is not None:
        with st.spinner("📄 파일을 분석하고 구글 시트와 대조 중입니다..."):
            save_dir = os.path.join(os.getcwd(), "temp_downloads")
            os.makedirs(save_dir, exist_ok=True)
            saved_pdf_path = os.path.join(save_dir, uploaded_file.name)
            
            with open(saved_pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            pdf_text = get_pdf_text(uploaded_file)
            
            system_instruction = """
당신은 세금계산서, 거래명세서, 청구서 분석 전문가입니다.
주어진 파일(PDF 또는 이미지)에서 정보를 정확히 추출하여 반드시 아래와 같은 JSON 형식으로만 응답하세요.

[⚠️ 절대 규칙 - 공급자(Supplier) 추출]
1. 'supplier': 돈을 청구하고 제공하는 '공급자(판매자)' 상호명만 추출하세요.
   - '발레오', '발레오전장시스템', 'Valeo'는 구매자(공급받는 자)이므로 절대로 supplier에 넣지 마세요.
   - 문서 내 '공급자' 또는 'ANIT', '주식회사 아남아이티', '이씨뱅크', 'LG U+', 'SK브로드밴드' 등 실제 돈을 받는 발행업체 이름을 적으세요.

[⚠️ 승인번호 / 고객번호(invoice number) 정밀 지시]
2. 'invoice number': 
   - **'220-81-39938' 같은 공급자/공급받는자 사업자등록번호는 절대로 invoice number로 가져오지 마세요.**
   - 문서 내의 '국세청 승인번호', '고객번호'(예: 511808413119, 399001198525 등), 또는 '승인/관리/청구 번호'를 최우선으로 추출하세요.
   - 🚨 [초정밀 스캔 요구] 국세청 승인번호나 아남아이티 등의 승인번호는 보통 **24자리**의 긴 영문/숫자 조합입니다 (예: 2026091541000008000b55Ip).
   - 절대 중간 글자(41, 8000b 등)를 건너뛰거나 0으로 축약하지 마세요. 이미지를 세밀하게 관찰하여 24자리 원본 그대로 대소문자까지 완벽하게 추출하세요.

[⚠️ 기타 추출 지시사항]
3. 'comment_keyword': '품목', '청구명', '이용서비스' 내용의 핵심 키워드 (예: 'U+ 오피스넷', 'Lease', 'Server', 'WEBLC' 등)
4. 'date': 작성일자 또는 청구일자 (YYYY-MM-DD 형식)
5. 'amount': 부가세 포함 최종 이번달 합계/납부 금액 (숫자만 추출, 예: 110000)

{
  "supplier": "공급자 업체명 (발레오 제외)",
  "comment_keyword": "품목 대표 키워드",
  "invoice number": "승인번호 또는 고객/청구번호 (사업자번호 제외)",
  "date": "발행/작성 날짜",
  "amount": "합계 금액",
  "gl_account": "",
  "cost_center": "",
  "internal_order": ""
}
"""
            doc = fitz.open(saved_pdf_path)
            image_contents = []
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                base64_image = base64.b64encode(img_data).decode('utf-8')
                image_contents.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                    "detail" : "high"
                })

            user_msg = [{"type": "text", "text": f"첨부된 인보이스/거래명세서 이미지에서 정보를 읽어 정밀 추출해주세요. 사용자 요청: {prompt}"}] + image_contents
            messages_for_api = [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_msg}
            ]

            response = client.chat.completions.create(
                model="gpt-4o",
                temperature=0.0,
                response_format={ "type": "json_object" },
                messages=messages_for_api
            ) 
            msg = response.choices[0].message.content
            
            try:
                data = json.loads(msg) 
                supplier = data.get('supplier', '-').strip()
                comment_kw = data.get('comment_keyword', '-').strip()
                raw_invoice_no = data.get('invoice number', '-').strip()
                raw_date = data.get('date', '-').strip()
                amount = data.get('amount', '-').strip()
                
                # 기본값 설정
                gl_account = data.get('gl_account', '61402100').strip()
                cost_center = data.get('cost_center', 'OJ1060').strip()
                internal_order = data.get('internal_order', '131900000441').strip()
                supplier_code = ""
                final_comment_kw = comment_kw
                req_type = ""
                category_val = ""
                bu_code = "A13"

                invoice_no = re.sub(r'(2026\d{4})A', r'\141', raw_invoice_no)
                invoice_no = re.sub(r'a[0oO]?wcc$', 'aowcc', invoice_no, flags=re.IGNORECASE)
                if 'aowcc' not in invoice_no.lower() and 'wcc' in invoice_no.lower():
                    invoice_no = re.sub(r'a?0*wcc$', 'aowcc', invoice_no, flags=re.IGNORECASE)

                if "u+" in supplier.lower() or "lg" in supplier.lower() or "유플러스" in supplier:
                    if "511808413119" in pdf_text or "511808413119" in raw_invoice_no:
                        invoice_no = "511808413119"
                    elif "399001198525" in pdf_text or "399001198525" in raw_invoice_no:
                        invoice_no = "399001198525"

                date_digits = re.sub(r'[^0-9]', '', raw_date)
                if len(date_digits) == 8:
                    date = f"{date_digits[:4]}-{date_digits[4:6]}-{date_digits[6:]}"
                else:
                    date = raw_date
                
                all_rows = get_template_data()
                
                if all_rows:
                    clean_supplier = re.sub(r'\(주\)|주식회사|\s+|유플러스', 'u+', supplier).lower()
                    extracted_words = re.findall(r'[A-Za-z0-9]+', comment_kw)

                    matched_rows = []
                    for idx, row in enumerate(all_rows, start=1):
                        if idx == 1: continue 
                        sheet_company_name = str(row[0]).strip() if len(row) > 0 else ""
                        clean_sheet_company = re.sub(r'\(주\)|주식회사|\s+|유플러스', 'u+', sheet_company_name).lower()

                        if clean_supplier and clean_sheet_company and (clean_supplier in clean_sheet_company or clean_sheet_company in clean_supplier):
                            matched_rows.append(row)

                    if matched_rows:
                        best_template = None
                        for row in matched_rows:
                            existing_inv_no = str(row[7]).strip() if len(row) > 7 else ""
                            existing_amount = str(row[10]).strip() if len(row) > 10 else ""
                            clean_existing_amt = re.sub(r'[^0-9]', '', existing_amount)
                            clean_current_amt = re.sub(r'[^0-9]', '', amount)

                            if (existing_inv_no and invoice_no and existing_inv_no.strip() == invoice_no.strip()) or \
                               (clean_existing_amt and clean_current_amt and clean_existing_amt == clean_current_amt):
                                best_template = row
                                break

                        if not best_template:
                            translation_map = {
                                "유지보수": ["maintenance", "support", "maint"],
                                "사용료": ["fee", "using", "use"],
                                "리스": ["lease", "rental"],
                                "청구": ["lease", "fee", "claim"],
                                "리소스": ["lease", "server"],
                                "회선": ["line", "internet", "network"],
                                "임차료": ["rent", "rental", "fee"],
                                "납부": ["line", "internet", "network", "skb", "rsm"],
                                "요금": ["line", "internet", "fee", "skb"],
                                "통신": ["line", "internet", "network"],
                                "오피스넷": ["valeonet4", "internet", "line"]
                            }
                            
                            for row in matched_rows:
                                sheet_comment = str(row[5]).strip() if len(row) > 5 else ""
                                comment_kw_lower = comment_kw.lower()
                                sheet_comment_lower = sheet_comment.lower()

                                is_kw_matched = False
                                for kr_kw, en_kws in translation_map.items():
                                    if kr_kw in comment_kw_lower and any(en_kw in sheet_comment_lower for en_kw in en_kws):
                                        is_kw_matched = True
                                        break

                                if not is_kw_matched:
                                    for word in extracted_words:
                                        if len(word) >= 2 and word.lower() in sheet_comment_lower:
                                            is_kw_matched = True
                                            break

                                if is_kw_matched:
                                    best_template = row
                                    break

                        if not best_template:
                            best_template = matched_rows[0]

                        if best_template:
                            if len(best_template) > 1 and str(best_template[1]).strip(): bu_code = str(best_template[1]).strip()
                            if len(best_template) > 3 and str(best_template[3]).strip(): req_type = str(best_template[3]).strip()
                            if len(best_template) > 4 and str(best_template[4]).strip(): category_val = str(best_template[4]).strip()
                            if len(best_template) > 5 and str(best_template[5]).strip(): final_comment_kw = str(best_template[5]).strip()
                            if len(best_template) > 6 and str(best_template[6]).strip(): supplier_code = str(best_template[6]).strip()
                            if len(best_template) > 9 and str(best_template[9]).strip(): gl_account = str(best_template[9]).strip()
                            if len(best_template) > 11 and str(best_template[11]).strip(): cost_center = str(best_template[11]).strip()
                            if len(best_template) > 12 and str(best_template[12]).strip(): internal_order = str(best_template[12]).strip()

                display_msg = f"""### 📄 인보이스 정보 추출 완료! (템플릿 매칭 적용)
* **업체명 (코드)**: {supplier} ({supplier_code if supplier_code else '수동입력 필요'})
* **품목/서비스**: {final_comment_kw}
* **요청 Type**: {req_type if req_type else '기본값'}
* **카테고리(Category)**: {category_val if category_val else '기본값'}
* **승인 번호**: {invoice_no}
* **발행 날짜**: {date}
* **금액**: {amount}
* **GL Account**: {gl_account} | **Cost Center**: {cost_center}

✅ 매크로 실행 준비가 완료되었습니다! 아래의 실행 버튼을 눌러주세요.
---
"""
                st.session_state["latest_invoice_data"] = {
                    "supplier": supplier_code if supplier_code else supplier,
                    "comment_kw": final_comment_kw,
                    "invoice_no": invoice_no,
                    "date": date,
                    "GL_Account": gl_account,
                    "amount": amount,
                    "cost_center": cost_center,
                    "internal_order": internal_order,
                    "bu_code": bu_code,
                    "req_type": req_type,
                    "category": category_val,
                    "pdf_path": saved_pdf_path
                }

            except Exception as e:
                display_msg = f"❌ AI 응답 해석 오류: `{e}`"

            st.session_state.messages.append({"role": "assistant", "content": display_msg}) 
            st.chat_message("assistant").write(display_msg)
    else:
        # 파일 업로드 안하고 분석 요청했을 때의 방어 로직
        msg = "⚠️ 파일이 첨부되지 않았습니다. 사이드바에서 PDF 파일을 먼저 업로드해주세요."
        st.session_state.messages.append({"role": "assistant", "content": msg})
        st.chat_message("assistant").write(msg)

# --- 5. 구매 시스템 자동 입력 버튼 ---
if "latest_invoice_data" in st.session_state:
    st.markdown("---")
    st.subheader("🖥️ 사내 구매 시스템 자동 입력")
    st.info("버튼 클릭 후 브라우저가 열리면 7초 이내에 'BU code' 입력칸을 클릭해주세요! (영문 자판 필수)")
    if st.button("🚀 자동 등록(PyAutoGUI) 실행", type="secondary"):
        inv = st.session_state["latest_invoice_data"]
        with st.spinner("매크로 실행 중... 완료 시까지 마우스와 키보드를 조작하지 마세요!"):
            success, result_msg = run_purchase_macro(
                supplier=inv["supplier"], 
                comment_kw=inv["comment_kw"],
                invoice_no=inv["invoice_no"],
                date=inv["date"],
                GL_Account=inv["GL_Account"],
                amount=inv["amount"],
                cost_center=inv["cost_center"],
                internal_order=inv["internal_order"],
                bu_code=inv.get("bu_code", "A13"),
                req_type=inv.get("req_type", ""),
                category=inv.get("category", ""),
                pdf_file_path=inv.get("pdf_path")
            )
            if success: st.success(result_msg)
            else: st.error(result_msg)
