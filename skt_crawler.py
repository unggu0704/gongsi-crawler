# =========================
# 필수 라이브러리 import
# =========================
import requests
import json
import time
import re
import random
from datetime import datetime
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# SSL 인증서 경고 무시 (verify=False 사용 시 발생)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SKTStableCrawler:
    """
    SKT T월드 공시지원금 정보를 안정적으로 수집하는 크롤러
    - requests.Session + Retry 전략
    - ThreadPoolExecutor 병렬 처리
    - 서버 탐지 방지를 위한 랜덤 딜레이 적용
    """

    def __init__(self):
        # =========================
        # 기본 설정 값
        # =========================
        self.base_url = "https://shop.tworld.co.kr"
        
        import os
        self.output_dir = "/app/output"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 요청 헤더 (브라우저 흉내)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': 'https://shop.tworld.co.kr/wireline/plan/list'
        }
        
        # 가입 유형 코드 → 한글 매핑
        self.scrb_type_map = {
            '31': '기기변경',
            '32': '번호이동',
            '33': '신규가입'
        }
        
        # =========================
        # requests 세션 + 재시도 전략
        # =========================
        self.session = requests.Session()
        
        # 네트워크 오류/서버 오류 발생 시 자동 재시도 설정
        retry_strategy = Retry(
            total=5,                  # 최대 재시도 횟수
            backoff_factor=1.5,       # 재시도 간 대기 시간 (지수 증가)
            status_forcelist=[429, 500, 502, 503, 504]  # 재시도 대상 HTTP 코드
        )
        
        # 커넥션 풀 + Retry 적용
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        self.session.mount("https://", adapter)

    # ==========================================================
    # 1단계: 요금제 카테고리 조회
    # ==========================================================
    def get_categories(self):
        """
        요금제 대분류 카테고리 조회
        """
        url = f"{self.base_url}/api/wireless/subscription/category"
        
        try:
            resp = self.session.get(
                url,
                params={'categoryId': '20010001'},
                headers=self.headers,
                verify=False,
                timeout=10
            )
            resp.raise_for_status()
            
            # 실제 데이터는 content 키에 있음
            return resp.json().get('content', [])
            
        except Exception as e:
            print(f"❌ 카테고리 로드 실패: {e}")
            return []

    # ==========================================================
    # 2단계: 카테고리별 요금제 목록 조회
    # ==========================================================
    def get_subscriptions(self, cat_id):
        """
        특정 카테고리 ID에 속한 요금제 목록 조회
        """
        url = f"{self.base_url}/api/wireless/subscription/list"
        
        params = {
            'type': 1,
            'upCategoryId': '300100400001',
            'categoryId': cat_id,
            '_': int(time.time() * 1000)  # 캐시 방지용 타임스탬프
        }
        
        try:
            resp = self.session.get(
                url,
                params=params,
                headers=self.headers,
                verify=False,
                timeout=10
            )
            return resp.json().get('content', [])
            
        except Exception:
            return []

    # ==========================================================
    # 3단계: 공시지원금 상세 조회 (병렬 워커)
    # ==========================================================
    def fetch_subsidy_worker(self, task):
        """
        단일 요금제 + 가입유형 + 약정기간 조합에 대해
        공시지원금 데이터를 수집하는 워커 함수
        """
        sub_id = task['id']
        sub_nm = task['nm']
        s_type = task['type']
        month = task['month']
        
        # 서버 부하 / 탐지 방지를 위한 랜덤 딜레이
        time.sleep(random.uniform(0.05, 0.15))
        
        url = f"{self.base_url}/notice"
        params = {
            'prodId': sub_id,
            'scrbType': s_type,
            'saleMonth': month
        }
        
        try:
            resp = self.session.get(
                url,
                params=params,
                headers=self.headers,
                verify=False,
                timeout=15
            )
            
            if resp.status_code != 200:
                return []

            # HTML 내 JS 코드에서 parseObject([...]) 부분 추출
            match = re.search(
                r'parseObject\(\s*(\[.*?\])\s*\);',
                resp.text,
                re.DOTALL
            )
            
            if not match:
                return []

            # JSON 문자열 → 파이썬 객체 변환
            raw_data = json.loads(match.group(1))
            extracted = []
            
            # 단말별 데이터 정리
            for item in raw_data:
                extracted.append({
                    '제조사': item.get('companyNm'),
                    '단말명': item.get('productNm'),
                    '용량': item.get('productMem'),
                    '요금제명': sub_nm,
                    '가입유형': self.scrb_type_map.get(s_type),
                    '약정기간': f"{month}개월",
                    '출고가': item.get('factoryPrice', 0),
                    '공시지원금': item.get('telecomSaleAmt', 0),
                    '추가지원금': item.get('selDsnetSupmAmt', 0),
                    '실구매가': item.get('price', 0),
                    '공시일': item.get('effStaDt')
                })
            
            return extracted
            
        except Exception:
            # 실패해도 전체 프로세스는 계속 진행
            return []

    # ==========================================================
    # 전체 실행 로직
    # ==========================================================
    def run(self, max_threads=5):
        """
        전체 크롤링 실행 함수
        """
        print("\n" + "🚀" * 40)
        print("SKT T월드 지원금 크롤러")
        print("🚀" * 40)
        
        print("\n🔍 1, 2단계: 요금제 목록 구성 중...")
        
        categories = self.get_categories()
        all_tasks = []
        
        # 모든 조합 생성
        for cat in categories:
            subs = self.get_subscriptions(cat['categoryId'])
            
            for s in subs:
                for t in ['31', '32', '33']:   # 가입 유형
                    for m in ['12', '24']:     # 약정 기간
                        all_tasks.append({
                            'id': s['subscriptionId'],
                            'nm': s['subscriptionNm'],
                            'type': t,
                            'month': m
                        })

        total_tasks = len(all_tasks)
        print(f"✅ 총 {total_tasks}개의 조회 조합 생성됨")
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
                
                if i % 100 == 0 or i == total_tasks:
                    print(f"📊 진행률: {i}/{total_tasks} ({i/total_tasks*100:.1f}%) 완료")

        # =========================
        # 4단계: 결과 저장
        # =========================
        if final_data:
            import os
            df = pd.DataFrame(final_data)
            fname = f"skt_subsidy_final_{datetime.now().strftime('%H%M%S')}.xlsx"
            output_path = os.path.join(self.output_dir, fname)
            df.to_excel(output_path, index=False)
            
            print(f"\n🎉 수집 성공!")
            print(f"📂 파일명: {fname}")
            print(f"📊 데이터: {len(final_data):,}건\n")

        else:
            print("\n❌ 수집된 데이터가 없습니다. 사이트 구조를 확인하세요.")


# ==========================================================
# 실행 진입점
# ==========================================================
if __name__ == "__main__":
    crawler = SKTStableCrawler()
    
    # 안정성을 위해 스레드 수 제한 (기본 5개)
    crawler.run(max_threads=5)