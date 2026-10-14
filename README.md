# 비트코인은 성숙한 자산이 되어가고 있는가?

BTCUSDT 일봉(2017-08-17 ~ 2026-10-13, 3,345일) 시계열 분석 프로젝트입니다.
반감기 주기, 변동성, 외부 요인(나스닥·미국 기준금리), 요일 효과를 분석했습니다.

📄 **분석 리포트: [REPORT.md](REPORT.md)**
📊 **대시보드 실행 방법과 시나리오: [docs/DASHBOARD.md](docs/DASHBOARD.md)**

## 폴더 구조

```
├── README.md
├── REPORT.md            # 분석 리포트
├── requirements.txt     # 라이브러리 버전
├── collect_data.py      # 1) 데이터 수집 → data/
├── check_data.py        # 2) 결측치·이상치 점검
├── analyze.py           # 3) 질문별 분석 + 그래프 → images/fig1~7
├── decompose.py         # 4) [보너스] STL 시계열 분해 → images/fig8
├── dashboard.py         # 5) [보너스] Streamlit 대시보드
├── data/                # 수집한 CSV
├── images/              # 리포트에 들어가는 그래프
└── docs/                # 대시보드 문서와 스크린샷
```

## 실행 방법

**환경:** Python 3.10 이상 (개발: Python 3.12.13, macOS)

```bash
# 가상환경 만들기와 라이브러리 설치
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 순서대로 실행
.venv/bin/python collect_data.py       # 데이터 수집 (인터넷 필요, API 키 불필요)
.venv/bin/python check_data.py         # 데이터 점검 결과 출력
.venv/bin/python analyze.py            # 분석 수치 출력 + images/fig1~7.png 저장
.venv/bin/python decompose.py          # STL 분해 수치 출력 + images/fig8.png 저장
.venv/bin/streamlit run dashboard.py   # 대시보드 → http://localhost:8501
```

- Windows에서는 `.venv/bin/` 대신 `.venv\Scripts\`를 사용합니다.
- 그래프의 한글 폰트는 설치된 것 중에서 자동으로 고릅니다 (macOS: Apple SD Gothic Neo, Windows: 맑은 고딕, Linux: 나눔고딕).

## 데이터 출처

| 파일 | 내용 | 출처 | 수집 방법 |
|---|---|---|---|
| `data/btcusdt_1d.csv` | BTCUSDT 현물 일봉 (시가·고가·저가·종가·거래량) | [Binance](https://www.binance.com) | 공개 REST API `GET /api/v3/klines` (symbol=BTCUSDT, interval=1d) |
| `data/nasdaq_1d.csv` | 나스닥 종합지수 `^IXIC` 일봉 | [Yahoo Finance](https://finance.yahoo.com) | `yfinance` 라이브러리 |
| `data/fed_rate_1d.csv` | 미국 실효 연방기금금리 `DFF` (일별) | [FRED](https://fred.stlouisfed.org/series/DFF), Federal Reserve Bank of St. Louis | FRED CSV 다운로드 엔드포인트 |

- **저장소에 포함된 데이터:** `btcusdt_1d.csv`, `fed_rate_1d.csv`
- **포함하지 않은 데이터:** `nasdaq_1d.csv` (Yahoo Finance 약관상 재배포하지 않음) → 분석 전에 `collect_data.py`를 실행하면 생성됩니다.
- 수집 기간: 2017-08-17 (바이낸스 BTCUSDT 거래 시작일) ~ 2026-10-13 (분석 시점 2026-10-14의 전날)
- 바이낸스 일봉은 UTC 00:00 기준으로 하루가 나뉩니다.
- 같은 스크립트를 다시 실행하면 같은 기간의 데이터를 다시 받을 수 있습니다. 다만 데이터 제공처에서 과거 값을 수정하면 결과가 조금 달라질 수 있습니다.

## 라이선스 및 이용 주의

이 저장소의 데이터는 **학습 목적의 비상업적 분석**에만 사용했습니다. 각 데이터의 권리는 원 제공처에 있으며, 재사용할 때는 각 제공처의 약관을 직접 확인해야 합니다.

- **Binance:** 시장 데이터는 Binance 이용약관(Terms of Use)과 API 이용 조건을 따릅니다. 국가나 지역에 따라 API 접근이 제한될 수 있습니다.
- **Yahoo Finance:** `yfinance`는 Yahoo가 공식 제공하는 도구가 아니며, Yahoo의 데이터는 개인적 용도로만 사용하도록 되어 있습니다. 재배포나 상업적 이용은 Yahoo 약관을 확인해야 합니다.
- **FRED:** 출처 표기 — Board of Governors of the Federal Reserve System (US), *Federal Funds Effective Rate [DFF]*, retrieved from FRED, Federal Reserve Bank of St. Louis. 이용 조건은 FRED 이용약관과 시리즈별 안내를 따릅니다.
- 이 분석은 투자 조언이 아닙니다.
