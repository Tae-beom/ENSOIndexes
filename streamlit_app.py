# -*- coding: utf-8 -*-
"""
실제 데이터 비교 (멀티지수: ONI / SOI / OLR)
- 드롭다운으로 지수 선택 → 동일한 Plotly + JS 슬라이더/점선/결과 패널 동작
- 임계값: ONI(±0.5), SOI(±0.7), OLR(임시 ±1.0; 파일 형식 확정 시 조정)
- 파일 예상 위치:
  - ONI: data/elnino_data.csv (컬럼: YR, MON, DATA)
  - SOI: data/soi_data.csv (또는 업로드 파일) (컬럼 예: Date, SOI)
  - OLR: data/olr_data.csv (파일 스키마 확정 필요)
"""

import json
import os
import pandas as pd
import streamlit as st
from utils import inject_css

# ─────────────────────────────────────────────────────────────
# 0) 공통 스타일 (왼쪽 정렬 & 본문 폭)
# ─────────────────────────────────────────────────────────────
inject_css(max_width_px=1200)
st.header("📈 실제 데이터 비교")

# ─────────────────────────────────────────────────────────────
# 1) 지수 선택 (시뮬레이션 페이지처럼 드롭다운)
# ─────────────────────────────────────────────────────────────
index_name = st.selectbox("지수 선택", ["ONI 지수", "SOI 지수", "OLR 지수"], index=0)

# ─────────────────────────────────────────────────────────────
# 2) 데이터 로더: 지수별 스키마 차이를 흡수하여 공통 형태로 반환
#    반환 df 컬럼: YearMonth(datetime64), VALUE(float), 상태(str), 색(str)
#    + 메타정보(title, yaxis_label, thresholds)
# ─────────────────────────────────────────────────────────────
def load_index(index_name: str):
    if index_name == "ONI 지수":
        # 파일 경로
        path = "data/elnino_data.csv"
        if not os.path.exists(path):
            st.error("ONI 파일이 없습니다: data/elnino_data.csv")
            st.stop()

        df = pd.read_csv(path)
        # 필수 컬럼 점검
        req = {"YR", "MON", "DATA"}
        if missing := (req - set(df.columns)):
            st.error(f"ONI 파일에 필요한 컬럼이 없습니다: {', '.join(missing)}")
            st.stop()

        df = df.dropna(subset=["DATA"]).copy()
        df["YR"] = pd.to_numeric(df["YR"], errors="coerce")
        df["MON"] = pd.to_numeric(df["MON"], errors="coerce")
        df = df.dropna(subset=["YR", "MON"]).copy()

        df["YearMonth"] = pd.to_datetime(
            df["YR"].astype(int).astype(str) + "-" + df["MON"].astype(int).astype(str),
            errors="coerce"
        )
        df = df.dropna(subset=["YearMonth"]).sort_values("YearMonth").reset_index(drop=True)
        df["VALUE"] = df["DATA"].astype(float)

        # 임계값: ±0.5°C
        thr_pos, thr_neg = 0.5, -0.5

        def classify(v):
            if v >= thr_pos:  # 따뜻함 → 엘니뇨
                return "엘니뇨", "red"
            elif v <= thr_neg:  # 차가움 → 라니냐
                return "라니냐", "blue"
            else:
                return "중립", "black"

        df["상태"], df["색"] = zip(*df["VALUE"].apply(classify))
        meta = dict(title="ONI (SST anomalies)", yaxis_label="SST anomalies (°C)",
                    thr_pos=thr_pos, thr_neg=thr_neg)
        return df, meta

    if index_name == "SOI 지수":
        # 파일 경로 우선순위: 프로젝트 내 → 업로드 경로(학습 세션)
        path_candidates = ["data/soi_data.csv", "/mnt/data/soi_data.csv"]
        path = next((p for p in path_candidates if os.path.exists(p)), None)
        if not path:
            st.error("SOI 파일이 없습니다. data/soi_data.csv 위치에 두거나 업로드 해주세요.")
            st.stop()

        df = pd.read_csv(path)
        # 컬럼명 트림
        df.columns = [c.strip() for c in df.columns]
        # 가능한 이름들: Date, SOI
        # Date 파싱
        date_col = next((c for c in df.columns if c.lower() == "date"), None)
        val_col  = next((c for c in df.columns if c.lower() in ["soi", "data", "value"]), None)
        if not date_col or not val_col:
            st.error(f"SOI 파일 컬럼을 인식할 수 없습니다. 발견된 컬럼: {list(df.columns)}")
            st.stop()

        df = df.dropna(subset=[date_col, val_col]).copy()
        df["YearMonth"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=["YearMonth"]).sort_values("YearMonth").reset_index(drop=True)
        df["VALUE"] = pd.to_numeric(df[val_col], errors="coerce")
        df = df.dropna(subset=["VALUE"]).copy()

        # 임계값: 사용자 지정 **±0.7**
        thr_pos, thr_neg = 0.7, -0.7

        def classify(v):
            # SOI는 일반적으로 (음수 → 엘니뇨, 양수 → 라니냐)
            if v <= thr_neg:
                return "엘니뇨", "red"
            elif v >= thr_pos:
                return "라니냐", "blue"
            else:
                return "중립", "black"

        df["상태"], df["색"] = zip(*df["VALUE"].apply(classify))
        meta = dict(title="SOI", yaxis_label="SOI (standardized)",  # 라벨은 필요시 조정
                    thr_pos=thr_pos, thr_neg=thr_neg)
        return df, meta

    if index_name == "OLR 지수":
        path = "data/olr_data.csv"
        if not os.path.exists(path):
            st.warning("OLR 파일이 아직 없습니다. data/olr_data.csv를 추가하면 자동으로 표시됩니다.")
            # 빈 예시 프레임 (표시만 막고 종료)
            st.stop()

        df = pd.read_csv(path)
        df.columns = [c.strip() for c in df.columns]
        # 가능한 이름들 추정: Date, OLR or DATA
        date_col = next((c for c in df.columns if c.lower() == "date"), None)
        val_col  = next((c for c in df.columns if c.lower() in ["olr", "data", "value"]), None)
        if not date_col or not val_col:
            st.error(f"OLR 파일 컬럼을 인식할 수 없습니다. 발견된 컬럼: {list(df.columns)}")
            st.stop()

        df = df.dropna(subset=[date_col, val_col]).copy()
        df["YearMonth"] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=["YearMonth"]).sort_values("YearMonth").reset_index(drop=True)
        df["VALUE"] = pd.to_numeric(df[val_col], errors="coerce")
        df = df.dropna(subset=["VALUE"]).copy()

        # 임시 임계값(파일 정의 확인 전): ±1.0
        thr_pos, thr_neg = 1.0, -1.0

        def classify(v):
            # OLR 해석은 지수 정의에 따라 다릅니다. 일단 절댓값 기준 중립/비중립만 표시.
            if v >= thr_pos:
                return "양의 편차", "red"
            elif v <= thr_neg:
                return "음의 편차", "blue"
            else:
                return "중립", "black"

        df["상태"], df["색"] = zip(*df["VALUE"].apply(classify))
        meta = dict(title="OLR (임시 기준)", yaxis_label="OLR anomaly (?)",
                    thr_pos=thr_pos, thr_neg=thr_neg)
        return df, meta

    # 예외
    st.error("알 수 없는 지수 선택입니다.")
    st.stop()


