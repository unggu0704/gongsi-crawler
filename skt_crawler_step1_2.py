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

# SSL 경고 무시
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class SKTStableCrawler:
    def __init__(self):
        self.base_url = "https://shop.tworld.co.kr"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': 'https://shop.tworld.co.kr/wireline/plan/list'
        }
        self.scrb_type_map = {'31': '기기변경', '32': '번호이동', '33': '신규가입'}
        
        # 세션 및 재시도 전략 (안정성 극대화)
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,  # 재시도 횟수 상향
            backoff_factor=1.5, # 지수 백오프 적용
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
        self.session.mount("https://", adapter)

    def get_categories(self):
        url = f"{self.base_url}/api/wireless/subscription/category"
        try:
            resp = self.session.get(url, params={'categoryId': '20010001'}, headers=self.headers, verify=False, timeout=10)
            resp.raise_for_status()
            return resp.json().get('content', [])
        except Exception as e:
            print(f"❌ 카테고리 로드 실패: {e}")
            return []

    def get_subscriptions(self, cat_id):
        url = f"{self.base_url}/api/wireless/subscription/list"
        params = {'type': 1, 'upCategoryId': '300100400001', 'categoryId': cat_id, '_': int(time.time() * 1000)}
        try:
            resp = self.session.get(url, params=params, headers=self.headers, verify=False, timeout=10)
            return resp.json().get('content', [])
        except Exception as e:
            return []

    def fetch_subsidy_worker(self, task):
        """단일 요청 처리 및 정교한 예외 처리"""
        sub_id = task['id']
        sub_nm = task['nm']
        s_type = task['type']
        month = task['month']
        
        # 서버 탐지 방지를 위한 미세 랜덤 지연
        time.sleep(random.uniform(0.05, 0.15))
        
        url = f"{self.base_url}/notice"
        params = {'prodId': sub_id, 'scrbType': s_type, 'saleMonth': month}
        
        try:
            resp = self.session.get(url, params=params, headers=self.headers, verify=False, timeout=15)
            if resp.status_code != 200:
                return []

            # 정규식 패턴 안정화 (멀티라인 대응)
            match = re.search(r'parseObject\(\s*(\[.*?\])\s*\);', resp.text, re.DOTALL)
            if not match:
                return []

            raw_data = json.loads(match.group(1))
            extracted = []
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
            return []

    def run(self, max_threads=5):
        print("🔍 1, 2단계: 요금제 목록 구성 중...")
        categories = self.get_categories()
        all_tasks = []
        
        for cat in categories:
            subs = self.get_subscriptions(cat['categoryId'])
            for s in subs:
                for t in ['31', '32', '33']:
                    for m in ['12', '24']:
                        all_tasks.append({'id': s['subscriptionId'], 'nm': s['subscriptionNm'], 'type': t, 'month': m})

        total_tasks = len(all_tasks)
        print(f"✅ 총 {total_tasks}개의 조회 조합 생성됨. 병렬 수집 시작 (Thread: {max_threads})")

        final_data = []
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {executor.submit(self.fetch_subsidy_worker, task): task for task in all_tasks}
            
            for i, future in enumerate(as_completed(futures), 1):
                res = future.result()
                if res:
                    final_data.extend(res)
                
                if i % 100 == 0 or i == total_tasks:
                    print(f"📊 진행률: {i}/{total_tasks} ({i/total_tasks*100:.1f}%) 완료")

        if final_data:
            df = pd.DataFrame(final_data)
            fname = f"skt_subsidy_final_{datetime.now().strftime('%H%M%S')}.xlsx"
            df.to_excel(fname, index=False)
            print(f"\n🎉 수집 성공! 파일명: {fname} (데이터: {len(final_data)}건)")
        else:
            print("\n❌ 수집된 데이터가 없습니다. 사이트 구조를 확인하세요.")

if __name__ == "__main__":
    crawler = SKTStableCrawler()
    # 안정성을 위해 5개 스레드 권장
    crawler.run(max_threads=5)