import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import gspread
from pypdf import PdfReader
import fitz  # PyMuPDF (이미지 PDF 파싱용)
import webbrowser
import pyautogui
import time
import pyperclip
import glob
import re
import base64
from io import BytesIO
from PIL import Image

load_dotenv()

# --- 1. 구글 시트 연결 ---
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
        
        # 크롬 브라우저 실행
        chrome_path = 'C:/Program Files/Google/Chrome/Application/chrome.exe %s'
        try:
            webbrowser.get(chrome_path).open(target_url)
        except Exception:
            try:
                chrome_path_x86 = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'
                webbrowser.get(chrome_path_x86).open(target_url)
            except Exception:
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

        # 6. Supplier Name (업체 코드 기입 후 드롭다운 선택)
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

        # 15. Upload invoice 버튼 클릭 및 파일 선택
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
                
        return True, "✅ 구매 시스템 자동 입력 및 PDF 파일 업로드가 완료되었습니다!"
    except Exception as e:
        return False, f"❌ 매크로 오류: {str(e)}"

# --- 3. UI 설정 ---
with st.sidebar:
    openai_api_key = os.getenv('OPENAI_API_KEY') 
    st.markdown("---")
    uploaded_file = st.file_uploader("인보이스(PDF)를 업로드하세요", type=["pdf"])

st.title("💬 인보이스 자동 추출 & 구매 시스템 등록 봇")

if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "PDF 업로드 후 '숫자 1' 입력 후 엔터!"}]

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

