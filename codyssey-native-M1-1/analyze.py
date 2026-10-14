"""
비트코인(BTCUSDT) 시계열 분석 - 질문별 수치 계산과 그래프 저장.

주제: 비트코인은 성숙한 자산이 되어가고 있는가?
  Q1. 4년 주기는 반복되는가?
  Q2. 변동성은 줄어들고 있는가?
  Q3. 외부 요인(나스닥, 금리)과 어떤 관계인가?
  Q4. 주말과 평일의 움직임이 다른가?

실행: python analyze.py   (먼저 collect_data.py로 data/ 를 채워야 함)
결과: images/*.png 그래프, 콘솔에 질문별 핵심 수치
"""

from pathlib import Path

import matplotlib.dates as mdates
from matplotlib import font_manager
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter

DATA_DIR = Path("data")
IMG_DIR = Path("images")

# 반감기 날짜 (UTC). 2016년 반감기는 데이터 시작 전이지만 주기 계산에 참고로 사용
HALVINGS = pd.to_datetime(["2016-07-09", "2020-05-11", "2024-04-20"])

# 이상치 후보 기준 (check_data.py와 동일): 일간 수익률 |z| > 3
Z_THRESHOLD = 3

# 반감기 후 이 기간(일) 안의 최고가를 그 사이클의 고점으로 본다
PEAK_WINDOW = 730

# 연율화 계수: 비트코인은 1년 365일 거래
DAYS_PER_YEAR = 365

# 미국 기준금리 국면 (FOMC 결정일 기준으로 구분)
RATE_REGIMES = [
    ("2017-08-17", "2018-12-31", "인상기 1"),
    ("2019-01-01", "2019-07-31", "동결"),
    ("2019-08-01", "2020-03-15", "인하기 1"),
    ("2020-03-16", "2022-03-16", "제로금리"),
    ("2022-03-17", "2023-07-26", "인상기 2"),
    ("2023-07-27", "2024-09-17", "고금리 동결"),
    ("2024-09-18", "2025-12-31", "인하기 2"),
]


# ---------------------------------------------------------------
# 그래프 공통 스타일
# ---------------------------------------------------------------
SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
TEXT_SUB = "#52514e"
GRID = "#e4e3df"
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
GRAY = "#8a8985"


def pick_korean_font():
    """macOS, Windows, Linux 순으로 설치된 한글 폰트 중 첫 번째를 고른다."""
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in ["Apple SD Gothic Neo", "Malgun Gothic", "NanumGothic"]:
        if name in installed:
            return name
    return "DejaVu Sans"  # 한글 폰트가 없으면 글자가 깨질 수 있음


plt.rcParams.update({
    "font.family": pick_korean_font(),
    "axes.unicode_minus": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID,
    "axes.labelcolor": TEXT_SUB,
    "axes.titlecolor": TEXT,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": GRID,
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": TEXT_SUB,
    "ytick.color": TEXT_SUB,
    "legend.frameon": False,
    "lines.linewidth": 1.6,
    "figure.dpi": 110,
})

price_fmt = FuncFormatter(lambda v, _: f"${v:,.0f}")
pct_fmt = FuncFormatter(lambda v, _: f"{v:.0f}%")


def add_source(fig, text):
    fig.text(0.01, 0.01, text, fontsize=8, color=TEXT_SUB, ha="left", va="bottom")


def save(fig, name):
    path = IMG_DIR / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  → 그래프 저장: {path}")


# ---------------------------------------------------------------
# 데이터 불러오기
# ---------------------------------------------------------------
def load_data():
    btc = pd.read_csv(DATA_DIR / "btcusdt_1d.csv", parse_dates=["date"]).set_index("date")
    btc["ret"] = btc["close"].pct_change() * 100
    z = (btc["ret"] - btc["ret"].mean()) / btc["ret"].std()
    # 이상치는 삭제하지 않고 표시만 해 둔다
    btc["is_outlier"] = z.abs() > Z_THRESHOLD

    nasdaq = pd.read_csv(DATA_DIR / "nasdaq_1d.csv", parse_dates=["date"]).set_index("date")
    rate = pd.read_csv(DATA_DIR / "fed_rate_1d.csv", parse_dates=["date"]).set_index("date")
    return btc, nasdaq, rate


