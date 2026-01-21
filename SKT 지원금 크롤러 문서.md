# SKT 공시지원금 크롤러 문서

**버전:** v1.0  
**최종 수정:** 2026-01-19

---

## 📋 개요

**목적:** SKT 요금제별 공시지원금 자동 수집  
**출력:** 엑셀 파일

- 공시지원금 (~85,000건)

### T 다이렉트 샵 분석
-  jQuery 기반, HTML 내 JavaScript 객체로 데이터 임베딩, 페이지 리로드로 데이터 갱신

---

## 🔄 실행 흐름

```
1단계: 카테고리 14개 수집
   ↓
2단계: 요금제 94개 수집
   ↓
3단계: 공시지원금 수집 (병렬 처리, 94×3×2xN)
   ↓
엑셀 저장
```

---

## 📡 API 3개

### 1️⃣ 카테고리 조회

```bash
GET https://shop.tworld.co.kr/api/wireless/subscription/category?categoryId=20010001
```

**응답:**

```json
{
  "content": [
    {"categoryId": "3001004000010001", "categoryNm": "5G 만34세이하"},
    ...
  ]
}
```

---

### 2️⃣ 요금제 목록 조회

```bash
GET https://shop.tworld.co.kr/api/wireless/subscription/list?type=1&upCategoryId=300100400001&categoryId=3001004000010001&_=1737123456789
```

**응답:**

```json
{
  "content": [
    {
      "subscriptionId": "NA00009121",
      "subscriptionNm": "5GX 프리미엄",
      "basicCharge": "109000",
      "dataInfo": "무제한",
      ...
    }
  ]
}
```

---

### 3️⃣ 공시지원금 조회

```bash
GET https://shop.tworld.co.kr/notice?prodId=NA00009121&scrbType=31&saleMonth=24
```

**파라미터:**

- `scrbType`: 31(기변), 32(번이), 33(신규)
- `saleMonth`: 12 or 24 (약정정)

**응답:** HTML 내 JavaScript

```html
<script>
_this.products = parseObject([
  {
    "companyNm": "삼성전자(주)",
    "productNm": "갤럭시 S24 울트라 5G",
    "productMem": "256G",
    "factoryPrice": 1544400,
    "telecomSaleAmt": 630000,
    "selDsnetSupmAmt": 94500,
    ...
  }
]);
</script>
```

---

## ⚙️ 수정 가능한 설정

### 1. 병렬 스레드 수

**위치:** 파일 최하단

```python
crawler.run(max_threads=5, test_mode=True)
            ↑ 변경 (권장: 3~5)
```

### 2. 랜덤 딜레이

**위치:** `fetch_subsidy_worker()` 함수

```python
time.sleep(random.uniform(0.05, 0.15))
                          ↑     ↑
                        최소   최대 (권장: 0.05~0.15)
```

### 3. 재시도 횟수

**위치:** `__init__()` 함수

```python
retry_strategy = Retry(
    total=5,           # 재시도 횟수 (권장: 5)
    backoff_factor=1.5 # 재시도 간격 (권장: 1.5)
)
```

### 4. 타임아웃

**위치:** `fetch_subsidy_worker()` 함수

```python
timeout=15  # 15초 (권장: 10~20)
```

---

## 🔧 변경 필수 포인트 (API 변경 시)

### 1. 전역 카테고리 ID 변경 (현재 고정 값)

**위치:** `get_categories()` 함수

```python
params = {'categoryId': '20010001'}  # ← 여기 수정
```

### 2. JS 정규식 패턴 변경

**위치:** `fetch_subsidy_worker()` 함수

```python
match = re.search(
    r'parseObject\(\s*(\[.*?\])\s*\);',  # ← 여기 수정
    resp.text,
    re.DOTALL
)
```

### 3. 필드 매핑 변경

**위치:** `fetch_subsidy_worker()` 함수

```python
extracted.append({
    '제조사': item.get('companyNm', ''),        # ← 필드명 변경 시 수정
    '공시지원금': item.get('telecomSaleAmt', 0),
    '유통망지원금': item.get('selDsnetSupmAmt', 0),
    ...
})
```

---

## 🚀 실행 방법

```bash
# 1. 패키지 설치
pip install -r requirements.txt

# 2. 테스트 실행 (첫 카테고리, 첫 요금제만)
python skt_crawler_final_parallel.py

# 3. 전체 실행
# 파일 최하단: test_mode=False로 변경 후 실행
```
