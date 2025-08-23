import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(page_title="SST Index Viewer", layout="wide")

# -----------------------------
# 1) 데이터 로드 & 전처리
# -----------------------------
df = pd.read_csv("data/elnino_data.csv")
df = df.dropna(subset=["DATA"]).copy()

df["YearMonth"] = pd.to_datetime(df["YR"].astype(str) + "-" + df["MON"].astype(str))
df["Label"] = df["YR"].astype(str) + "년 " + df["MON"].astype(str) + "월"

def classify_sst(v):
    if v >= 0.5:
        return "엘니뇨", "red"
    elif v <= -0.5:
        return "라니냐", "blue"
    else:
        return "중립", "black"

df["상태"], df["색"] = zip(*df["DATA"].apply(classify_sst))

# y축 범위
ymin = float(df["DATA"].min()) - 0.2
ymax = float(df["DATA"].max()) + 0.2

# 5년 간격 x축 눈금
ticks = df[(df["MON"] == 1) & (df["YR"] % 5 == 0)]["YearMonth"]
tick_dates = ticks.dt.strftime("%Y-%m-%d").tolist()
tick_texts = [str(d.year) for d in ticks]

# JS로 넘길 배열
dates_js = df["YearMonth"].dt.strftime("%Y-%m-%d").tolist()
sst_js    = df["DATA"].round(2).astype(float).tolist()
state_js  = df["상태"].tolist()
color_js  = df["색"].tolist()

init_idx  = len(df) - 1
init_date = dates_js[init_idx]

st.title("📊 El nino 지수")

# 차트 래퍼/폭 (오른쪽 잘림 방지 위해 넓힘)
W = 1120   # ← 필요하면 여기 수치만 바꿔서 전체 가로폭 조절

html = f"""
<div id="chartWrap" style="width:{W}px; margin:0 auto; position:relative;">
  <!-- 차트 -->
  <div id="chart" style="width:{W}px; height:440px;"></div>

  <!-- 슬라이더(그래프 바로 아래, 플롯영역과 정확히 길이/위치 맞춤) -->
  <div id="sliderWrap" style="position:relative; height:56px; margin-top:0;">
    <input type="range" id="monthSlider" min="0" max="{len(df)-1}" value="{init_idx}"
      style="width:920px; margin-left:50px;">
  </div>

  <!-- 결과 문구: 좌측 정렬 -->
  <div id="info" style="text-align:left; font-size:18px; margin-top:8px;"></div>
</div>

<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<script>
  // 데이터
  const dates  = {dates_js};
  const ssts   = {sst_js};
  const states = {state_js};
  const colors = {color_js};

  const tickDates = {tick_dates};
  const tickTexts = {tick_texts};
  const yMin = {ymin};
  const yMax = {ymax};

  // 트레이스
  const lineTrace = {{
    x: dates,
    y: ssts,
    mode: 'lines',
    name: 'SST anomalies',
    line: {{color: 'dodgerblue', width: 2}}
  }};

  const vlineTrace = {{
    x: ['{init_date}', '{init_date}'],
    y: [yMin, yMax],
    mode: 'lines',
    line: {{color: 'red', dash: 'dot', width: 2}},
    hoverinfo: 'skip',
    showlegend: false
  }};

  // 레이아웃 (오른쪽 잘림 방지: r 마진 확대)
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
      title: 'SST anomalies',
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

  // 차트 생성 (반응형)
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
    const sst   = ssts[idx];
    const state = states[idx];
    const color = colors[idx];

    // 점선 위치 즉시 갱신 (두번째 트레이스)
    Plotly.restyle('chart', {{ x: [[date, date]], y: [[yMin, yMax]] }}, [1]);

    const sstStr = (sst >= 0 ? '+' : '') + sst.toFixed(2) + '°C';
    const year   = date.slice(0,4);

    let stateText = '';
    if (state === '엘니뇨') {{
      stateText = "<span style='color:red'><b>엘니뇨 시기</b></span>";
    }} else if (state === '라니냐') {{
      stateText = "<span style='color:blue'><b>라니냐 시기</b></span>";
    }} else {{
      stateText = "<span style='color:black'><b>중립 시기</b></span>";
    }}

    info.innerHTML = "📅 " + year + "년 동태평양 표층 수온 편차: "
                   + "<span style='color:" + color + "'><b>" + sstStr + "</b></span> ⇒ "
                   + stateText;
  }}

  // 슬라이더를 플롯(bg) 크기/위치에 정확히 맞추기
  function syncSliderToPlot() {{
    const chart   = document.getElementById('chart');
    const slider  = document.getElementById('monthSlider');
    const host    = document.getElementById('sliderWrap');

    // 플롯 영역 사각형
    const bg = chart.querySelector('.cartesianlayer .bg');
    if (!bg) return;

    const bbox    = bg.getBoundingClientRect();
    const hostBox = host.getBoundingClientRect();

    // 길이 = 플롯 폭, 위치 = 플롯 좌측/하단 기준
    slider.style.width = (bbox.width) + 'px';
    slider.style.left  = (bbox.left - hostBox.left) + 'px';
    slider.style.top   = (bbox.bottom - hostBox.top + 10) + 'px';
  }}

  // 초기 상태 반영 & 드래그 실시간 갱신
  slider.addEventListener('input', e => update(+e.target.value));
  update({init_idx});
</script>
"""

components.html(html, height=760)
