# LG U+ 공시지원금 크롤러 문서

**버전:** v1.0  
**최종 수정:** 2026-01-21

---

## 📋 개요

**목적:** LG U+ 요금제별 공시지원금 자동 수집  
**출력:** 엑셀 파일 (~61,000건)

### LG U+ 사이트 분석

- React/Vue 기반 SPA
- RESTful API + JSON 응답
- Cloudflare 보호 (Selenium 쿠키 획득 필수)
- 10개씩 페이징 처리 응답 (CSR)

---

## 🔄 실행 흐름

```
1단계: Selenium 쿠키 획득 (15초)
   ↓
2단계: 요금제 78개 수집 (5G 64개 + LTE 14개)
   ↓
3단계: 지원금 수집 (병렬 처리, 78×3×N페이지)
   ↓
4단계: 엑셀 저장
```

---

## 📡 API 2개

### 1️⃣ 요금제 리스트 조회

```bash
GET https://www.lguplus.com/uhdc/fo/prdv/mdlbsufu/v1/mdlb-pp-list?hphnPpGrpKwrdCd=00&_=1737123456789
```

**파라미터:**

- `hphnPpGrpKwrdCd`: 00(5G), 01(LTE)
- `_`: 타임스탬프 (캐시 방지)

**응답:**

```json
{
  "dvicMdlbSufuPpList": [
    {
      "trmPpGrpNm": "5G 프리미어",
      "dvicMdlbSufuPpDetlList": [
        {
          "urcMblPpCd": "RPP00000001",
          "urcMblPpNm": "5G 프리미어 에센셜"
        }
      ]
    }
  ]
}
```

---

### 2️⃣ 지원금 상세 조회 (페이징)

```bash
GET https://www.lguplus.com/uhdc/fo/prdv/mdlbsufu/v2/mdlb-sufu-list
```

**파라미터:**

- `urcHphnEntrPsblKdCd`: 1(기변), 2(번이), 3(신규)
- `urcMblPpCd`: 요금제 코드
- `pageNo`: 페이지 번호 (1부터)
- `rowSize`: 10 (고정)
- `_`: 타임스탬프

**응답:**

```json
{
  "totalCnt": 135,
  "dvicMdlbSufuDtoList": [
    {
      "urcTrmMdlNm": "갤럭시 S24 울트라",
      "dlvrPrc": 1544400,
      "sixPlanPuanSuptAmt": 630000,
      "basicPlanPuanSuptAmt": 580000
    }
  ]
}
```

**특징:**

- 한 응답에 6개월/기본 약정 데이터 모두 포함
- 10개씩 반환 → 평균 14번 요청

---

## ⚙️ 수정 가능한 설정

### 1. 병렬 스레드 수

**위치:** 파일 최하단

```python
crawler.run(max_threads=5)
```

**권장값:**

- 3: 안전
- 5: 기본
- 10: 빠름 (위험)

---

### 2. 랜덤 딜레이

**위치:** `fetch_worker()` 함수

```python
time.sleep(random.uniform(0.05, 0.2))
```

**권장값:**

- `(0.1, 0.5)`: 안전
- `(0.05, 0.2)`: 기본
- `(0.01, 0.1)`: 빠름 (위험)

---

### 3. Selenium 대기 시간

**위치:** `get_cookies()` 함수

```python
time.sleep(15)  # 최소 10초 필요
```

---

### 4. Headless 모드

**위치:** `get_cookies()` 함수

```python
# options.add_argument('--headless')  # 주석 해제
```

---

### 5. 재시도 전략

**위치:** `fetch_worker()` 함수

```python
retry_strategy = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
```

---

## 🔧 변경 필수 포인트 (API 변경 시)

### 1. API 엔드포인트

**위치:** `__init__()` 함수

```python
self.base_url = "https://www.lguplus.com"
```

**위치:** `get_plans()` 함수

```python
api_url = f'{self.base_url}/uhdc/fo/prdv/mdlbsufu/v1/mdlb-pp-list'
```

---

### 2. 요금제 카테고리 코드

**위치:** `get_plans()` 함수

```python
categories = [
    ('00', '5G'),
    ('01', 'LTE')
]
```

---

### 3. 가입 유형 코드

**위치:** `__init__()` 함수

```python
self.signup_types = {
    '1': '기기변경',
    '2': '번호이동',
    '3': '신규가입'
}
```

---

### 4. 필드 매핑

**위치:** `fetch_worker()` 함수

```python
results.append({
    '모델명': m.get('urcTrmMdlNm'),
    '출고가': m.get('dlvrPrc'),
    '이통사지원금': m.get('sixPlanPuanSuptAmt')
})
```

---

## 🚀 실행 방법

### 일반 환경

```bash
# 패키지 설치
pip install requests pandas openpyxl selenium webdriver-manager urllib3

# 실행
python lguplus_crawler_final.py
```

---

### Podman 환경

```bash
# 빌드
podman build -t lguplus-crawler .

# 실행
podman run --rm -v ./output:/app/output:Z lguplus-crawler python lguplus_crawler_final.py
```

---

## ⚠️ 주의사항

**1. Cloudflare 쿠키 만료**

- 유효 시간: 약 1시간
- 실패 시 재실행

**2. Headless 모드**

- 서버 환경에서 필수
- 152번째 줄 주석 해제

**3. 메모리**

- 61,000건 수집 시 약 200MB

---

## 🐛 트러블슈팅

**쿠키 획득 실패:**

```bash
pip install --upgrade webdriver-manager
```

**429 에러:**

- 스레드 수 감소 (5 → 3)
- 딜레이 증가 (0.2 → 0.5)

---


## 📁 출력 파일

**파일명:** `lguplus_subsidy_YYYYMMDD_HHMMSS.xlsx`

**컬럼:**

- 요금제명
- 요금제유형 (5G/LTE)
- 가입유형
- 약정 (6개월/기본)
- 모델명
- 출고가
- 이통사지원금
- 추가지원금
- 유통망지원금
- 지원금총액

**예상 데이터:** ~61,000건