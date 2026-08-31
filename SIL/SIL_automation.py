import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import gspread
from pypdf import PdfReader
import webbrowser
import pyautogui
import time
import tempfile
import pyperclip

load_dotenv()

# --- 1. 구글 시트 연결 설정 ---
worksheet = None
try:
    gc = gspread.oauth(
        credentials_filename='client_secret.json',
        authorized_user_filename='authorized_user.json'
    )
    sheet_url = 'https://docs.google.com/spreadsheets/d/1j_uveQsax4_Lz_aoyhViSJk769W7lkZVyUZ107-9wcw/edit'
    worksheet = gc.open_by_url(sheet_url).sheet1
except Exception as e:
    st.error(f"구글 시트 연동 오류: {e}")

# --- 2. 매크로 자동화 함수 ---
def run_purchase_macro(supplier, comment_kw, invoice_no, date, GL_Account, amount, cost_center, internal_order, pdf_file_path=None):
    try:
        target_url = "https://financesscportal.appengine.valeo.com/request/new?form=11&detail=false"
        webbrowser.open(target_url)
        
        st.toast("⏳ 7초 안에 열린 창에서 'BU code' 입력칸을 클릭하세요!", icon="⚠️")
        time.sleep(7)
        
        # 1. BU Code
        pyautogui.write('a13', interval=0.1) 
        pyautogui.press('tab', presses=1) 
        time.sleep(1.0)
        
        # 2. Overseas/Domestic
        pyautogui.write('d', interval=0.1) 
        pyautogui.press('tab', presses=1)
        time.sleep(1.0)
        
        # 3. Type
        pyautogui.write('d', interval=0.1) 
        pyautogui.press('enter', presses=1)
        time.sleep(0.2)
        pyautogui.press('tab', presses=1)
        time.sleep(1.0) 
        
        # 4. Category
        pyautogui.write('IS', interval=0.1) 
        pyautogui.press('tab', presses=1)
        time.sleep(1.0)
        
        # 5. Request Comments 
        pyautogui.write(str(comment_kw), interval=0.05)
        pyautogui.press('tab', presses=1) 
        time.sleep(0.3)
        
        # 6. Supplier Name (업체 코드 기입)
        pyautogui.write(str(supplier), interval=0.05)
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

        # 15. Upload invoice 버튼 클릭 (윈도우 파일 탐색기 열기)
        pyautogui.press('enter', presses=2)
        time.sleep(2)

        # 16. PDF 파일 경로 자동 입력 및 선택
        if pdf_file_path and os.path.exists(pdf_file_path):
            # 절대 경로로 변환
            abs_path = os.path.abspath(pdf_file_path)
            pyperclip.copy(abs_path)
            time.sleep(0.5)
            
            # 파일 이름 입력 칸 포커스 강제 지정 (Alt + N 후 Ctrl + A)
            pyautogui.hotkey('alt', 'n')
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            
            # 경로 붙여넣기 및 엔터
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.5)
            pyautogui.press('enter')
            time.sleep(0.8)
                
        return True, "✅ 구매 시스템 자동 입력 및 PDF 파일 업로드가 완료되었습니다!"
        
    except Exception as e:
        return False, f"❌ 매크로 실행 중 오류 발생: {str(e)}"

# --- 3. UI 및 사이드바 설정 ---
with st.sidebar:
    openai_api_key = os.getenv('OPENAI_API_KEY') 
    st.markdown("---")
    uploaded_file = st.file_uploader("인보이스(PDF)를 업로드하세요", type=["pdf"])

st.title("💬 인보이스 자동 추출 & 구매 시스템 등록 봇")

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": "PDF 업로드 후 '정보 추출해서 시트에 넣어줘'라고 입력해보세요!"}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

