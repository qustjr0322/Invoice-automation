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
