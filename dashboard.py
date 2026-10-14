"""
[보너스] 비트코인 분석 대시보드 - 기간과 조건을 바꿔가며 탐색한다.

실행: streamlit run dashboard.py
     (먼저 collect_data.py로 data/ 를 채워야 함)
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from analyze import (HALVINGS, RATE_REGIMES, DAYS_PER_YEAR, Z_THRESHOLD,
                     BLUE, ORANGE, AQUA, YELLOW, GRAY, align_with_nasdaq, load_data)

st.set_page_config(page_title="비트코인 성숙도 대시보드", layout="wide")

REGIME_COLOR = {"인상기 1": ORANGE, "인상기 2": ORANGE, "고금리 동결": YELLOW,
                "동결": GRAY, "인하기 1": BLUE, "인하기 2": BLUE, "제로금리": AQUA}
WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]


@st.cache_data
def get_data():
    return load_data()


def log_ticks(values):
    """로그 축 눈금을 1·3 단위로만 표시 (기본 눈금은 너무 빽빽함)"""
    lo, hi = np.nanmin(values), np.nanmax(values)
    ticks = [m * 10 ** k for k in range(2, 7) for m in (1, 3)]
    return [t for t in ticks if lo / 1.5 <= t <= hi * 1.5]


def base_layout(fig, height=420, title=None):
    # 제목은 맨 위, 범례는 그 아래(그래프 바로 위)에 두어 겹치지 않게 한다
    fig.update_layout(
        height=height, hovermode="x unified",
        title=dict(text=title, y=0.98, yanchor="top", x=0, xanchor="left") if title else None,
        margin=dict(l=10, r=10, t=80 if title else 40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)")
    return fig


btc_all, nasdaq_all, rate_all = get_data()

# ---------------------------------------------------------------
# 필터 (한 줄)
# ---------------------------------------------------------------
st.title("비트코인은 성숙한 자산이 되어가고 있는가?")
st.caption("Binance BTCUSDT 일봉 · Yahoo Finance ^IXIC · FRED DFF  |  2017-08-17 ~ 2025-12-31")

min_d, max_d = btc_all.index.min().date(), btc_all.index.max().date()
c1, c2, c3, c4 = st.columns([3, 1.3, 1.3, 1.3])
with c1:
    start, end = st.slider("기간", min_value=min_d, max_value=max_d,
                           value=(min_d, max_d), format="YYYY-MM")
with c2:
    ma_window = st.selectbox("이동평균", [50, 100, 200, 365], index=2, format_func=lambda d: f"{d}일")
with c3:
    roll_window = st.selectbox("롤링 창 (변동성·상관)", [30, 60, 90, 180], index=0,
                               format_func=lambda d: f"{d}일")
with c4:
    show_outliers = st.toggle("이상치 표시", value=True,
                              help=f"일간 수익률 |z| > {Z_THRESHOLD} 인 날 (삭제하지 않고 유지)")

s, e = pd.Timestamp(start), pd.Timestamp(end)
# 이동평균·롤링 값은 기간 시작 전 데이터까지 써서 계산한 뒤 자른다 (앞부분이 비지 않도록)
btc = btc_all.copy()
btc["ma"] = btc["close"].rolling(ma_window).mean()
btc["vol"] = btc["ret"].rolling(roll_window).std() * np.sqrt(DAYS_PER_YEAR)
view = btc.loc[s:e]

# 핵심 수치 카드
k1, k2, k3, k4 = st.columns(4)
period_ret = (view["close"].iloc[-1] / view["close"].iloc[0] - 1) * 100
max_dd = ((view["close"] / view["close"].cummax()) - 1).min() * 100
k1.metric("기간 수익률", f"{period_ret:+,.1f}%")
k2.metric("연율화 변동성", f"{view['ret'].std() * np.sqrt(DAYS_PER_YEAR):.1f}%")
k3.metric("기간 내 최대 낙폭", f"{max_dd:.1f}%")
k4.metric("이상치 후보", f"{int(view['is_outlier'].sum())}일 / {len(view)}일")

tab1, tab2, tab3, tab4 = st.tabs(["Q1 가격과 주기", "Q2 변동성", "Q3 나스닥·금리", "Q4 요일 효과"])

# ---------------------------------------------------------------
# Q1. 가격, 이동평균, 반감기
# ---------------------------------------------------------------
with tab1:
    log_scale = st.toggle("로그 스케일", value=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=view.index, y=view["close"], name="종가",
                             line=dict(color=BLUE, width=1.3),
                             hovertemplate="$%{y:,.0f}"))
    fig.add_trace(go.Scatter(x=view.index, y=view["ma"], name=f"{ma_window}일 이동평균",
                             line=dict(color=ORANGE, width=2.2),
                             hovertemplate="$%{y:,.0f}"))
    if show_outliers:
        o = view[view["is_outlier"]]
        fig.add_trace(go.Scatter(x=o.index, y=o["close"], mode="markers", name="이상치 후보",
                                 marker=dict(color=YELLOW, size=8, line=dict(color="white", width=1.5)),
                                 customdata=o["ret"], hovertemplate="%{customdata:+.1f}%"))
    for h in HALVINGS:
        if s <= h <= e:
            fig.add_vline(x=h, line_dash="dash", line_color=GRAY,
                          annotation_text=f"반감기 {h.date()}", annotation_position="top left")
    fig.update_yaxes(type="log" if log_scale else "linear", tickprefix="$", tickformat=",.0f",
                     tickvals=log_ticks(view["close"]) if log_scale else None)
    st.plotly_chart(base_layout(fig, 460), width="stretch")

    dd = (view["close"] / view["close"].cummax() - 1) * 100
    fig = go.Figure(go.Scatter(x=dd.index, y=dd, fill="tozeroy", name="고점 대비 하락률",
                               line=dict(color=BLUE, width=1.2), hovertemplate="%{y:.1f}%"))
    fig.update_yaxes(ticksuffix="%", range=[-100, 2])
    st.plotly_chart(base_layout(fig, 260, "선택 기간 내 최고가 대비 하락률"), width="stretch")

# ---------------------------------------------------------------
# Q2. 변동성
# ---------------------------------------------------------------
with tab2:
    fig = go.Figure(go.Scatter(x=view.index, y=view["vol"], name=f"{roll_window}일 롤링 변동성",
                               line=dict(color=BLUE, width=1.4), hovertemplate="%{y:.0f}%"))
    yearly_mean = view["vol"].groupby(view.index.year).transform("mean")
    fig.add_trace(go.Scatter(x=view.index, y=yearly_mean, name="연도별 평균",
                             line=dict(color=ORANGE, width=2.2), hovertemplate="%{y:.0f}%"))
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(base_layout(fig, 400, f"{roll_window}일 롤링 변동성 (연율화)"),
                    width="stretch")

    threshold = st.slider("하루 변동 기준 (±%)", 3, 15, 5)
    big = (view["ret"].abs() >= threshold).groupby(view.index.year).sum()
    fig = go.Figure(go.Bar(x=big.index.astype(str), y=big.values, marker_color=BLUE,
                           text=big.values, textposition="outside", hovertemplate="%{y}일"))
    st.plotly_chart(base_layout(fig, 300, f"하루에 ±{threshold}% 이상 움직인 날 수 (연도별)"),
                    width="stretch")

# ---------------------------------------------------------------
# Q3. 나스닥 상관계수, 금리 국면
# ---------------------------------------------------------------
with tab3:
    rets, _ = align_with_nasdaq(btc_all, nasdaq_all)
    rc = rets["btc"].rolling(roll_window).corr(rets["nasdaq"]).loc[s:e]
    fig = go.Figure(go.Scatter(x=rc.index, y=rc, name=f"{roll_window}거래일 롤링 상관계수",
                               line=dict(color=BLUE, width=1.4), hovertemplate="%{y:.2f}"))
    fig.add_hline(y=0, line_color=GRAY, line_width=1)
    fig.update_yaxes(range=[-0.6, 1])
    corr_view = rets.loc[s:e]
    st.plotly_chart(base_layout(fig, 340,
                    f"비트코인-나스닥 상관계수 (선택 기간 전체: {corr_view['btc'].corr(corr_view['nasdaq']):.2f})"),
                    width="stretch")
    st.caption("두 시장이 모두 거래한 날의 가격을 먼저 맞춘 뒤 수익률을 계산 (BTC 주말 움직임은 월요일 수익률에 포함)")

    # 가격과 금리는 y축을 겹치지 않고 위아래 패널로 나눈다
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35],
                        vertical_spacing=0.06)
    fig.add_trace(go.Scatter(x=view.index, y=view["close"], name="BTC 종가",
                             line=dict(color=BLUE, width=1.2), hovertemplate="$%{y:,.0f}"), row=1, col=1)
    rate = rate_all.loc[s:e]
    fig.add_trace(go.Scatter(x=rate.index, y=rate["fed_rate"], name="기준금리",
                             line=dict(color="#555", width=1.8, shape="hv"),
                             hovertemplate="%{y:.2f}%"), row=2, col=1)
    rows = []
    for rs, re_, name in RATE_REGIMES:
        a, b = max(pd.Timestamp(rs), s), min(pd.Timestamp(re_), e)
        if a >= b:
            continue
        fig.add_vrect(x0=a, x1=b, fillcolor=REGIME_COLOR[name], opacity=0.12, line_width=0,
                      row="all", col=1)
        # 국면 이름은 위 패널에만 한 번 표시
        fig.add_annotation(x=a + (b - a) / 2, y=1, xref="x", yref="y domain", text=name,
                           showarrow=False, yanchor="bottom", font=dict(size=10))
        p = btc_all["close"].loc[a:b]
        rr = rets.loc[a:b]
        rows.append({"국면": name, "기간": f"{a.date()} ~ {b.date()}",
                     "평균 금리(%)": rate_all["fed_rate"].loc[a:b].mean(),
                     "BTC 수익률(%)": (p.iloc[-1] / p.iloc[0] - 1) * 100,
                     "BTC 변동성(%)": btc_all["ret"].loc[a:b].std() * np.sqrt(DAYS_PER_YEAR),
                     "나스닥 상관": rr["btc"].corr(rr["nasdaq"]) if len(rr) > 2 else np.nan})
    fig.update_yaxes(type="log", tickprefix="$", tickformat=",.0f",
                     tickvals=log_ticks(view["close"]), title_text="BTC 종가", row=1, col=1)
    fig.update_yaxes(ticksuffix="%", rangemode="tozero", title_text="기준금리", row=2, col=1)
    fig.update_layout(showlegend=False)
    st.plotly_chart(base_layout(fig, 520, "비트코인 가격과 미국 기준금리 국면"), width="stretch")
    st.dataframe(pd.DataFrame(rows).round(2), hide_index=True, width="stretch")

# ---------------------------------------------------------------
# Q4. 요일 효과
# ---------------------------------------------------------------
with tab4:
    stat = st.radio("집계 방식", ["평균", "중앙값", "표준편차"], horizontal=True,
                    help="평균은 극단값에 끌려가므로 중앙값과 함께 보는 것을 권장")
    r = view["ret"].dropna()
    g = r.groupby(r.index.dayofweek)
    agg = {"평균": g.mean(), "중앙값": g.median(), "표준편차": g.std()}[stat]
    colors = [ORANGE if i >= 5 else BLUE for i in agg.index]
    fig = go.Figure(go.Bar(x=[WEEKDAYS[i] for i in agg.index], y=agg.values, marker_color=colors,
                           text=[f"{v:.2f}%" for v in agg.values], textposition="outside",
                           hovertemplate="%{y:.3f}%"))
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(base_layout(fig, 360, f"요일별 일간 수익률 {stat} (주황 = 주말, UTC 기준)"),
                    width="stretch")

    is_we = r.index.dayofweek >= 5
    yearly = pd.DataFrame({"평일": r[~is_we].groupby(r[~is_we].index.year).std(),
                           "주말": r[is_we].groupby(r[is_we].index.year).std()})
    fig = go.Figure([
        go.Bar(x=yearly.index.astype(str), y=yearly["평일"], name="평일", marker_color=BLUE,
               hovertemplate="%{y:.2f}%"),
        go.Bar(x=yearly.index.astype(str), y=yearly["주말"], name="주말", marker_color=ORANGE,
               hovertemplate="%{y:.2f}%"),
    ])
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
    fig.update_yaxes(ticksuffix="%")
    st.plotly_chart(base_layout(fig, 320, "연도별 일간 변동성: 평일 vs 주말"), width="stretch")