def get_pdf_text(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

# --- 4. 메인 대화 및 처리 로직 ---
if prompt := st.chat_input():
    if not openai_api_key:
        st.info("Please add your OpenAI API key to continue.")
        st.stop()

    client = OpenAI(api_key=openai_api_key)
    
    st.session_state.messages.append({"role": "user", "content": prompt}) 
    st.chat_message("user").write(prompt) 
    
    messages_for_api = st.session_state.messages.copy()
    
    if uploaded_file is not None:
        # 임시 폴더 생성 및 원본 파일명 유지 저장
        save_dir = os.path.join(os.getcwd(), "temp_downloads")
        os.makedirs(save_dir, exist_ok=True)
        
        # 원본 파일명(uploaded_file.name) 그대로 파일 경로 지정
        saved_pdf_path = os.path.join(save_dir, uploaded_file.name)
        
        with open(saved_pdf_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        pdf_text = get_pdf_text(uploaded_file)
        
        system_instruction = """
당신은 인보이스 분석 전문가입니다.
주어진 텍스트에서 정보를 추출하여 반드시 아래와 같은 JSON 형식으로만 응답하세요. 

[⚠️ 지시사항]
1. 'supplier'에는 돈을 받는 공급자(판매자)의 이름만 가져오세요. ('발레오' 관련 이름 제외)
2. 'comment_keyword'에는 청구된 서비스나 품목 항목의 핵심 단어를 가져오세요.

{
  "supplier": "공급자 업체명",
  "comment_keyword": "청구 서비스/품목 키워드",
  "invoice number": "승인 번호 (납부번호)",
  "date": "발행 날짜",
  "amount": "금액 (숫자만 또는 숫자+화폐)",
  "gl_account": "G/L 계정 번호 (모르면 빈값)",
  "cost_center": "Cost Center 번호 (모르면 빈값)",
  "internal_order": "Internal Order 번호 (모르면 빈값)"
}
"""
        messages_for_api = [{"role": "system", "content": system_instruction}] + st.session_state.messages[:-1]
        combined_content = f"--- [PDF 문서 내용] ---\n{pdf_text}\n\n사용자 요청: {prompt}"
        messages_for_api.append({"role": "user", "content": combined_content})

        response = client.chat.completions.create(
            model="gpt-4o", 
            response_format={ "type": "json_object" },
            messages=messages_for_api
        ) 
        msg = response.choices[0].message.content
        
        try:
            data = json.loads(msg) 
            
            supplier = data.get('supplier', '-').strip()
            comment_kw = data.get('comment_keyword', '-').strip()
            invoice_no = data.get('invoice number', '-').strip()
            date = data.get('date', '-').strip()
            amount = data.get('amount', '-').strip()
            gl_account = data.get('gl_account', '').strip()
            cost_center = data.get('cost_center', '').strip()
            internal_order = data.get('internal_order', '').strip()
            
            # 🎯 추출 결과 요약 메시지 복원
            display_msg = f"""### 📄 인보이스 정보 추출 완료!
* **업체명**: {supplier}
* **품목/서비스**: {comment_kw}
* **승인 번호**: {invoice_no}
* **발행 날짜**: {date}
* **금액**: {amount}
---
"""

            # 구글 시트 연동 처리
            if worksheet is not None:
                try:
                    all_rows = worksheet.get_all_values()
                    target_row_idx = None
                    matching_supplier_template = None
                    supplier_code = ""

                    for idx, row in enumerate(all_rows, start=1):
                        if idx == 1: continue
                        sheet_company_name = row[0].strip() if len(row) > 0 else ""
                        sheet_comment = row[5].strip().lower() if len(row) > 5 else ""
                        existing_inv_no = row[7].strip() if len(row) > 7 else ""
                        existing_amount = row[10].strip() if len(row) > 10 else ""

                        if supplier and sheet_company_name and (supplier in sheet_company_name or sheet_company_name in supplier):
                            matching_supplier_template = list(row)
                            if len(row) > 6 and row[6].strip(): supplier_code = row[6].strip()
                            if len(row) > 9 and row[9].strip(): gl_account = row[9].strip()
                            if len(row) > 11 and row[11].strip(): cost_center = row[11].strip()
                            if len(row) > 12 and row[12].strip(): internal_order = row[12].strip()

                            if comment_kw and sheet_comment and (comment_kw.lower() in sheet_comment or sheet_comment in comment_kw.lower()):
                                if not existing_inv_no and not existing_amount:
                                    target_row_idx = idx
                                    break

                    # 세션 저장
                    st.session_state["latest_invoice_data"] = {
                        "supplier": supplier,
                        "supplier_code": supplier_code,
                        "comment_kw": comment_kw,
                        "invoice_no": invoice_no,
                        "date": date,
                        "GL_Account": gl_account if gl_account else "61402100",
                        "amount": amount,
                        "cost_center": cost_center if cost_center else "OJ1060",
                        "internal_order": internal_order if internal_order else "131900000441",
                        "pdf_path": saved_pdf_path
                    }

                    # 구글 시트 기입 메시지 추가
                    if target_row_idx:
                        worksheet.update_cell(target_row_idx, 1, supplier)
                        if supplier_code: worksheet.update_cell(target_row_idx, 7, supplier_code)
                        worksheet.update_cell(target_row_idx, 8, invoice_no)
                        worksheet.update_cell(target_row_idx, 9, date)
                        worksheet.update_cell(target_row_idx, 11, amount)
                        display_msg += f"✅ **구글 시트 {target_row_idx}번째 행에 자동 기입되었습니다!**"
                    else:
                        new_row = [supplier, "A13", "Domestic", "Debit note", "IS", comment_kw, supplier_code, invoice_no, date, gl_account if gl_account else "61402100", amount, cost_center if cost_center else "OJ1060", internal_order if internal_order else "131900000441"]
                        worksheet.append_row(new_row)
                        display_msg += f"✅ **구글 시트에 [새로운 행]으로 추가되었습니다!**"

                except Exception as sheet_err:
                    display_msg += f"\n⚠️ **구글 시트 기입 실패**: `{sheet_err}`"

        except Exception as e:
            display_msg = f"❌ AI 응답 해석 오류: `{e}`"

        st.session_state.messages.append({"role": "assistant", "content": display_msg}) 
        st.chat_message("assistant").write(display_msg)

# --- 5. 구매 시스템 자동 입력 버튼 ---
if "latest_invoice_data" in st.session_state:
    st.markdown("---")
    st.subheader("🖥️ 사내 구매 시스템 자동 입력")
    st.info("아래 버튼을 누르면 브라우저가 열립니다. 7초 이내에 'BU code' 입력칸을 마우스로 클릭해주세요!")
    
    if st.button("🚀 구매 시스템에 자동 입력 및 PDF 첨부 시작"):
        inv = st.session_state["latest_invoice_data"]
        
        with st.spinner("매크로 실행 중... 마우스와 키보드에서 손을 떼어주세요."):
            success, result_msg = run_purchase_macro(
                supplier=inv["supplier_code"],
                comment_kw=inv["comment_kw"],
                invoice_no=inv["invoice_no"],
                date=inv["date"],
                GL_Account=inv["GL_Account"],
                amount=inv["amount"],
                cost_center=inv["cost_center"],
                internal_order=inv["internal_order"],
                pdf_file_path=inv.get("pdf_path")
            )
            
            if success:
                st.success(result_msg)
            else:
                st.error(result_msg)