# ─────────────────────────────────────────────────────────────
# 3) 데이터 로드
# ─────────────────────────────────────────────────────────────
df, meta = load_index(index_name)

# y축 범위(여유 0.2)
ymin = float(df["VALUE"].min()) - 0.2
ymax = float(df["VALUE"].max()) + 0.2

# 5년 간격 x축 틱 (매년 1월 기준)
df["YR"] = df["YearMonth"].dt.year
df["MON"] = df["YearMonth"].dt.month
ticks = df[(df["MON"] == 1) & (df["YR"] % 5 == 0)]["YearMonth"]
tick_dates = ticks.dt.strftime("%Y-%m-%d").tolist()
tick_texts = [str(d.year) for d in ticks]

# JS로 넘길 데이터 (json.dumps로 안전 직렬화)
dates_js = json.dumps(df["YearMonth"].dt.strftime("%Y-%m-%d").tolist(), ensure_ascii=False)
vals_js  = json.dumps(df["VALUE"].round(3).astype(float).tolist(), ensure_ascii=False)
state_js = json.dumps(df["상태"].tolist(), ensure_ascii=False)
color_js = json.dumps(df["색"].tolist(), ensure_ascii=False)
tick_dates_js = json.dumps(tick_dates, ensure_ascii=False)
tick_texts_js = json.dumps(tick_texts, ensure_ascii=False)

init_idx = len(df) - 1
init_date = df["YearMonth"].iloc[init_idx].strftime("%Y-%m-%d")

