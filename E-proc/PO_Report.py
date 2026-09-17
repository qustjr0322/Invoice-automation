import os
import glob
import time
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains
import pandas as pd

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def start_sso_macro():
    driver = None
    try:
        print("🧹 기존 크롬 프로세스 정리 및 설정 중...")
        os.system("taskkill /f /im chromedriver.exe /t >nul 2>&1")
        time.sleep(1.0)
        
        # SSO 세션 유지를 위한 크롬 프로필 경로 설정
        profile_path = r'C:\ChromeProfile_PO'
        lock_file = os.path.join(profile_path, 'SingletonLock')
        if os.path.exists(lock_file):
            try: 
                os.remove(lock_file)
            except: 
                pass

        options = uc.ChromeOptions()
        options.add_argument(f'--user-data-dir={profile_path}')
        options.add_argument('--profile-directory=Default')
        options.add_argument('--no-first-run')
        options.add_argument('--no-service-autorun')
        options.add_argument('--start-maximized') 
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--remote-debugging-port=0')

        # ========================================================
        # 다운로드 경로 설정 코드
        # ========================================================
        download_path = r"C:\Project\Status\CSV"
        
        # 폴더가 없으면 자동으로 생성
        if not os.path.exists(download_path):
            os.makedirs(download_path)

        # 크롬 다운로드 기본 경로를 강제로 변경
        prefs = {
            "download.default_directory": download_path,
            "download.prompt_for_download": False, # 다운로드 시 창 띄우지 않기
            "download.directory_upgrade": True
        }
        options.add_experimental_option("prefs", prefs)
        # ========================================================

        try:
            # version_main은 현재 설치된 크롬 버전에 맞게 수정하세요 (에러 발생 시 파라미터 삭제)
            driver = uc.Chrome(options=options, version_main=152, use_subprocess=True) 
        except Exception as uc_e:
            print(f"⚠️ 크롬을 제어할 수 없습니다. 열려있는 '크롬 창'을 닫고 시도해주세요! (오류: {uc_e})")
            return

        # 목적지 URL 설정
        target_url = "https://valeo.determine.com/t/ui/md/reports"
        driver.get(target_url)
        
        print("🚀 프로세스 시작 및 SSO 로그인 대기 중...")

        # ========================================================
        # 📌 [추가] Determine SSO / SAML 로그인 페이지 클릭 대응
        # ========================================================
        try:
            # SAML 로그인 버튼이 보일 때까지 최대 5초 대기 후 클릭 시도
            saml_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="saml_input0"]'))
            )
            print("🔍 SAML 로그인 페이지 감지됨. SSO 버튼 클릭 중...")
            saml_btn.click()
            print("✅ SAML 버튼 클릭 완료! 로그인 진행 중...")
            time.sleep(2)  # SSO 리다이렉트 대기
        except Exception:
            # 버튼이 없는 경우(이미 로그인 세션이 살아있는 경우) 에러 없이 그냥 통과
            pass
        # ========================================================

        # SSO 인증 대기 (최대 60초)
        wait = WebDriverWait(driver, 60)
        try:
            # URL에 목적지 도메인이 포함될 때까지 대기
            wait.until(EC.url_contains("valeo.determine.com"))
            print("✅ SSO 통과 및 목적지 URL 진입 성공")
        except:
            print("❌ SSO 로그인 대기 시간 초과! 직접 화면에서 로그인을 완료해주거나 세션을 확인하세요.")
            return
            
        print("🎉 인증 완료! 이제 Report 페이지 내 요소 제어를 시작할 수 있습니다.")
        time.sleep(2)

        # --- 🚨 여기에 Iframe 전환 코드 추가! ---
        try:
            print("🔍 화면 내의 Iframe을 탐색합니다...")
            # 화면에 있는 모든 iframe 태그 찾기
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            
            if len(iframes) > 0:
                print(f"✅ {len(iframes)}개의 Iframe 발견! 메인 Iframe으로 시선을 이동합니다.")
                # 보통 기업 포털은 첫 번째(0) 또는 특정 iframe 안에 메인 메뉴를 둡니다.
                # 우선 첫 번째 iframe으로 진입해 봅니다.
                driver.switch_to.frame(iframes[0]) 
            else:
                print("⚠️ Iframe이 없습니다. (만약 계속 에러가 나면 다른 원인입니다)")
        except Exception as e:
            print(f"Iframe 탐색 중 오류: {e}")
        
        # --- 1. 세모 클릭 (Purchasing 폴더 열기) ---
        try:
            print("⏳ 1. 세모 버튼(Purchasing) 클릭 대기 중...")
            step1_xpath = "//dt[@data-key='4']" 
            
            step1_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step1_xpath))
            )
            driver.execute_script("arguments[0].click();", step1_node)
            print("✅ 1. 세모 버튼 클릭 성공!")
            
            time.sleep(1.5) # 하위 메뉴가 펼쳐질 때까지 대기
            
        except Exception as e:
            print(f"❌ 1단계 실패: {e}")
            return


        # --- 2. 하위 메뉴 클릭 ---
        try:
            print("⏳ 2. 하위 메뉴 클릭 대기 중...")
            step2_xpath = '//*[@id="bpackLayout"]/table/tbody/tr/td[1]/div/div/dl/dd[4]/dl/dt[2]/div'
            
            step2_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step2_xpath))
            )
            driver.execute_script("arguments[0].click();", step2_node)
            print("✅ 2. 하위 메뉴 클릭 성공!")
            
            time.sleep(2) # 우측에 메인 데이터 테이블/필터가 로딩될 때까지 대기
            
        except Exception as e:
            print(f"❌ 2단계 실패: {e}")
            return


        # --- 3. ITEMID 필터 버튼 클릭 ---
        try:
            print("⏳ 3. ITEMID 필터 버튼 클릭 대기 중...")
            step3_xpath = '//*[@id="ITEMID_filter"]/table/tbody/tr/td[1]/button'
            
            step3_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step3_xpath))
            )
            driver.execute_script("arguments[0].click();", step3_node)
            print("✅ 3. 필터 버튼 클릭 성공!")
            
        except Exception as e:
            # ⬅️ 여기가 3단계 try를 닫아주는 except 입니다. (들여쓰기 8칸)
            print(f"❌ 3단계 실패: {e}")
            return

        # --- 4. VMK 선택
        try:
            print("⏳ 4. 첫 번째 버튼 클릭 대기 중...")
            step4_xpath = '/html/body/div[7]/div[2]/div[1]/div/div/div[8]/div/div/div/button[1]'
                
            step4_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step4_xpath))
            )
            driver.execute_script("arguments[0].click();", step4_node)
            print("✅ 4. 첫 번째 버튼 클릭 성공!")
                
            time.sleep(2) # 다음 팝업이나 요소가 뜰 때까지 대기
                
        except Exception as e:
            print(f"❌ 4단계 실패: {e}")
            return

        # --- 5. 테이블 내 특정 셀 클릭 (K47 항목) ---
        try:
            print("⏳ 5. 'K47-Valeo Mobility Korea' 항목 클릭 대기 중...")
                
            # 텍스트 'K47-Valeo Mobility Korea'를 포함하는 td 태그를 찾는 절대 실패하지 않는 경로
            step5_xpath = "//td[contains(text(), 'K47-Valeo Mobility Korea')]"
                
            step5_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step5_xpath))
            )
            driver.execute_script("arguments[0].click();", step5_node)
            print("✅ 5. 회사 항목(K47) 클릭 성공!")
                
            time.sleep(2) # 클릭 후 드롭다운이 닫히고 데이터가 로딩될 때까지 대기
                
        except Exception as e:
            print(f"❌ 5단계 실패: {e}")
            return

        #Search 버튼 클릭
        try:
            print("⏳ 9. 'Search' 버튼 클릭 대기 중...")
                
            # 버튼 태그 중 data-btname 속성이 'search'인 요소를 정확히 타겟팅
            step9_xpath = "//button[@data-btname='search']"
                
            step9_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step9_xpath))
            )
            driver.execute_script("arguments[0].click();", step9_node)
            print("✅ 9. 'Search' 버튼 클릭 성공!")
                
            time.sleep(3) # 검색 후 결과 데이터가 화면에 완전히 로딩될 때까지 넉넉히 대기
                
        except Exception as e:
            print(f"❌ 6단계 실패: {e}")
            return

        # --- 6. invcomp(송장/인보이스 관련) 요소 클릭 ---
        try:
            print("⏳ 6. 'invcomp' 요소 클릭 대기 중...")
            step6_xpath = '//*[@id="invcomp"]'
                
            step6_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step6_xpath))
            )
            driver.execute_script("arguments[0].click();", step6_node)
            print("✅ 6. 'invcomp' 요소 클릭 성공!")
                
            time.sleep(2) # 클릭 후 드롭다운이나 다음 화면이 뜰 때까지 대기
                
        except Exception as e:
            print(f"❌ 7단계 실패: {e}")
            return

        #검색 기간 설정
        try:
            print("⏳ 기간 필터 'Last 3 months' 선택 대기 중...")
                
            # 1. select 태그 요소 찾기
            year_xpath = '//*[@id="Year"]'
            year_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, year_xpath))
            )
                
            # 2. Select 모듈을 사용하여 화면에 보이는 텍스트로 바로 선택!
            year_select = Select(year_node)
            year_select.select_by_visible_text("Last 3 months")
                
            print("✅ 'Last 3 months' 선택 성공!")
            time.sleep(1) # 선택값이 화면에 갱신될 때까지 아주 짧게 대기
                
        except Exception as e:
            print(f"❌ 기간 필터 선택 실패: {e}")
            return

        try:
            print("⏳ 7. 필터 내 버튼 클릭 대기 중...")
            step7_xpath = '//*[@id="ITEMID_filter"]/table/tbody/tr/td[2]/div/div[9]/div/div/div/button[1]'
                
            step7_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step7_xpath))
            )
            driver.execute_script("arguments[0].click();", step7_node)
            print("✅ 7. 필터 내 버튼 클릭 성공!")
                
            time.sleep(5) # 팝업이나 드롭다운이 뜰 때까지 대기
                
        except Exception as e:
            print(f"❌ 8단계 실패: {e}")
            return

        try:
            print("⏳ 8. 'WA - IT' 항목 클릭 대기 중...")
                
            # 텍스트가 'WA - IT'인 칸을 정확하게 찾는 XPath
            step8_xpath = "//td[text()='WA - IT']"
                
            step8_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step8_xpath))
            )
            driver.execute_script("arguments[0].click();", step8_node)
            print("✅ 8. 'WA - IT' 항목 클릭 성공!")
                
            time.sleep(2) # 클릭 후 드롭다운이 닫히고 처리될 때까지 대기
                
        except Exception as e:
            print(f"❌ 9단계 실패: {e}")
            return

        # --- 10. Export 버튼 클릭 (정확한 대소문자 속성 매칭) ---
        try:
            print("⏳ 10. 'Export' 메뉴 버튼 클릭 대기 중...")
                
            # 캡처에서 확인한 정확한 속성명 'exportList' 사용
            step10_xpath = "//button[contains(@data-btname, 'export')]"
                
            step10_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step10_xpath))
            )
            driver.execute_script("arguments[0].click();", step10_node)
            print("✅ 10. 'Export' 메뉴 버튼 클릭 성공!")
                
            time.sleep(2) # 팝업 메뉴가 완전히 뜰 때까지 대기
                
        except Exception as e:
            print(f"❌ 10단계 실패: {e}")
            return


        # --- 11. 진짜 CSV 다운로드 버튼 클릭 및 파일명 자동 변경 ---
        try:
            print("⏳ 11. 'CSV' 옵션 클릭 및 다운로드 대기 중...")
                
            step11_xpath = "(//td[@data-btname='exportcsv'])[last()]"
                
            step11_node = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, step11_xpath))
            )
            time.sleep(1)
            driver.execute_script("arguments[0].click();", step11_node)
            print("✅ 11. CSV 다운로드 버튼 클릭 완료! (다운로드 시작)")
                
            # 파일이 완전히 다운로드될 때까지 넉넉히 대기
            time.sleep(15)                 
                
            download_path = r"C:\Project\Status\CSV"
                
            # 해당 폴더에 있는 모든 CSV 파일 목록 불러오기
            list_of_files = glob.glob(os.path.join(download_path, '*.csv'))
                
            if list_of_files:
                # 그 중 생성(수정) 시간이 가장 최근인 파일 찾기
                latest_file = max(list_of_files, key=os.path.getctime)
                    
                # 현재 날짜 및 시간 구하기 (예: 20260916_1511)
                now_str = datetime.now().strftime("%Y%m%d_%H%M")
                new_filename = f"PO_Report_{now_str}.csv"
                new_filepath = os.path.join(download_path, new_filename)
                    
                # 파일 이름 변경
                os.rename(latest_file, new_filepath)
                print(f"🎉 파일 다운로드 및 이름 변경 완료: {new_filename}")
            else:
                print("⚠️ 다운로드된 CSV 파일을 찾지 못해 이름을 변경할 수 없습니다.")
                
        except Exception as e:
            print(f"❌ 11단계(또는 파일명 변경) 실패: {e}")
            return

        # --- 12. CSV 파일 정제 및 고정 폭(칸조절) CSV 저장 ---
        try:
            print("⏳ 12. 다운로드된 CSV 파일 정제 및 칸조절 작업 시작...")
            download_path = r"C:\Project\Status\CSV"
            save_path = r"C:\Project\Status\Sorted_CSV"
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            
            list_of_files = glob.glob(os.path.join(download_path, '*.csv'))
            if not list_of_files:
                print("⚠️ 정제할 CSV 파일을 찾을 수 없습니다.")
                return
            latest_file = max(list_of_files, key=os.path.getctime)
            
            # CSV 데이터 읽기
            df = pd.read_csv(latest_file, engine='python', on_bad_lines='skip')
            
            # 1. Status - PO 중 'Received' 제외
            if 'Status - PO' in df.columns:
                df = df[df['Status - PO'] != 'Received']
            
            # 2. 지정된 컬럼 선택 및 이름 변경
            column_mapping = {
                'Login identifier - Created by': 'Originated by',
                'Requisition # - Requisition': 'PR',
                'PO - PO': 'PO',
                'Short description': 'Short description',
                'Unit price': 'Unit price',
                'Qty': 'Qty',
                'Department code - Cost Center': 'Cost Center',
                'Internal Order - Internal Order': 'Internal Order'
            }
            valid_keys = [k for k in column_mapping.keys() if k in df.columns]
            df_sorted = df[valid_keys].rename(columns=column_mapping)
            
            # 데이터 내 줄바꿈/탭 제거
            for col in df_sorted.columns:
                df_sorted[col] = df_sorted[col].astype(str).str.replace(r'[\r\n\t]+', ' ', regex=True).str.strip()
            
            # 🚨 [핵심 해결책] 각 열의 최대 글자 폭 계산 후 공백 채우기 (고정 폭 정렬)
            for col in df_sorted.columns:
                # 헤더 이름과 데이터 내용 중 가장 긴 글자 길이 산출
                max_len = max(df_sorted[col].astype(str).map(len).max(), len(col))
                # 각 열의 길이에 맞게 우측 공백 채우기 (ljust)
                df_sorted[col] = df_sorted[col].astype(str).apply(lambda x: x.ljust(max_len + 3))
            
            now_str = datetime.now().strftime("%Y%m%d_%H%M")
            sorted_filepath = os.path.join(save_path, f"Sorted_PO_Report_{now_str}.csv")
            
            # UTF-8-SIG 인코딩 CSV 파일로 저장
            df_sorted.to_csv(sorted_filepath, index=False, encoding='utf-8-sig')
            print(f"🎉 칸 정렬 완벽 적용 완료! 저장 경로: {sorted_filepath}")
            
        except Exception as e:
            print(f"❌ 12단계 데이터 정제 실패: {e}")
            return

        # --- 13. 웹 Gmail 이메일 발송 (JS 직접 주입으로 가림막 우회) ---
        try:
            print("⏳ 13. 웹 Gmail 작성 페이지 진입 및 이메일 자동 발송 시작...")
            
            abs_sorted_filepath = os.path.abspath(sorted_filepath)
            if not os.path.exists(abs_sorted_filepath):
                print("⚠️ 첨부할 정제 CSV 파일을 찾을 수 없습니다.")
                return

            # 1. 작성 창이 열린 상태로 Gmail 진입
            driver.get("https://mail.google.com/mail/u/0/#inbox?compose=new")
            time.sleep(5)

            # 2. 수신자 입력
            print("👤 수신자 입력 중...")
            actions = ActionChains(driver)
            recipients = "seokhoon.byun.ext@valeo.com, jeongil.sun@valeo.com"
            actions.send_keys(recipients)
            actions.send_keys(Keys.ENTER)
            actions.perform()
            time.sleep(1)

            # 🚨 수신자 자동완성 팝업 강제 닫기 (ESC 입력)
            actions = ActionChains(driver)
            actions.send_keys(Keys.ESCAPE)
            actions.perform()
            time.sleep(0.5)

            # 3. 제목(Subject) 입력 (JS 및 일반 클릭 이중 적용)
            print("📝 제목 입력 중...")
            subject_field = driver.find_element(By.NAME, "subjectbox")
            # 가림막 무시를 위해 JavaScript로 먼저 포커스 및 값 주입 후 입력
            driver.execute_script("arguments[0].focus(); arguments[0].value = arguments[1];", subject_field, f"[자동발송] PO 리포트 ({now_str})")
            time.sleep(1)

            # 4. 본문(Body) 입력
            print("📄 본문 내용 작성 중...")
            body_field = driver.find_element(By.XPATH, "//div[@role='textbox']")
            body_text = "안녕하세요,\n\nPO 리포트 파일(CSV)을 첨부하여 보내드립니다.\n\n감사합니다."
            driver.execute_script("arguments[0].innerText = arguments[1];", body_field, body_text)
            time.sleep(1)

            # 5. 정제 CSV 파일 첨부
            print("📎 정제 CSV 파일 첨부 중...")
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(abs_sorted_filepath)
            
            print("⏳ 파일 업로드 진행 중 (5초 대기)...")
            time.sleep(5)

            # 6. 파란색 'Send' (보내기) 버튼 클릭
            print("🚀 메일 '보내기(Send)' 버튼 클릭 중...")
            try:
                send_btn = driver.find_element(By.CSS_SELECTOR, "div.aoO")
                driver.execute_script("arguments[0].click();", send_btn)
            except Exception:
                send_btn = driver.find_element(By.XPATH, "//div[@role='button' and (text()='Send' or text()='보내기' or contains(@aria-label, 'Send') or contains(@aria-label, '보내기'))]")
                driver.execute_script("arguments[0].click();", send_btn)
            
            time.sleep(5)
            print("🎉 성공적으로 웹 Gmail을 통해 메일을 최종 발송했습니다!")

        except Exception as e:
            print(f"❌ 13단계 웹 이메일 발송 실패: {e}")
            return

        # ========================================================
        # 🚨 [고정] 브라우저 꺼짐 방지 (항상 모든 단계가 끝난 맨 마지막에 위치)
        # ========================================================
        print("🎉 준비된 모든 매크로 작업이 완료되었습니다!")
        input("매크로를 종료하고 창을 닫으려면 터미널 창에서 Enter 키를 누르세요...")

          
    except Exception as e:
        # ⬅️ 여기가 함수 맨 처음 시작했던 전체 try를 닫아주는 except 입니다. (들여쓰기 4칸)
        print(f"❌ 전체 매크로 실행 중 알 수 없는 오류 발생: {e}")
        
if __name__ == "__main__":
    start_sso_macro()
