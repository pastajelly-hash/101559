# ============================================================
# 전국 시군구 고령화율(65세 이상 인구 비율) 단계구분도
# Streamlit Cloud용 main.py
#
# 필요한 추가 라이브러리
#   geopandas
#
# requirements.txt에 아래 한 줄만 추가하면 됩니다.
# geopandas
# ============================================================

import pandas as pd
import geopandas as gpd
import streamlit as st
import plotly.express as px

# ------------------------------------------------------------
# 페이지 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="전국 시군구 고령화 지도",
    layout="wide"
)

st.title("🧓 전국 시군구 고령화 지도")
st.caption("최신 연도의 65세 이상 인구 비율(%)")

# ------------------------------------------------------------
# 데이터 주소
# ------------------------------------------------------------
POP_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/population_yearly.csv.gz"

GEO_URL = "https://raw.githubusercontent.com/greatsong/modudata/main/data/boundaries/sigungu_kr.geojson"


# ------------------------------------------------------------
# 인구 데이터 읽기
# ------------------------------------------------------------
@st.cache_data
def load_population():

    # 코드 열은 반드시 문자열로 읽는다.
    df = pd.read_csv(
        POP_URL,
        compression="gzip",
        dtype={"코드": str}
    )

    # 코드 앞 5자리가 시군구 코드
    df["시군구코드"] = df["코드"].str[:5]

    # 가장 최신 연도 찾기
    latest_year = df["연도"].max()

    df = df[df["연도"] == latest_year].copy()

    # --------------------------------------------------------
    # 65세 이상 인구 열 찾기
    # --------------------------------------------------------
    old_cols = []

    for age in range(65, 100):
        col = f"계_{age}세"
        if col in df.columns:
            old_cols.append(col)

    # 100세 이상
    if "계_100세 이상" in df.columns:
        old_cols.append("계_100세 이상")

    # 전체 인구 열 자동 찾기
    total_candidates = [
        "계",
        "총인구",
        "총인구수",
        "계_총인구"
    ]

    total_col = None

    for c in total_candidates:
        if c in df.columns:
            total_col = c
            break

    # 없으면 모든 계_나이 열을 합산
    if total_col is None:

        age_cols = []

        for c in df.columns:
            if c.startswith("계_"):
                age_cols.append(c)

        df["전체인구"] = df[age_cols].sum(axis=1)
        total_col = "전체인구"

    # 읍면동 → 시군구 집계
    agg = (
        df.groupby("시군구코드", as_index=False)
        .agg(
            전체인구=(total_col, "sum"),
            고령인구=(old_cols, lambda x: x.sum().sum())
        )
    )

    agg["고령화율"] = agg["고령인구"] / agg["전체인구"] * 100

    return agg, latest_year


# ------------------------------------------------------------
# 지도 읽기
# ------------------------------------------------------------
@st.cache_data
def load_map():

    gdf = gpd.read_file(GEO_URL)

    gdf["코드"] = gdf["코드"].astype(str)

    return gdf


# ------------------------------------------------------------
# 데이터 준비
# ------------------------------------------------------------
pop, latest_year = load_population()
gdf = load_map()

gdf = gdf.merge(
    pop,
    left_on="코드",
    right_on="시군구코드",
    how="left"
)

# ------------------------------------------------------------
# 단계 구분
# ------------------------------------------------------------
bins = [-1, 19, 23, 28, 38, 100]

labels = [
    "19% 미만",
    "19~23%",
    "23~28%",
    "28~38%",
    "38% 이상"
]

gdf["등급"] = pd.cut(
    gdf["고령화율"],
    bins=bins,
    labels=labels
)

# ------------------------------------------------------------
# Plotly 단계색 지도
# ------------------------------------------------------------
fig = px.choropleth(
    gdf,
    geojson=gdf.geometry.__geo_interface__,
    locations=gdf.index,
    color="등급",
    category_orders={"등급": labels},
    color_discrete_sequence=[
        "#f7fbff",
        "#c6dbef",
        "#6baed6",
        "#3182bd",
        "#08519c",
    ],
    hover_data={
        "시군구": True,
        "시도": True,
        "고령화율": ":.1f",
        "등급": False,
        "locations": False
    }
)

fig.update_geos(
    fitbounds="locations",
    visible=False,
    showcountries=False,
    showcoastlines=False,
    showland=False,
    showocean=False,
    showframe=False,
    bgcolor="rgba(0,0,0,0)"
)

fig.update_traces(
    marker_line_color="white",
    marker_line_width=0.6,
    hovertemplate=
    "<b>%{customdata[0]}</b><br>"
    "시도 : %{customdata[1]}<br>"
    "고령화율 : %{customdata[2]:.1f}%<extra></extra>"
)

fig.update_layout(
    title=f"{latest_year}년 전국 시군구 고령화율",
    height=850,
    margin=dict(l=0, r=0, t=50, b=0),
    legend_title="고령화율"
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------
# 상위/하위 10개
# ------------------------------------------------------------
table = (
    gdf[["시도", "시군구", "고령화율"]]
    .sort_values("고령화율")
    .copy()
)

table["고령화율"] = table["고령화율"].round(1)

low10 = table.head(10).reset_index(drop=True)
high10 = table.tail(10).sort_values(
    "고령화율",
    ascending=False
).reset_index(drop=True)

st.markdown("---")

c1, c2 = st.columns(2)

with c1:
    st.subheader("고령화율 낮은 시군구 10곳")
    st.dataframe(
        low10,
        use_container_width=True,
        hide_index=True
    )

with c2:
    st.subheader("고령화율 높은 시군구 10곳")
    st.dataframe(
        high10,
        use_container_width=True,
        hide_index=True
    )