# --- 4. 메인 처리 로직 ---
if prompt := st.chat_input():
    if not openai_api_key:
        st.info("API 키를 추가해주세요.")
        st.stop()

    client = OpenAI(api_key=openai_api_key)
    st.session_state.messages.append({"role": "user", "content": prompt}) 
    st.chat_message("user").write(prompt) 
    
    if uploaded_file is not None:
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
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            base64_image = base64.b64encode(img_data).decode('utf-8')
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
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
            gl_account = data.get('gl_account', '').strip()
            cost_center = data.get('cost_center', '').strip()
            internal_order = data.get('internal_order', '').strip()

            # 🎯 [승인번호 정규식 완벽 정제]
            invoice_no = re.sub(r'(2026\d{4})A', r'\141', raw_invoice_no)
            invoice_no = re.sub(r'a[0oO]?wcc$', 'aowcc', invoice_no, flags=re.IGNORECASE)
            if 'aowcc' not in invoice_no.lower() and 'wcc' in invoice_no.lower():
                invoice_no = re.sub(r'a?0*wcc$', 'aowcc', invoice_no, flags=re.IGNORECASE)

            # 🎯 2. LG U+ 청구서 전용 고객번호 강제 추출 패치
            # 지로번호(6121857)나 사업자번호(2208139938)가 뽑혔더라도 문서 내 진짜 고객번호 탐색
            if "u+" in supplier.lower() or "lg" in supplier.lower() or "유플러스" in supplier:
                # PDF 텍스트 내에 LG U+ 마스터 고객번호 패턴이 있으면 무조건 고객번호로 교체
                if "511808413119" in pdf_text or "511808413119" in raw_invoice_no:
                    invoice_no = "511808413119"
                elif "399001198525" in pdf_text or "399001198525" in raw_invoice_no:
                    invoice_no = "399001198525"

            # 🎯 [날짜 포맷 정제]
            date_digits = re.sub(r'[^0-9]', '', raw_date)
            if len(date_digits) == 8:
                date = f"{date_digits[:4]}-{date_digits[4:6]}-{date_digits[6:]}"
            else:
                date = raw_date
            
            # 🎯 [구글 시트 처리 - 템플릿 정보만 참조 후 무조건 맨 아래 신규 행 추가]
            if worksheet is not None:
                try:
                    all_rows = worksheet.get_all_values()
                    
                    # 기본 공통값 설정
                    supplier_code = ""
                    gl_account = "61402100"
                    cost_center = "OJ1060"
                    internal_order = "131900000441"
                    final_comment_kw = comment_kw
                    
                    clean_supplier = re.sub(r'\(주\)|주식회사|\s+|유플러스', 'u+', supplier).lower()
                    extracted_words = re.findall(r'[A-Za-z0-9]+', comment_kw)

                    # 1단계: 업체명이 일치하는 템플릿 행들 필터링
                    matched_rows = []
                    for idx, row in enumerate(all_rows, start=1):
                        if idx == 1: continue # 헤더 스킵
                        sheet_company_name = row[0].strip() if len(row) > 0 else ""
                        clean_sheet_company = re.sub(r'\(주\)|주식회사|\s+|유플러스', 'u+', sheet_company_name).lower()

                        if clean_supplier and clean_sheet_company and (clean_supplier in clean_sheet_company or clean_sheet_company in clean_supplier):
                            matched_rows.append(row)

                    # 2단계: 필터링된 템플릿 중 가장 적절한 표준 템플릿 데이터 추출 (수정은 안 함!)
                    if matched_rows:
                        best_template = None

                        # ① H열(고객번호) 또는 K열(금액)이 일치하는 템플릿 찾기
                        for row in matched_rows:
                            existing_inv_no = row[7].strip() if len(row) > 7 else ""
                            existing_amount = row[10].strip() if len(row) > 10 else ""
                            clean_existing_amt = re.sub(r'[^0-9]', '', existing_amount)
                            clean_current_amt = re.sub(r'[^0-9]', '', amount)

                            if (existing_inv_no and invoice_no and existing_inv_no.strip() == invoice_no.strip()) or \
                               (clean_existing_amt and clean_current_amt and clean_existing_amt == clean_current_amt):
                                best_template = row
                                break

                        # ② 금액/번호 일치 항목 없으면 품목 키워드로 매칭
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
                                sheet_comment = row[5].strip() if len(row) > 5 else ""
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

                        # ③ 키워드 매칭도 실패하면 해당 업체의 첫 번째 템플릿 사용
                        if not best_template:
                            best_template = matched_rows[0]

                        # 매칭된 템플릿 데이터 추출
                        if best_template:
                            if len(best_template) > 5 and best_template[5].strip(): final_comment_kw = best_template[5].strip()
                            if len(best_template) > 6 and best_template[6].strip(): supplier_code = best_template[6].strip()
                            if len(best_template) > 9 and best_template[9].strip(): gl_account = best_template[9].strip()
                            if len(best_template) > 11 and best_template[11].strip(): cost_center = best_template[11].strip()
                            if len(best_template) > 12 and best_template[12].strip(): internal_order = best_template[12].strip()

                    # 3단계: 세션 데이터 저장 (구매 매크로 실행용)
                    st.session_state["latest_invoice_data"] = {
                        "supplier": supplier,
                        "supplier_code": supplier_code,
                        "comment_kw": final_comment_kw,
                        "invoice_no": invoice_no,
                        "date": date,
                        "GL_Account": gl_account,
                        "amount": amount,
                        "cost_center": cost_center,
                        "internal_order": internal_order,
                        "pdf_path": saved_pdf_path
                    }

                    display_msg = f"""### 📄 인보이스 정보 추출 완료!
* **업체명**: {supplier}
* **품목/서비스**: {final_comment_kw}
* **승인 번호**: {invoice_no}
* **발행 날짜**: {date}
* **금액**: {amount}
---
"""

                    # 4단계: 템플릿 건드리지 않고 무조건 구글 시트 맨 아래 [신규 행] 추가
                    new_row = [
                        supplier, "A13", "Domestic", "Debit note", "IS", 
                        final_comment_kw, 
                        supplier_code, invoice_no, date, 
                        gl_account, 
                        amount, 
                        cost_center, 
                        internal_order
                    ]
                    worksheet.append_row(new_row)
                    display_msg += f"✅ **[{supplier} - {final_comment_kw}] 마스터 템플릿 참조 후 [신규 행]으로 등록되었습니다!**"

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
    st.info("자판 영문인지 확인해주세요!")
    if st.button("🚀 구매 시스템에 자동 입력 및 PDF 첨부 시작"):
        inv = st.session_state["latest_invoice_data"]
        with st.spinner("매크로 실행 중..."):
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
            if success: st.success(result_msg)
            else: st.error(result_msg)