# ---------------------------------------------------------------
# Q1. 4년 주기는 반복되는가?
# ---------------------------------------------------------------
def q1_cycle(btc):
    print("\n" + "=" * 60)
    print("Q1. 4년 주기는 반복되는가?")
    print("=" * 60)
    close = btc["close"]

    # 사이클 고점 = 반감기 후 PEAK_WINDOW일 이내의 최고 종가
    # (반감기~다음 반감기 전체에서 찾으면 2024-03처럼 다음 사이클 직전 고가가 잡히므로 범위를 제한)
    # 저점 = 그 고점 이후 다음 반감기 전까지(또는 데이터 끝까지)의 최저 종가
    cycles = []
    for i, h in enumerate(HALVINGS):
        win = close[(close.index >= h) & (close.index <= h + pd.Timedelta(days=PEAK_WINDOW))]
        peak_date, peak = win.idxmax(), win.max()
        nxt = HALVINGS[i + 1] if i + 1 < len(HALVINGS) else close.index[-1] + pd.Timedelta(days=1)
        after = close[(close.index > peak_date) & (close.index < nxt)]
        trough_date, trough = after.idxmin(), after.min()
        cycles.append({
            "반감기": h.date(),
            "고점일": peak_date.date(),
            "고점가": peak,
            "반감기→고점(일)": (peak_date - h).days,
            "고점 후 저점일": trough_date.date(),
            "저점가": trough,
            "고점 대비 하락률(%)": (trough / peak - 1) * 100,
            "고점→저점(일)": (trough_date - peak_date).days,
        })
    cyc = pd.DataFrame(cycles)
    print("\n[사이클별 고점과 이후 저점]")
    print(cyc.round(1).to_string(index=False))
    print("  * 2016 반감기 가격은 데이터 범위 밖. 마지막 저점은 2025-12-31까지만 본 값(진행 중)")

    # 반감기 당일 대비 고점 배수 (데이터가 있는 반감기만)
    print("\n[반감기 당일 가격 대비 사이클 고점 배수]")
    for _, r in cyc.iterrows():
        h = pd.Timestamp(r["반감기"])
        if h not in close.index:
            continue
        h_price = close.loc[h]
        print(f"  {h.date()} 반감기: ${h_price:,.0f} → 고점 ${r['고점가']:,.0f} ({r['고점가'] / h_price:.1f}배)")

    # 그래프 1: 로그 가격 + 200일 이동평균 + 반감기
    ma200 = close.rolling(200).mean()
    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.plot(close.index, close, color=BLUE, linewidth=1.2, label="종가")
    ax.plot(ma200.index, ma200, color=ORANGE, linewidth=2, label="200일 이동평균")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(price_fmt)
    ax.set_ylim(top=close.max() * 2.2)  # 고점 라벨이 들어갈 여백
    for h in HALVINGS[1:]:
        ax.axvline(h, color=TEXT_SUB, linestyle="--", linewidth=1)
        ax.text(h, ax.get_ylim()[1], f" 반감기\n {h.date()}", va="top", fontsize=9, color=TEXT_SUB)
    for _, r in cyc.iterrows():
        d = pd.Timestamp(r["고점일"])
        ax.plot(d, r["고점가"], "o", markersize=7, color=BLUE, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(f"고점 ${r['고점가']:,.0f}\n({d.date()})", (d, r["고점가"]),
                    xytext=(0, 10), textcoords="offset points", ha="center", va="bottom",
                    fontsize=9, color=TEXT)
    ax.set_title("비트코인 가격 (로그 스케일)과 반감기")
    ax.legend(loc="lower right")
    add_source(fig, "출처: Binance BTCUSDT 일봉 (2017-08-17 ~ 2025-12-31)")
    save(fig, "fig1_price_halving.png")

    # 그래프 2: 반감기 기준으로 사이클 겹쳐 보기 (반감기 당일 가격 = 1)
    fig, ax = plt.subplots(figsize=(11, 5.2))
    for i, (h, color) in enumerate(zip(HALVINGS[1:], [BLUE, ORANGE]), start=1):
        # 반감기 500일 전부터 다음 반감기 전날(또는 데이터 끝)까지
        end = HALVINGS[i + 1] - pd.Timedelta(days=1) if i + 1 < len(HALVINGS) else close.index[-1]
        rel = (close / close.loc[h]).loc[h - pd.Timedelta(days=500):end]
        days = (rel.index - h).days
        ax.plot(days, rel.values, color=color, linewidth=1.6, label=f"{h.year} 반감기 사이클")
        r = cyc[cyc["반감기"] == h.date()].iloc[0]
        pk = pd.Timestamp(r["고점일"])
        ax.plot((pk - h).days, rel.loc[pk], "o", markersize=7, color=color,
                markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(f"{(pk - h).days}일 후 고점\n×{rel.loc[pk]:.1f}", ((pk - h).days, rel.loc[pk]),
                    xytext=(8, 4), textcoords="offset points", fontsize=9, color=TEXT)
    ax.axvline(0, color=TEXT_SUB, linestyle="--", linewidth=1)
    ax.axhline(1, color=GRAY, linewidth=0.8)
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"×{v:g}"))
    ax.set_xlabel("반감기로부터 경과일")
    ax.set_ylabel("반감기 당일 가격 대비 배수")
    ax.set_title("반감기 기준으로 겹쳐 본 두 사이클")
    ax.legend(loc="upper left")
    add_source(fig, "출처: Binance BTCUSDT 일봉. 반감기 당일 종가를 1로 맞춤")
    save(fig, "fig2_cycle_overlay.png")

    # 그래프 3: 역대 최고가 대비 하락률 (drawdown)
    dd = (close / close.cummax() - 1) * 100
    fig, ax = plt.subplots(figsize=(11, 4.2))
    ax.fill_between(dd.index, dd, 0, color=BLUE, alpha=0.25, linewidth=0)
    ax.plot(dd.index, dd, color=BLUE, linewidth=1.2)
    for _, r in cyc.iterrows():
        d = pd.Timestamp(r["고점 후 저점일"])
        ax.plot(d, dd.loc[d], "o", markersize=7, color=BLUE, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(f"{dd.loc[d]:.0f}%\n({d.date()})", (d, dd.loc[d]),
                    xytext=(8, -6), textcoords="offset points", fontsize=9, color=TEXT)
    ax.yaxis.set_major_formatter(pct_fmt)
    ax.set_ylim(-100, 5)
    ax.set_title("역대 최고가 대비 하락률 (Drawdown)")
    add_source(fig, "출처: Binance BTCUSDT 일봉. 그 시점까지의 최고 종가 대비 하락 폭")
    save(fig, "fig3_drawdown.png")


# ---------------------------------------------------------------
# Q2. 변동성은 줄어들고 있는가?
# ---------------------------------------------------------------
def q2_volatility(btc):
    print("\n" + "=" * 60)
    print("Q2. 변동성은 줄어들고 있는가?")
    print("=" * 60)
    ret = btc["ret"]
    # 30일 롤링 표준편차를 연율화 (일간 표준편차 × √365)
    vol30 = ret.rolling(30).std() * np.sqrt(DAYS_PER_YEAR)

    yearly = pd.DataFrame({
        "일간 표준편차(%)": ret.groupby(ret.index.year).std(),
        "연율화 변동성(%)": ret.groupby(ret.index.year).std() * np.sqrt(DAYS_PER_YEAR),
        "|수익률|≥5% 일수": (ret.abs() >= 5).groupby(ret.index.year).sum(),
        "이상치 후보 일수": btc["is_outlier"].groupby(btc.index.year).sum(),
        "거래일수": ret.groupby(ret.index.year).count(),
    })
    print("\n[연도별 변동성]")
    print(yearly.round(2).to_string())
    print("  * 2017년은 8/17부터라 일수가 적음")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.2), height_ratios=[3, 2])
    ax1.plot(vol30.index, vol30, color=BLUE, linewidth=1.2, label="30일 롤링 변동성(연율화)")
    # 연도별 평균 수준을 계단선으로 겹쳐 추세를 보기 쉽게
    yearly_level = vol30.groupby(vol30.index.year).transform("mean")
    ax1.plot(yearly_level.index, yearly_level, color=ORANGE, linewidth=2, label="연도별 평균")
    ax1.yaxis.set_major_formatter(pct_fmt)
    ax1.set_title("비트코인 변동성 추이")
    ax1.legend(loc="upper right")

    years = yearly.index.astype(str)
    ax2.bar(years, yearly["|수익률|≥5% 일수"], color=BLUE, width=0.6)
    for x, v, n in zip(years, yearly["|수익률|≥5% 일수"], yearly["거래일수"]):
        ax2.text(x, v, f"{v}일", ha="center", va="bottom", fontsize=9, color=TEXT)
    ax2.set_title("하루에 ±5% 이상 움직인 날 수 (연도별)", fontsize=11)
    ax2.grid(axis="x", visible=False)
    ax2.set_ylim(0, yearly["|수익률|≥5% 일수"].max() * 1.18)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    add_source(fig, "출처: Binance BTCUSDT 일봉. 2017년은 8/17~12/31 (137일)")
    save(fig, "fig4_volatility.png")


