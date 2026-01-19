"""
SKT 공시지원금 크롤러 (1~3단계 통합)
- 데이터 정제 및 가독성 개선
- JSON + Excel 출력
"""
import requests
import json
import time
import re
from datetime import datetime
import pandas as pd

class SKTCrawler:
    def __init__(self):
        self.base_url = "https://shop.tworld.co.kr"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # 가입유형 매핑
        self.scrb_type_map = {
            '31': '기기변경',
            '32': '번호이동',
            '33': '신규가입'
        }
    
    def get_categories(self):
        """1단계: 카테고리 수집"""
        url = f"{self.base_url}/api/wireless/subscription/category"
        params = {'categoryId': '20010001'}
        
        print("=" * 70)
        print("1단계: 카테고리 수집")
        print("=" * 70)
        
        try:
            response = requests.get(url, params=params, headers=self.headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                categories = data.get('content', [])
                
                print(f"✅ {len(categories)}개 카테고리 수집 완료\n")
                
                for idx, cat in enumerate(categories, 1):
                    print(f"  {idx:2d}. {cat['categoryNm']:25s} (ID: {cat['categoryId']})")
                
                return categories
            else:
                print(f"❌ API 오류: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ 예외 발생: {e}")
            return []
    
    def get_subscriptions_by_category(self, category):
        """2단계: 특정 카테고리의 요금제 수집"""
        url = f"{self.base_url}/api/wireless/subscription/list"
        
        params = {
            'type': 1,
            'upCategoryId': '300100400001',
            'categoryId': category['categoryId'],
            '_': int(time.time() * 1000)
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                subscriptions = data.get('content', [])
                
                # 카테고리 정보 추가
                for sub in subscriptions:
                    sub['_category_id'] = category['categoryId']
                    sub['_category_name'] = category['categoryNm']
                
                return subscriptions
            else:
                print(f"  ❌ API 오류: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"  ❌ 예외 발생: {e}")
            return []
    
    def clean_subsidy_data(self, raw_data, subscription_id, scrb_type, sale_month):
        """공시지원금 데이터 정제
        
        필요한 필드만 추출하고 가독성 개선
        """
        cleaned = []
        
        for item in raw_data:
            clean_item = {
                # 단말 정보
                '제조사': item.get('companyNm', ''),
                '단말명': item.get('productNm', ''),
                '용량': item.get('productMem', ''),
                
                # 요금제 정보
                '요금제ID': item.get('prodId', subscription_id),
                '요금제명': item.get('prodNm', ''),
                
                # 가입 조건
                '가입유형': self.scrb_type_map.get(scrb_type, scrb_type),
                '약정기간': f"{sale_month}개월",
                
                # 가격 정보
                '출고가': item.get('factoryPrice', 0),
                '공시지원금_공통': item.get('telecomSaleAmt', 0),
                '공시지원금_추가': item.get('selDsnetSupmAmt', 0),
                '공시지원금_총액': item.get('twdSumSaleAmt', 0),
                '판매가': item.get('price', 0),
                
                # 추가 정보
                '유통망지원금': item.get('dsnetSupmAmt', 0),
                '공시일': item.get('effStaDt', ''),

                # T다이렉트샵 가격
                'T다이렉트샵_지원금총액': item.get('twdSumSaleAmt', 0),
                'T다이렉트샵_판매가': item.get('twdPrice', 0),
                
                # 원본 코드 (참고용)
                '_원본_가입유형코드': scrb_type,
                '_원본_단말코드': item.get('modelCd', ''),
            }
            
            cleaned.append(clean_item)
        
        return cleaned
    
    def get_subsidy_for_subscription(self, subscription_id, scrb_type='31', sale_month='24'):
        """3단계: 특정 요금제의 공시지원금 수집"""
        url = f"{self.base_url}/notice"
        
        params = {
            'prodId': subscription_id,
            'scrbType': scrb_type,
            'saleMonth': sale_month
        }
        
        try:
            response = requests.get(url, params=params, headers=self.headers, verify=False)
            
            if response.status_code == 200:
                html = response.text
                
                # parseObject([...]) 부분 추출
                pattern = r'parseObject\((.*?)\);'
                match = re.search(pattern, html, re.DOTALL)
                
                if match:
                    json_str = match.group(1)
                    raw_data = json.loads(json_str)
                    
                    # 데이터 정제
                    cleaned_data = self.clean_subsidy_data(
                        raw_data, subscription_id, scrb_type, sale_month
                    )
                    
                    return cleaned_data
                else:
                    print(f"    ⚠️ parseObject를 찾을 수 없음")
                    return []
            else:
                print(f"    ❌ HTTP 오류: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"    ❌ 예외 발생: {e}")
            return []
    
    def save_to_excel(self, data, filename):
        """엑셀 파일로 저장"""
        if not data:
            print("⚠️ 저장할 데이터가 없습니다.")
            return
        
        df = pd.DataFrame(data)
        
        # 엑셀 저장
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='공시지원금')
            
            # 열 너비 자동 조정
            worksheet = writer.sheets['공시지원금']
            for idx, col in enumerate(df.columns):
                max_length = max(
                    df[col].astype(str).apply(len).max(),
                    len(col)
                ) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)
        
        print(f"✅ 엑셀 저장: {filename}")
    
    def crawl_all(self, test_mode=True):
        """전체 크롤링 실행"""
        print("\n")
        print("╔" + "═" * 68 + "╗")
        print("║" + " " * 18 + "SKT 공시지원금 크롤러 시작" + " " * 23 + "║")
        print("╚" + "═" * 68 + "╝")
        print()
        
        # 1단계: 카테고리 수집
        categories = self.get_categories()
        
        if not categories:
            print("\n❌ 카테고리 수집 실패")
            return
        
        # 테스트 모드: 첫 카테고리만
        if test_mode:
            categories = categories[:32]
            print(f"\n⚠️ 테스트 모드: 첫 {len(categories)}개 카테고리만 처리")
        
        # 2단계: 각 카테고리별 요금제 수집
        print("\n" + "=" * 70)
        print("2단계: 요금제 수집")
        print("=" * 70)
        
        all_subscriptions = []
        
        for idx, category in enumerate(categories, 1):
            print(f"\n[{idx}/{len(categories)}] {category['categoryNm']} 처리 중...")
            
            subscriptions = self.get_subscriptions_by_category(category)
            all_subscriptions.extend(subscriptions)
            
            print(f"  ✅ {len(subscriptions)}개 요금제 수집")
            
            time.sleep(0.3)
        
        # 테스트 모드: 첫 요금제만
        if test_mode and all_subscriptions:
            all_subscriptions = all_subscriptions[:32]
            print(f"\n⚠️ 테스트 모드: 첫 {len(all_subscriptions)}개 요금제만 처리")
        
        # 3단계: 각 요금제별 공시지원금 수집
        print("\n" + "=" * 70)
        print("3단계: 공시지원금 수집")
        print("=" * 70)
        
        all_subsidies = []
        
        # 가입유형 및 약정기간 조합
        scrb_types = ['31', '32', '33']  # 기변, 번이, 신규
        sale_months = ['12', '24']
        
        for idx, subscription in enumerate(all_subscriptions, 1):
            subscription_id = subscription['subscriptionId']
            subscription_name = subscription['subscriptionNm']
            
            print(f"\n[{idx}/{len(all_subscriptions)}] {subscription_name} (ID: {subscription_id})")
            
            for scrb_type in scrb_types:
                scrb_name = self.scrb_type_map[scrb_type]
                
                for sale_month in sale_months:
                    print(f"  - {scrb_name}/{sale_month}개월 조회 중...", end=' ')
                    
                    subsidies = self.get_subsidy_for_subscription(
                        subscription_id, scrb_type, sale_month
                    )
                    
                    if subsidies:
                        all_subsidies.extend(subsidies)
                        print(f"✅ {len(subsidies)}개 단말")
                    else:
                        print("⚠️ 없음")
                    
                    time.sleep(0.3)
        
        # 결과 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 저장
        json_file = f'skt_subsidies_{timestamp}.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'crawled_at': datetime.now().isoformat(),
                'total_records': len(all_subsidies),
                'data': all_subsidies
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ JSON 저장: {json_file}")
        
        # 엑셀 저장
        excel_file = f'skt_subsidies_{timestamp}.xlsx'
        self.save_to_excel(all_subsidies, excel_file)
        
        # 최종 요약
        print("\n" + "=" * 70)
        print("✅ 크롤링 완료!")
        print("=" * 70)
        print(f"\n📊 수집 요약:")
        print(f"  - 카테고리: {len(categories)}개")
        print(f"  - 요금제: {len(all_subscriptions)}개")
        print(f"  - 공시지원금 레코드: {len(all_subsidies):,}개")
        print(f"\n📁 저장 파일:")
        print(f"  - JSON: {json_file}")
        print(f"  - Excel: {excel_file}")
        
        # 샘플 데이터 출력
        if all_subsidies:
            print(f"\n📋 샘플 데이터 (첫 번째 레코드):")
            sample = all_subsidies[0]
            print(f"  - 단말: {sample.get('단말명', 'N/A')} ({sample.get('용량', 'N/A')})")
            print(f"  - 요금제: {sample.get('요금제명', 'N/A')}")
            print(f"  - 가입유형: {sample.get('가입유형', 'N/A')}")
            print(f"  - 약정: {sample.get('약정기간', 'N/A')}")
            print(f"  - 공시지원금: {sample.get('공시지원금_총액', 0):,}원")
        
        return all_subsidies


if __name__ == "__main__":
    # SSL 경고 무시
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    crawler = SKTCrawler()
    
    # 테스트 모드로 실행 (첫 카테고리, 첫 요금제만)
    result = crawler.crawl_all(test_mode=False)
    
    print("\n" + "=" * 70)
    print("💡 테스트 완료!")
    print("   전체 수집: test_mode=False로 변경 후 실행")
    print("=" * 70)