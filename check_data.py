"""
수집한 데이터의 기본 정보, 결측치, 이상치 후보를 점검한다.

실행: python check_data.py
"""

import pandas as pd

df = pd.read_csv("data/btcusdt_1d.csv", parse_dates=["date"])

# 1. 기본 정보
print("=== 1. 기본 정보 ===")
print(f"기간: {df['date'].min().date()} ~ {df['date'].max().date()}")
print(f"행 수: {len(df)}")
print(f"컬럼: {list(df.columns)}")
print()
print(df.describe().round(2).to_string())
print()

# 2. 결측치
print("=== 2. 결측치 ===")
print("컬럼별 빈 값 개수:")
print(df.isna().sum().to_string())

# 빈 값이 없어도 '날짜 자체가 빠진' 경우가 있을 수 있으므로 따로 확인
full_range = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
missing_dates = full_range.difference(df["date"])
print(f"\n빠진 날짜 수: {len(missing_dates)}")
if len(missing_dates) > 0:
    print(list(missing_dates.date))

dup = df["date"].duplicated().sum()
print(f"중복 날짜 수: {dup}")
print()

# 3. 값의 논리적 오류 (가격 데이터라면 반드시 성립해야 하는 조건)
print("=== 3. 값 논리 검사 ===")
bad_hl = df[df["high"] < df["low"]]
bad_range = df[(df["close"] > df["high"]) | (df["close"] < df["low"])]
non_positive = df[(df[["open", "high", "low", "close"]] <= 0).any(axis=1)]
print(f"high < low 인 행: {len(bad_hl)}")
print(f"close가 [low, high] 범위를 벗어난 행: {len(bad_range)}")
print(f"가격이 0 이하인 행: {len(non_positive)}")
print()

# 4. 이상치 후보: 일간 수익률이 평균에서 3 표준편차 이상 벗어난 날
print("=== 4. 이상치 후보 (일간 수익률 |z| > 3) ===")
df["return_pct"] = df["close"].pct_change() * 100
mean, std = df["return_pct"].mean(), df["return_pct"].std()
df["z"] = (df["return_pct"] - mean) / std
outliers = df[df["z"].abs() > 3]
print(f"일간 수익률 평균 {mean:.2f}%, 표준편차 {std:.2f}%")
print(f"이상치 후보 {len(outliers)}일:")
print(outliers[["date", "close", "return_pct", "z"]].round({"return_pct": 2, "z": 2}).to_string(index=False))