# ---------------------------------------------------------------
# Q3. 외부 요인(나스닥, 금리)과 어떤 관계인가?
# ---------------------------------------------------------------
def align_with_nasdaq(btc, nasdaq):
    """
    두 시장이 모두 거래한 날짜의 '가격'을 먼저 맞춘 뒤 수익률을 계산한다.
    이렇게 하면 월요일 수익률이 두 시장 모두 '금요일 종가 → 월요일 종가'가 되어
    비트코인의 주말 움직임이 월요일 수익률에 포함된다.
    """
    prices = pd.concat([btc["close"].rename("btc"), nasdaq["close"].rename("nasdaq")],
                       axis=1, join="inner")
    return prices.pct_change().dropna() * 100, prices


def q3_external(btc, nasdaq, rate):
    print("\n" + "=" * 60)
    print("Q3. 외부 요인(나스닥, 금리)과 어떤 관계인가?")
    print("=" * 60)
    rets, prices = align_with_nasdaq(btc, nasdaq)
    print(f"\n[날짜 맞추기] BTC {len(btc)}일, 나스닥 {len(nasdaq)}일 → 공통 거래일 {len(prices)}일")

    corr_all = rets["btc"].corr(rets["nasdaq"])
    print(f"전체 기간 일간 수익률 상관계수: {corr_all:.3f}")

    # 보조 검증: 주간 수익률(금요일 종가 기준)로도 계산
    weekly = prices.resample("W-FRI").last().pct_change().dropna()
    # 마지막 주(2025-12-29~31)는 2026-01-02(금)로 라벨이 붙으므로 제외
    weekly = weekly[weekly.index <= prices.index[-1]]
    yearly_corr = rets.groupby(rets.index.year).apply(lambda g: g["btc"].corr(g["nasdaq"]))
    yearly_corr_w = weekly.groupby(weekly.index.year).apply(lambda g: g["btc"].corr(g["nasdaq"]))
    print("\n[연도별 상관계수: 일간 vs 주간(보조 검증)]")
    print(pd.DataFrame({"일간": yearly_corr, "주간": yearly_corr_w}).round(2).to_string())

    roll_corr = rets["btc"].rolling(90).corr(rets["nasdaq"])

    # 금리 국면별 통계
    rows = []
    for start, end, name in RATE_REGIMES:
        p = btc["close"].loc[start:end]
        r = btc["ret"].loc[start:end]
        days = (p.index[-1] - p.index[0]).days
        rr = rets.loc[start:end]
        rows.append({
            "국면": name,
            "기간": f"{start} ~ {end}",
            "평균 금리(%)": rate["fed_rate"].loc[start:end].mean(),
            "BTC 기간 수익률(%)": (p.iloc[-1] / p.iloc[0] - 1) * 100,
            "BTC 연환산 수익률(%)": ((p.iloc[-1] / p.iloc[0]) ** (DAYS_PER_YEAR / days) - 1) * 100,
            "BTC 연율화 변동성(%)": r.std() * np.sqrt(DAYS_PER_YEAR),
            "나스닥 상관계수": rr["btc"].corr(rr["nasdaq"]),
        })
    regimes = pd.DataFrame(rows)
    print("\n[금리 국면별 비트코인]")
    print(regimes.round(2).to_string(index=False))

    # 그래프 5: 나스닥과의 90일 롤링 상관계수
    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.plot(roll_corr.index, roll_corr, color=BLUE, linewidth=1.4, label="90거래일 롤링 상관계수")
    for y, v in yearly_corr.items():
        ax.hlines(v, max(pd.Timestamp(f"{y}-01-01"), rets.index[0]), pd.Timestamp(f"{y}-12-31"),
                  color=ORANGE, linewidth=2.2, label="연도별 상관계수" if y == yearly_corr.index[0] else None)
    ax.axhline(0, color=GRAY, linewidth=0.8)
    ax.set_ylim(-0.4, 0.9)
    ax.set_title("비트코인과 나스닥의 상관계수 추이 (일간 수익률)")
    ax.legend(loc="upper left")
    add_source(fig, "출처: Binance BTCUSDT, Yahoo Finance ^IXIC. 두 시장이 모두 거래한 날만 사용")
    save(fig, "fig5_nasdaq_corr.png")

    # 그래프 6: 가격과 금리를 위아래로 (y축 2개를 겹치지 않고 패널을 나눔)
    regime_color = {"인상기 1": ORANGE, "인상기 2": ORANGE, "고금리 동결": YELLOW,
                    "동결": GRAY, "인하기 1": BLUE, "인하기 2": BLUE, "제로금리": AQUA}
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True, height_ratios=[3, 1.6])
    for start, end, name in RATE_REGIMES:
        for ax in (ax1, ax2):
            ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=regime_color[name],
                       alpha=0.12, linewidth=0)
        mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2
        ax2.text(mid, 6.1, name, ha="center", va="bottom", fontsize=8.5, color=TEXT)
    ax1.plot(btc.index, btc["close"], color=BLUE, linewidth=1.2)
    ax1.set_yscale("log")
    ax1.yaxis.set_major_formatter(price_fmt)
    ax1.set_title("비트코인 가격과 미국 기준금리 국면")
    ax2.plot(rate.index, rate["fed_rate"], color=TEXT, linewidth=1.6)
    ax2.set_ylim(0, 7)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax2.set_ylabel("기준금리")
    ax2.xaxis.set_major_locator(mdates.YearLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    add_source(fig, "출처: Binance BTCUSDT, FRED DFF(실효 연방기금금리). 배경색 = 금리 국면")
    save(fig, "fig6_rate_regimes.png")


# ---------------------------------------------------------------
# Q4. 주말과 평일의 움직임이 다른가?
# ---------------------------------------------------------------
def q4_weekday(btc):
    print("\n" + "=" * 60)
    print("Q4. 주말과 평일의 움직임이 다른가?")
    print("=" * 60)
    df = btc[["ret"]].dropna().copy()
    names = ["월", "화", "수", "목", "금", "토", "일"]
    df["weekday"] = df.index.dayofweek
    df["is_weekend"] = df["weekday"] >= 5

    by_day = df.groupby("weekday")["ret"].agg(["mean", "median", "std", "count"])
    by_day.index = names
    print("\n[요일별 일간 수익률(%)] - 이상치 포함, 평균과 중앙값 함께")
    print(by_day.round(3).to_string())

    yearly = df.groupby([df.index.year, "is_weekend"])["ret"].std().unstack()
    yearly.columns = ["평일 표준편차", "주말 표준편차"]
    yearly["주말/평일 비율"] = yearly["주말 표준편차"] / yearly["평일 표준편차"]
    print("\n[연도별 주말 vs 평일 변동성]")
    print(yearly.round(2).to_string())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.8), width_ratios=[3, 2])
    data = [df.loc[df["weekday"] == i, "ret"] for i in range(7)]
    bp = ax1.boxplot(data, tick_labels=names, showfliers=False, patch_artist=True, widths=0.55,
                     medianprops={"color": TEXT, "linewidth": 1.6},
                     whiskerprops={"color": TEXT_SUB}, capprops={"color": TEXT_SUB})
    for i, box in enumerate(bp["boxes"]):
        box.set_facecolor(ORANGE if i >= 5 else BLUE)
        box.set_alpha(0.55)
        box.set_edgecolor(SURFACE)
    ax1.axhline(0, color=GRAY, linewidth=0.8)
    ax1.yaxis.set_major_formatter(pct_fmt)
    ax1.set_title("요일별 일간 수익률 분포")
    ax1.grid(axis="x", visible=False)
    ax1.text(0.99, 0.02, "상자 = 중간 50%, 수염 = 1.5×IQR\n(극단값 점은 생략)", transform=ax1.transAxes,
             ha="right", va="bottom", fontsize=8.5, color=TEXT_SUB)

    years = yearly.index.astype(str)
    x = np.arange(len(years))
    ax2.bar(x - 0.2, yearly["평일 표준편차"], width=0.38, color=BLUE, label="평일")
    ax2.bar(x + 0.2, yearly["주말 표준편차"], width=0.38, color=ORANGE, label="주말")
    ax2.set_xticks(x, years, rotation=45)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.1f}%"))
    ax2.set_title("연도별 일간 변동성: 평일 vs 주말", fontsize=11)
    ax2.grid(axis="x", visible=False)
    ax2.legend(loc="upper right")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    add_source(fig, "출처: Binance BTCUSDT 일봉. 요일은 UTC 기준(한국시간 오전 9시~다음날 오전 9시)")
    save(fig, "fig7_weekday.png")


def main():
    IMG_DIR.mkdir(exist_ok=True)
    pd.set_option("display.width", 160)
    btc, nasdaq, rate = load_data()
    print(f"BTC {btc.index.min().date()} ~ {btc.index.max().date()} ({len(btc)}일), "
          f"이상치 후보 {btc['is_outlier'].sum()}일 (삭제하지 않고 유지)")
    q1_cycle(btc)
    q2_volatility(btc)
    q3_external(btc, nasdaq, rate)
    q4_weekday(btc)


if __name__ == "__main__":
    main()
