import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
from plotly.utils import PlotlyJSONEncoder
import streamlit.components.v1 as components

st.set_page_config(page_title="SST Index Viewer", layout="centered")

# 1) 데이터 로드 & 전처리
df = pd.read_csv("data/elnino_data.csv")
# NaN 값 제거 (첫 행 NaN 등)
df = df.dropna(subset=["DATA"]).copy()

# 연-월(datetime) 생성
df["YearMonth"] = pd.to_datetime(df["YR"].astype(str) + "-" + df["MON"].astype(str))
# 표시용 텍스트
df["Label"] = df["YR"].astype(str) + "년 " + df["MON"].astype(str) + "월"

# 상태 분류
def classify_sst(val):
    if val >= 0.5:
        return "엘니뇨", "red"
    elif val <= -0.5:
        return "라니냐", "blue"
    else:
        return "중립", "black"

df["상태"], df["색"] = zip(*df["DATA"].apply(classify_sst))

# y 범위(약간의 여유)
ymin = float(df["DATA"].min()) - 0.2
ymax = float(df["DATA"].max()) + 0.2

# 5년 간격 x축 눈금 (1월인 지점 중 5년 간격)
year_ticks = df[(df["MON"] == 1) & (df["YR"] % 5 == 0)]["YearMonth"]
year_tick_text = [str(x.year) for x in year_ticks]

# 2) Plotly Figure 구성
fig = go.Figure()

# (a) SST 라인
fig.add_trace(go.Scatter(
    x=df["YearMonth"],
    y=df["DATA"],
    mode="lines",
    name="SST Index",
    line=dict(color="dodgerblue")
))

# (b) 선택 점선(처음엔 마지막 지점에 수직선)
init_idx = len(df) - 1
init_date = df["YearMonth"].iloc[init_idx]
fig.add_trace(go.Scatter(
    x=[init_date, init_date],
    y=[ymin, ymax],
    mode="lines",
    name="Selected",
    line=dict(color="red", dash="dot", width=2),
    hoverinfo="skip",
    showlegend=False
))

# (c) y=0 기준선
fig.add_hline(y=0, line_dash="dot", line_color="gray")

fig.update_layout(
    height=420,
    margin=dict(l=40, r=40, t=30, b=40),
    xaxis=dict(
        title="Year",
        tickmode="array",
        tickvals=year_ticks,
        ticktext=year_tick_text
    ),
    yaxis=dict(
        title="SST Index",
        range=[ymin, ymax]
    ),
    template="simple_white"
)

fig_json = json.dumps(fig, cls=PlotlyJSONEncoder)

# 3) JS로 전달할 데이터(문자열화)
dates_js = df["YearMonth"].dt.strftime("%Y-%m-%d").tolist()
sst_js = df["DATA"].round(2).tolist()
state_js = df["상태"].tolist()
color_js = df["색"].tolist()

# 4) HTML + JS (슬라이더 oninput 시 즉시 업데이트)
html_code = f"""
<div style="width:720px; margin: 0 auto;">
  <div id="chart" style="width:700px; height:420px; margin: 0 auto;"></div>

  <!-- 슬라이더: 그래프와 폭을 맞춤 -->
  <div style="width:700px; margin: 18px auto 6px auto; text-align:center;">
    <input type="range" id="monthSlider" min="0" max="{len(df)-1}" value="{init_idx}" style="width:700px;">
  </div>

  <!-- 상태 표시 -->
  <div id="info" style="text-align:center; font-size:18px; margin-top:8px;"></div>
</div>

<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<script>
  // Python에서 전달한 그래프와 데이터
  const fig = {fig_json};
  const dates = {json.dumps(dates_js)};
  const ssts = {json.dumps(sst_js)};
  const states = {json.dumps(state_js)};
  const colors = {json.dumps(color_js)};
  const yMin = {ymin};
  const yMax = {ymax};

  // 그래프 렌더링
  Plotly.newPlot('chart', fig.data, fig.layout);

  const slider = document.getElementById('monthSlider');
  const info = document.getElementById('info');

  function update(idx) {{
    const date = dates[idx];
    const sst = ssts[idx];
    const state = states[idx];
    const color = colors[idx];

    // 선택 수직선(두번째 트레이스 index=1)의 x, y 업데이트
    Plotly.restyle('chart', {{
      x: [[date, date]],
      y: [[yMin, yMax]]
    }}, [1]);

    const sstStr = (sst >= 0 ? "+" : "") + sst.toFixed(2) + "°C";
    const year = date.slice(0,4);

    let stateText = "";
    if (state === "엘니뇨") {{
      stateText = "<span style='color:red'><b>엘니뇨 시기</b></span>";
    }} else if (state === "라니냐") {{
      stateText = "<span style='color:blue'><b>라니냐 시기</b></span>";
    }} else {{
      stateText = "<span style='color:black'><b>중립 시기</b></span>";
    }}

    info.innerHTML = `
      <span>📅 ${{year}}년 동태평양 표층 수온 편차:
        <span style="color:${{color}}"><b>${{sstStr}}</b></span>,
        ${{stateText}}
      </span>`;
  }}

  // 초기 상태 반영
  update({init_idx});

  // 드래그 중 실시간 반영
  slider.addEventListener('input', (e) => {{
    update(e.target.value);
  }});
</script>
"""

st.title("📊 SST 지수 — 슬라이더 실시간 시각화")
components.html(html_code, height=560)
