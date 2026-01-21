# =========================
# 필수 라이브러리 import
# =========================
import requests
import json
import time
import random
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# SSL 인증서 경고 무시 (verify=False 사용 시 발생)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LGUplusCrawler:
    """
    LG U+ 공시지원금 정보를 안정적으로 수집하는 크롤러
    - Selenium으로 쿠키 획득 (Cloudflare 우회)
    - requests.Session + Retry 전략
    - ThreadPoolExecutor 병렬 처리
    - 봇 탐지 회피를 위한 랜덤 딜레이 및 User-Agent 다양화
    """

    def __init__(self):
        # =========================
        # 기본 설정 값
        # =========================
        self.base_url = "https://www.lguplus.com"

        # 출력 디렉토리 설정 (Docker 볼륨)
        import os
        self.output_dir = "/app/output"
        os.makedirs(self.output_dir, exist_ok=True)

        # 봇 탐지 회피용 User-Agent 목록
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        
        # 가입 유형 코드 → 한글 매핑
        self.signup_type_map = {
            '1': '기기변경',
            '2': '번호이동',
            '3': '신규가입'
        }
        
        # 쿠키 저장소
        self.cookies = None

    # ==========================================================
    # 1단계: Selenium으로 쿠키 획득
    # ==========================================================
    def get_cookies_from_selenium(self):
        """
        Selenium으로 페이지 접속 후 쿠키 획득 (Cloudflare 우회)
        """
        print("\n🔐 쿠키 획득 중 (Selenium)...")
        
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f'user-agent={random.choice(self.user_agents)}')
        
        # Docker 환경 감지
        import os
        is_docker = os.getenv('RUNNING_IN_DOCKER') == 'true'
        
        if is_docker:
            options.add_argument('--headless=new')
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-extensions')
            options.add_argument('--proxy-server="direct://"')
            options.add_argument('--proxy-bypass-list=*')
            options.add_argument('--start-maximized')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.binary_location = '/usr/bin/chromium'
        else:
            print("[Local] 환경에서 실행 중")
        
        try:
            if is_docker:
                from selenium.webdriver.chrome.service import Service
                service = Service('/usr/bin/chromedriver')
                driver = webdriver.Chrome(service=service, options=options)
            else:
                try:
                    from selenium.webdriver.chrome.service import Service
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                except:
                    driver = webdriver.Chrome(options=options)
            
            # LG U+ 페이지 접속
            url = f'{self.base_url}/mobile/financing-model'
            print(f"🌐 페이지 접속 중: {url}")
            driver.get(url)
            
            # 초기 대기
            time.sleep(5)
            
            # 페이지 타이틀 확인
            print(f"📄 페이지 타이틀: {driver.title}")
            
            # Cloudflare 체크 대기
            print("⏳ Cloudflare 우회 대기 중... (30초)")
            time.sleep(30)
            
            # 쿠키 추출 전 재확인
            print(f"📄 최종 페이지 타이틀: {driver.title}")
            
            # 쿠키 추출 및 필터링
            cookies = driver.get_cookies()
            print(f"🍪 전체 쿠키 개수: {len(cookies)}")
            
            cookie_dict = {}
            for cookie in cookies:
                try:
                    cookie['value'].encode('latin-1')
                    cookie_dict[cookie['name']] = cookie['value']
                except UnicodeEncodeError:
                    print(f"⚠️  쿠키 건너뜀 (인코딩 오류): {cookie['name']}")
            
            driver.quit()
            
            if cookie_dict:
                print(f"✅ 쿠키 획득 완료: {len(cookie_dict)}개")
                return cookie_dict
            else:
                print("⚠️  쿠키가 없습니다. Cloudflare가 차단했을 수 있습니다.")
                return None
            
        except Exception as e:
            print(f"❌ 쿠키 획득 실패: {e}")
            import traceback
            traceback.print_exc()
            return None


    # ==========================================================
    # 2단계: 요금제 코드 리스트 조회
    # ==========================================================
    def get_plan_codes(self):
        """
        요금제 카테고리별 코드 리스트 조회 (5G, LTE)
        """
        print("\n📋 요금제 코드 수집 중...")
        
        # Retry 전략 설정
        retry_strategy = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        session.mount("https://", adapter)
        
        session.cookies.update(self.cookies)
        session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'application/json, text/plain, */*',
            'Referer': f'{self.base_url}/mobile/financing-model'
        })
        
        api_url = f'{self.base_url}/uhdc/fo/prdv/mdlbsufu/v1/mdlb-pp-list'
        all_plans = []
        
        # 요금제 카테고리별 조회
        categories = [
            ('00', '5G'),
            ('01', 'LTE')
        ]
        
        for cat_code, cat_name in categories:
            try:
                params = {
                    'hphnPpGrpKwrdCd': cat_code,
                    '_': int(time.time() * 1000)  # 캐시 방지
                }
                response = session.get(api_url, params=params, verify=False, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    count = 0
                    
                    for group in data.get('dvicMdlbSufuPpList', []):
                        for plan in group.get('dvicMdlbSufuPpDetlList', []):
                            all_plans.append({
                                'code': plan['urcMblPpCd'],
                                'name': plan['urcMblPpNm'],
                                'type': cat_name
                            })
                            count += 1
                    
                    print(f"  ✅ {cat_name}: {count}개")
                else:
                    print(f"  ❌ {cat_name} 실패: {response.status_code}")
                
                # 카테고리 간 딜레이
                time.sleep(random.uniform(0.1, 0.3))
                
            except Exception as e:
                print(f"  ❌ {cat_name} 에러: {e}")
        
        session.close()
        print(f"✅ 총 {len(all_plans)}개 요금제 수집 완료\n")
        
        return all_plans

    # ==========================================================
    # 3단계: 공시지원금 상세 조회 (병렬 워커)
    # ==========================================================
    def fetch_subsidy_worker(self, task):
        """
        단일 요금제 + 가입유형 조합에 대해
        공시지원금 데이터를 수집하는 워커 함수
        """
        plan = task['plan']
        signup_code = task['signup_code']
        signup_name = task['signup_name']
        
        # 봇 탐지 회피: 랜덤 딜레이
        time.sleep(random.uniform(0.05, 0.2))
        
        # Retry 전략 설정
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=5, pool_maxsize=10)
        session.mount("https://", adapter)
        
        session.cookies.update(self.cookies)
        session.headers.update({
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'application/json, text/plain, */*',
            'Referer': f'{self.base_url}/mobile/financing-model'
        })
        
        api_url = f'{self.base_url}/uhdc/fo/prdv/mdlbsufu/v2/mdlb-sufu-list'
        result_data = []
        
        try:
            params = {
                'onlnOrdrPsblEposDivsCd': 'Y',
                'urcHphnEntrPsblKdCd': signup_code,
                'urcMblPpCd': plan['code'],
                'shwd': '',
                'sortOrd': '01',
                'urcWlcmAplyDivsCd': 'NONE',
                'pageNo': '1',
                'rowSize': '10',
                '_': int(time.time() * 1000)
            }
            
            response = session.get(api_url, params=params, verify=False, timeout=15)
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            models = data.get('dvicMdlbSufuDtoList', [])
            total_count = data.get('totalCnt', 0)
            
            all_models = models.copy()
            
            # 페이징 처리
            if total_count > 10:
                import math
                total_pages = math.ceil(total_count / 10)
                
                for page in range(2, total_pages + 1):
                    time.sleep(random.uniform(0.05, 0.15))
                    
                    params['pageNo'] = str(page)
                    params['_'] = int(time.time() * 1000)
                    
                    resp = session.get(api_url, params=params, verify=False, timeout=15)
                    if resp.status_code == 200:
                        all_models.extend(resp.json().get('dvicMdlbSufuDtoList', []))
            
            # 데이터 저장
            for model in all_models:
                # 6개월 약정
                result_data.append({
                    '요금제명': plan['name'],
                    '요금제유형': plan['type'],
                    '가입유형': signup_name,
                    '약정': '6개월',
                    '모델명': model.get('urcTrmMdlNm'),
                    '출고가': model.get('dlvrPrc'),
                    '이통사지원금': model.get('sixPlanPuanSuptAmt'),
                    '추가지원금': model.get('sixPlanAddSuptAmt'),
                    '유통망지원금': model.get('dsnwSupportAmt'),
                    '지원금총액': model.get('sixPlanSuptTamt')
                })
                
                # 기본 약정
                result_data.append({
                    '요금제명': plan['name'],
                    '요금제유형': plan['type'],
                    '가입유형': signup_name,
                    '약정': '기본',
                    '모델명': model.get('urcTrmMdlNm'),
                    '출고가': model.get('dlvrPrc'),
                    '이통사지원금': model.get('basicPlanPuanSuptAmt'),
                    '추가지원금': model.get('basicPlanAddSuptAmt'),
                    '유통망지원금': model.get('dsnwSupportAmt'),
                    '지원금총액': model.get('basicPlanSuptTamt')
                })
            
            return result_data
            
        except Exception:
            return []
        finally:
            session.close()

    # ==========================================================
    # 4단계: Excel 저장
    # ==========================================================
    def save_to_excel(self, data):
        """
        수집된 데이터를 Excel 파일로 저장
        """
        import os
        print("\n💾 Excel 파일 저장 중...")

        # pandas DataFrame으로 변환 및 저장
        df = pd.DataFrame(data)
        filename = f'lguplus_subsidy_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        # 출력 파일 경로를 /app/output 디렉토리로 설정
        output_path = os.path.join(self.output_dir, filename)
        df.to_excel(output_path, index=False)

        print(f"✅ 파일 저장 완료: {filename}")
        print(f"📂 저장 위치: {output_path}")
        return filename

    # ==========================================================
    # 전체 실행 로직
    # ==========================================================
    def run(self, max_threads=5):
        """
        전체 크롤링 실행 함수
        """
        start_time = time.time()
        
        print("\n" + "🚀" * 40)
        print("LG U+ 지원금 크롤러")
        print("🚀" * 40)
        
        # 1단계: 쿠키 획득
        self.cookies = self.get_cookies_from_selenium()
        if not self.cookies:
            print("\n❌ 쿠키 획득 실패")
            return
        
        # 2단계: 요금제 코드 수집
        plan_codes = self.get_plan_codes()
        if not plan_codes:
            print("\n❌ 요금제 코드 수집 실패")
            return
        
        # 작업 목록 생성
        all_tasks = []
        for plan in plan_codes:
            for signup_code, signup_name in self.signup_type_map.items():
                all_tasks.append({
                    'plan': plan,
                    'signup_code': signup_code,
                    'signup_name': signup_name
                })
        
        total_tasks = len(all_tasks)
        print(f"🔄 총 {total_tasks}개 작업 생성 완료")
        print(f"⚙️  병렬 처리: {max_threads}개 스레드\n")
        
        final_data = []
        
        # =========================
        # 3단계: 병렬 처리로 데이터 수집
        # =========================
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {
                executor.submit(self.fetch_subsidy_worker, task): task
                for task in all_tasks
            }
            
            for i, future in enumerate(as_completed(futures), 1):
                res = future.result()
                
                if res:
                    final_data.extend(res)
                
                if i % 50 == 0 or i == total_tasks:
                    print(f"📊 진행률: {i}/{total_tasks} ({i/total_tasks*100:.1f}%) | 수집 데이터: {len(final_data):,}건")
        
        # =========================
        # 4단계: 결과 저장
        # =========================
        if final_data:
            filename = self.save_to_excel(final_data)
            
            elapsed_time = time.time() - start_time
            minutes = int(elapsed_time // 60)
            seconds = int(elapsed_time % 60)
            
            print(f"\n🎉 수집 성공!")
            print(f"📂 파일명: {filename}")
            print(f"📊 데이터: {len(final_data):,}건")
            print(f"⏱️  실행 시간: {minutes}분 {seconds}초\n")
        else:
            print("\n❌ 수집된 데이터가 없습니다.")


# ==========================================================
# 실행 진입점
# ==========================================================
if __name__ == "__main__":
    crawler = LGUplusCrawler()
    
    # 안정성을 위해 스레드 수 제한 (기본 5개)
    crawler.run(max_threads=5)
