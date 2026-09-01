import os
import time
import pyautogui
import pyperclip
import ctypes

# 🎯 윈도우 DPI 스케일링 보정
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# 이미지 파일 경로 정의 (커스텀 경로 및 신규 파일 추가)
dots_img_path = r'C:\Project\Eproc_images\dots_menu.png'
box_img_path = r'C:\Project\Eproc_images\import_box.png'
import_blue_path = r'C:\Project\Eproc_images\import_blue.png'
back_home_path = r'C:\Project\Eproc_images\back_home.png'
my_cart_path = r'C:\Project\Eproc_images\my_cart.png'
summary_checkout_path = r'C:\Project\Eproc_images\summary_checkout.png'
proceed_req_path = r'C:\Project\Eproc_images\proceed_to_requisition.png'  # 신규 이미지

# 🎯 원본 규격 100% 유지 데이터 (공백/탭/줄바꿈 원형 보존)
raw_clipboard_data = """
Purchase item(Corcentric ID)	Part #	Short description *	Technology *	Supplier *	Supplier part #	Qty *	Unit	Type	Unit price	Currency	Tax code	Description	Manufacturer part #	Manufacturer	Needed date	Cost Center *	Start date	End date	Order Type *	VAT ID	Internal Order	WBS	Account *	GL account type *
		WEB EDI using fee for HR(비즈메카)	T342	85148		1	Each	Product	8440.00	KRW					2026-09-01	OJ1060			ZF		131900000441-KJ01		61410100	Overhead              
"""

print("🔍 3초 뒤 매크로 프로세스를 시작합니다...")
time.sleep(3)

try:
    # 🎯 1단계: '...' 버튼 탐색 및 클릭
    dots_loc = pyautogui.locateCenterOnScreen(dots_img_path, confidence=0.65, grayscale=True)
    if dots_loc:
        pyautogui.moveTo(dots_loc, duration=0.4)
        pyautogui.click()
        time.sleep(0.4)
        
        # 메뉴 이동 (Import 진입)
        pyautogui.press('down')
        time.sleep(0.2)
        pyautogui.click()
        print("🚀 Import 메뉴 진입 성공!")
        
        # 🎯 2단계: 페이지 전환 로딩 대기 (3초)
        time.sleep(3)
        
        # 🎯 3단계: 입력창(import_box.png) 클릭 & Ctrl+V 붙여넣기
        if os.path.exists(box_img_path):
            box_loc = pyautogui.locateCenterOnScreen(box_img_path, confidence=0.65, grayscale=True)
            if box_loc:
                pyautogui.moveTo(box_loc, duration=0.4)
                pyautogui.click()
                print("🖱️ Import 입력 박스 클릭 완료!")
                time.sleep(0.3)
                
                # 원본 데이터 복사 및 붙여넣기
                pyperclip.copy(raw_clipboard_data)
                time.sleep(0.2)
                pyautogui.hotkey('ctrl', 'v')
                time.sleep(0.5)
                print("📋 원본 데이터 붙여넣기 완료!")
                
                # 🎯 4단계: 파란색 'Import' 버튼 클릭
                if os.path.exists(import_blue_path):
                    blue_loc = pyautogui.locateCenterOnScreen(import_blue_path, confidence=0.65)
                    if blue_loc:
                        pyautogui.moveTo(blue_loc, duration=0.4)
                        pyautogui.click()
                        print("🎉 파란색 Import 버튼 클릭 완료!")
                        
                        # 🎯 5단계: 등록 완료 처리 (9초 대기) 후 back_home.png 클릭
                        time.sleep(9)
                        if os.path.exists(back_home_path):
                            home_loc = pyautogui.locateCenterOnScreen(back_home_path, confidence=0.65, grayscale=True)
                            if home_loc:
                                pyautogui.moveTo(home_loc, duration=0.4)
                                pyautogui.click()
                                print("🏠 back_home 버튼 클릭 완료!")
                                
                                # 🎯 6단계: 메인 페이지 로딩 (4초 대기) 후 my_cart.png 클릭
                                print("⏳ 메인 페이지 로딩 중 (4초 대기)...")
                                time.sleep(3)
                                
                                if os.path.exists(my_cart_path):
                                    cart_loc = pyautogui.locateCenterOnScreen(my_cart_path, confidence=0.65, grayscale=True)
                                    if cart_loc:
                                        pyautogui.moveTo(cart_loc, duration=0.4)
                                        pyautogui.click()
                                        print("🛒 My Cart 버튼 클릭 완료!")
                                        
                                        # 🎯 7단계: 장바구니 로딩 (3초 대기) 후 summary_checkout.png 클릭
                                        print("⏳ 장바구니 페이지 로딩 중 (2초 대기)...")
                                        time.sleep(3)
                                        
                                        if os.path.exists(summary_checkout_path):
                                            checkout_loc = pyautogui.locateCenterOnScreen(summary_checkout_path, confidence=0.65)
                                            if checkout_loc:
                                                pyautogui.moveTo(checkout_loc, duration=0.4)
                                                pyautogui.click()
                                                print("💳 Checkout 버튼 클릭 완료!")
                                                
                                                # 🎯 8단계: 요약 페이지 로딩 (3초 대기) 후 proceed_to_requisition.png 클릭
                                                print("⏳ 구매 신청 요약 페이지 로딩 중 (3초 대기)...")
                                                time.sleep(3)
                                                
                                                if os.path.exists(proceed_req_path):
                                                    proceed_loc = pyautogui.locateCenterOnScreen(proceed_req_path, confidence=0.65)
                                                    if proceed_loc:
                                                        pyautogui.moveTo(proceed_loc, duration=0.4)
                                                        pyautogui.click()
                                                        print("📑 Proceed to Requisition 버튼 클릭 완료! 전체 매크로 시나리오 성공!")
                                                    else:
                                                        print("❌ 'proceed_to_requisition.png' 이미지를 화면에서 찾지 못했습니다.")
                                                else:
                                                    print(f"❌ '{proceed_req_path}' 파일이 존재하지 않습니다.")

                                            else:
                                                print("❌ 'summary_checkout.png' 이미지를 화면에서 찾지 못했습니다.")
                                        else:
                                            print(f"❌ '{summary_checkout_path}' 파일이 존재하지 않습니다.")

                                    else:
                                        print("❌ 'my_cart.png' 이미지를 화면에서 찾지 못했습니다.")
                                else:
                                    print(f"❌ '{my_cart_path}' 파일이 존재하지 않습니다.")

                            else:
                                print("❌ 'back_home.png' 이미지를 찾지 못했습니다.")
                        else:
                            print(f"❌ '{back_home_path}' 파일이 없습니다.")

                    else:
                        print("❌ 파란색 'Import' 버튼을 찾지 못했습니다.")
                else:
                    print(f"❌ '{import_blue_path}' 파일이 없습니다.")

            else:
                print("❌ 'import_box.png' 이미지를 찾지 못했습니다.")
        else:
            print(f"❌ '{box_img_path}' 파일이 없습니다.")

except pyautogui.ImageNotFoundException:
    print("❌ 화면 요소를 찾지 못했습니다.")
except Exception as e:
    print(f"⚠️ 오류 발생: {e}")
