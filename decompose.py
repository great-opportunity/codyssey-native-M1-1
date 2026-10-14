"""
[보너스 A] 시계열 분해 - 비트코인 가격을 추세 / 계절성 / 잔차로 나눈다.

방법: STL (Seasonal-Trend decomposition using LOESS)
- 가격이 수십 배 변하므로 로그 가격을 분해한다.
  → 로그에서는 '더하기'가 원래 가격의 '곱하기(%)'에 해당해 계절 성분을 %로 읽을 수 있다.
- 주기: 1년(365일). (요일 효과는 analyze.py Q4에서 직접 집계)
- robust=False (기본값)를 쓴다. robust=True로 하면 극단값의 가중치를 낮추는 과정에서
  계절 성분과 잔차가 서로 반대로 크게 움직이며 상쇄되어(상관 약 -0.46) 분해가 왜곡되었다.
- 결과가 설정에 얼마나 민감한지 보기 위해 추세 창/계절 평활 설정을 바꿔 계절성 강도를 비교한다.
- 교차 확인: STL과 별개로 '달력 월별 수익률'을 직접 집계해 같은 경향이 보이는지 확인한다.

계절성 강도 (Hyndman & Athanasopoulos, "Forecasting: Principles and Practice"):
    F_s = max(0, 1 - Var(잔차) / Var(계절 + 잔차))
    0에 가까우면 계절성이 거의 없고, 1에 가까우면 강하다.

실행: python decompose.py
결과: images/fig8_stl_decompose.png, 콘솔에 계절성 강도
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL

# 그래프 스타일은 analyze.py와 같은 것을 쓴다
from analyze import (BLUE, ORANGE, AQUA, GRAY, TEXT, TEXT_SUB, IMG_DIR,
                     add_source, save, load_data, pct_fmt)


def seasonal_strength(res) -> float:
    resid, seasonal = res.resid, res.seasonal
    return max(0.0, 1 - np.var(resid) / np.var(seasonal + resid))


def trend_strength(res) -> float:
    resid, trend = res.resid, res.trend
    return max(0.0, 1 - np.var(resid) / np.var(trend + resid))


def main():
    IMG_DIR.mkdir(exist_ok=True)
    btc, _, _ = load_data()
    log_price = np.log(btc["close"]).asfreq("D")

    print("=" * 60)
    print("[보너스 A] STL 시계열 분해 (로그 종가)")
    print("=" * 60)

    res = STL(log_price, period=365).fit()
    print("\n주기 365일")
    print(f"  추세 강도   F_t = {trend_strength(res):.3f}")
    print(f"  계절성 강도 F_s = {seasonal_strength(res):.3f}")

    # 민감도 확인: 설정을 바꿔도 '계절성이 약하다'는 결론이 유지되는가
    print("\n[민감도 확인] 주기 365일, 설정별 계절성 강도")
    settings = [
        ("기본값", {}),
        ("추세 창 367일 (짧게)", {"trend": 367}),
        ("계절 패턴 고정 (매년 같은 모양)", {"seasonal": 9999}),
        ("robust=True (참고: 왜곡됨)", {"robust": True}),
    ]
    for name, kw in settings:
        r = STL(log_price, period=365, **kw).fit()
        print(f"  {name:<28} F_s = {seasonal_strength(r):.2f}")

    seasonal_pct = (np.exp(res.seasonal) - 1) * 100
    resid_pct = (np.exp(res.resid) - 1) * 100

    print("\n[연간 계절 성분: 월별 평균 (%)] - 그 달에 추세보다 평균 몇 % 위/아래였는가")
    by_month = seasonal_pct.groupby(seasonal_pct.index.month).mean()
    print(by_month.round(1).to_string())
    print(f"\n계절 성분 범위: {seasonal_pct.min():.1f}% ~ {seasonal_pct.max():.1f}%")
    print(f"잔차 범위:     {resid_pct.min():.1f}% ~ {resid_pct.max():.1f}%")
    print(f"잔차 표준편차: {resid_pct.std():.1f}%  /  계절 성분 표준편차: {seasonal_pct.std():.1f}%")

    # 교차 확인: 달력 월별 수익률 (월말 종가 기준)
    monthly = btc["close"].resample("ME").last().pct_change().dropna() * 100
    # 데이터가 월말 전에 끝나면 마지막 달은 한 달치가 아니므로 제외 (예: 2026-10은 1~13일뿐)
    if not btc.index[-1].is_month_end:
        monthly = monthly.iloc[:-1]
    g = monthly.groupby(monthly.index.month)
    cross = pd.DataFrame({
        "평균(%)": g.mean(), "중앙값(%)": g.median(),
        "상승한 해 비율(%)": g.apply(lambda x: (x > 0).mean() * 100), "표본 수(년)": g.count(),
    })
    print("\n[교차 확인] 달력 월별 수익률")
    print(cross.round(1).T.to_string())

    # 그래프: 원본 / 추세 / 계절 / 잔차 (패널마다 각자의 y축)
    fig, axes = plt.subplots(4, 1, figsize=(11, 9.5), sharex=True,
                             height_ratios=[2.2, 2.2, 1.5, 1.5])
    price = btc["close"]
    trend_price = np.exp(res.trend)

    axes[0].plot(price.index, price, color=BLUE, linewidth=1)
    axes[0].set_yscale("log")
    axes[0].set_title("① 원본: 종가 (로그 스케일)", fontsize=11)

    axes[1].plot(trend_price.index, trend_price, color=ORANGE, linewidth=2)
    axes[1].set_yscale("log")
    axes[1].set_title("② 추세 (Trend)", fontsize=11)

    for ax in axes[:2]:
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"${v:,.0f}"))

    axes[2].plot(seasonal_pct.index, seasonal_pct, color=AQUA, linewidth=1.2)
    axes[2].axhline(0, color=GRAY, linewidth=0.8)
    axes[2].set_title("③ 연간 계절성 (Seasonal, 추세 대비 %)", fontsize=11)

    axes[3].plot(resid_pct.index, resid_pct, color=TEXT_SUB, linewidth=0.8)
    axes[3].axhline(0, color=GRAY, linewidth=0.8)
    axes[3].set_title("④ 잔차 (Residual, 추세 대비 %)", fontsize=11)

    # 계절과 잔차는 같은 눈금으로 맞춰 크기를 직접 비교할 수 있게 한다
    lim = max(seasonal_pct.abs().max(), resid_pct.abs().max()) * 1.1
    for ax in axes[2:]:
        ax.set_ylim(-lim, lim)
        ax.yaxis.set_major_formatter(pct_fmt)

    s365 = seasonal_strength(res)
    fig.suptitle(f"비트코인 가격의 STL 분해 (주기 365일) — 연간 계절성 강도 {s365:.2f}",
                 x=0.01, ha="left", fontsize=13, fontweight="bold", color=TEXT)
    fig.tight_layout(rect=(0, 0.03, 1, 0.97))
    add_source(fig, "출처: Binance BTCUSDT 일봉. statsmodels STL(period=365), 로그 종가 분해. ③④는 같은 y축 범위")
    save(fig, "fig8_stl_decompose.png")


if __name__ == "__main__":
    main()
