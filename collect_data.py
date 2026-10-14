"""
분석에 필요한 시계열 데이터 3종을 수집해 data/ 폴더에 CSV로 저장한다.

1. BTCUSDT 일봉   - 바이낸스 공개 API (주 분석 대상)
2. 나스닥 종합지수 - Yahoo Finance (^IXIC, 비교용)
3. 미국 기준금리   - FRED 실효 연방기금금리 (DFF, 비교용)

모두 API 키 없이 받을 수 있다.

실행: python collect_data.py
"""

from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf

# 바이낸스 BTCUSDT 거래가 시작된 날부터
START = "2017-08-17"
END = "2026-10-13"
DATA_DIR = Path("data")


# ---------------------------------------------------------------
# 1. BTCUSDT (바이낸스)
# ---------------------------------------------------------------
BINANCE_URL = "https://api.binance.com/api/v3/klines"

# 바이낸스 응답의 각 컬럼 의미 (공식 문서 순서 그대로)
KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def to_ms(date_str: str) -> int:
    """'YYYY-MM-DD'(UTC)를 밀리초 타임스탬프로 바꾼다."""
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def fetch_btc() -> pd.DataFrame:
    # END 당일 캔들까지 포함하도록 하루 끝 시각으로 설정
    end_ms = to_ms(END) + 24 * 60 * 60 * 1000 - 1
    cursor = to_ms(START)
    rows = []
    # 한 번 요청에 최대 1000개까지만 주므로 나눠서 요청한다
    while cursor <= end_ms:
        params = {
            "symbol": "BTCUSDT",
            "interval": "1d",
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 1000,
        }
        resp = requests.get(BINANCE_URL, params=params, timeout=10)
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        rows.extend(batch)
        # 마지막 캔들의 시작 시각 + 1ms부터 다음 요청
        cursor = batch[-1][0] + 1
        print(f"  {len(rows)}개 수집...")

    df = pd.DataFrame(rows, columns=KLINE_COLUMNS)
    df["date"] = pd.to_datetime(df["open_time"], unit="ms").dt.date
    num_cols = ["open", "high", "low", "close", "volume", "quote_volume"]
    df[num_cols] = df[num_cols].astype(float)
    return df[["date"] + num_cols + ["trades"]]


# ---------------------------------------------------------------
# 2. 나스닥 종합지수 (Yahoo Finance)
# ---------------------------------------------------------------
def fetch_nasdaq() -> pd.DataFrame:
    # yfinance의 end는 해당 날짜를 포함하지 않으므로 하루 뒤로 지정
    end_exclusive = (pd.Timestamp(END) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    raw = yf.download("^IXIC", start=START, end=end_exclusive,
                      auto_adjust=False, progress=False)
    # 종목 1개만 받아도 컬럼이 (항목, 티커) 2단으로 오므로 1단으로 정리
    raw.columns = raw.columns.get_level_values(0)
    df = raw.reset_index().rename(columns=str.lower)
    df["date"] = df["date"].dt.date
    return df[["date", "open", "high", "low", "close", "volume"]]


# ---------------------------------------------------------------
# 3. 미국 실효 연방기금금리 (FRED)
# ---------------------------------------------------------------
def fetch_fed_rate() -> pd.DataFrame:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    params = {"id": "DFF", "cosd": START, "coed": END}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text))
    return df.rename(columns={"observation_date": "date", "DFF": "fed_rate"})


def save(df: pd.DataFrame, name: str):
    path = DATA_DIR / name
    df.to_csv(path, index=False)
    print(f"저장 완료: {path} ({len(df)}행, {df['date'].iloc[0]} ~ {df['date'].iloc[-1]})")


def main():
    DATA_DIR.mkdir(exist_ok=True)
    print(f"수집 기간: {START} ~ {END}\n")

    print("[1/3] BTCUSDT (Binance)")
    save(fetch_btc(), "btcusdt_1d.csv")

    print("[2/3] 나스닥 종합지수 (Yahoo Finance)")
    save(fetch_nasdaq(), "nasdaq_1d.csv")

    print("[3/3] 미국 기준금리 (FRED DFF)")
    save(fetch_fed_rate(), "fed_rate_1d.csv")


if __name__ == "__main__":
    main()