# ─────────────────────────────────────────────────────────────
# 4) HTML/JS: Plotly + 슬라이더(플롯 폭/좌표에 정확히 정렬)
# ─────────────────────────────────────────────────────────────
W = 1100  # 전체 컨테이너 가로폭 (필요 시 조절)

yaxis_label = meta["yaxis_label"]
title_label = meta["title"]  # 좌측 정보 문구에 사용

html = f"""
<div id="chartWrap" style="width:{W}px; margin:0; position:relative;"> <!-- margin:0 → 왼쪽 정렬 -->
  <!-- 차트 -->
  <div id="chart" style="width:{W}px; height:440px;"></div>

  <!-- 슬라이더 (그래프 바로 아래) -->
  <div id="sliderWrap" style="position:relative; height:56px; margin-top:0;">
    <input type="range" id="monthSlider" min="0" max="{len(df)-1}" value="{init_idx}"
      style="position:absolute; width:897px; left:50px;">
  </div>

  <!-- 결과 패널 -->
  <div id="info" style="text-align:left; font-size:18px; margin-top:8px;"></div>
</div>

<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<script>
  // 데이터
  const dates  = {dates_js};
  const vals   = {vals_js};
  const states = {state_js};
  const colors = {color_js};

  const tickDates = {tick_dates_js};
  const tickTexts = {tick_texts_js};
  const yMin = {ymin};
  const yMax = {ymax};

  // 라인
  const lineTrace = {{
    x: dates,
    y: vals,
    mode: 'lines',
    name: '{title_label}',
    line: {{color: 'dodgerblue', width: 2}}
  }};

  // 선택 시점 세로 점선
  const vlineTrace = {{
    x: ['{init_date}', '{init_date}'],
    y: [yMin, yMax],
    mode: 'lines',
    line: {{color: 'red', dash: 'dot', width: 2}},
    hoverinfo: 'skip',
    showlegend: false
  }};

  // 레이아웃
  const layout = {{
    margin: {{l: 60, r: 60, t: 10, b: 60}},
    height: 440,
    xaxis: {{
      title: 'Year',
      tickmode: 'array',
      tickvals: tickDates,
      ticktext: tickTexts
    }},
    yaxis: {{
      title: '{yaxis_label}',
      range: [yMin, yMax]
    }},
    template: 'simple_white',
    shapes: [
      // y=0 기준선
      {{
        type: 'line', xref: 'paper', x0: 0, x1: 1,
        yref: 'y', y0: 0, y1: 0,
        line: {{color: 'gray', width: 1, dash: 'dot'}}
      }}
    ]
  }};

  // 차트
  Plotly.newPlot('chart', [lineTrace, vlineTrace], layout, {{responsive:true}}).then(() => {{
    syncSliderToPlot();
    document.getElementById('chart').on('plotly_relayout', syncSliderToPlot);
    window.addEventListener('resize', syncSliderToPlot);
  }});

  const slider = document.getElementById('monthSlider');
  const info   = document.getElementById('info');

  // 결과 갱신
  function update(idx) {{
    const date  = dates[idx];
    const val   = vals[idx];
    const state = states[idx];
    const color = colors[idx];

    // 점선 이동
    Plotly.restyle('chart', {{ x: [[date, date]], y: [[yMin, yMax]] }}, [1]);

    const valStr = (val >= 0 ? '+' : '') + Number(val).toFixed(2);
    const [year, month] = date.split('-');

    info.innerHTML = "📅 " + year + "년 " + String(parseInt(month)) + "월 "
                   + "{title_label}: "
                   + "<span style='color:" + color + "'><b>" + valStr + "</b></span> ⇒ "
                   + state;
  }}

  // 슬라이더를 플롯(bg) 크기/위치에 정확히 맞추기
  function syncSliderToPlot() {{
    const chart   = document.getElementById('chart');
    const host    = document.getElementById('sliderWrap');
    const bg = chart.querySelector('.cartesianlayer .bg');
    if (!bg) return;

    const bbox    = bg.getBoundingClientRect();
    const hostBox = host.getBoundingClientRect();

    slider.style.width = (bbox.width) + 'px';
    slider.style.left  = (bbox.left - hostBox.left) + 'px';
    slider.style.top   = (bbox.bottom - hostBox.top + 10) + 'px';
  }}

  slider.addEventListener('input', e => update(+e.target.value));
  update({init_idx});
</script>
"""

st.components.v1.html(html, width=1200, height=800)
