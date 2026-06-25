from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.charts import (
    PALETTE,
    ai_market_scatter,
    career_transition_sankey,
    category_market,
    category_projection_chart,
    category_sector_mix,
    city_category_sankey,
    city_map,
    cluster_scatter,
    employment_evolution,
    employment_forecast_chart,
    polish,
    skill_network,
    task_metric_heatmap,
    task_metric_scatter,
    threshold_chart,
)
from src.config import describe_runtime, get_database_path
from src.database import TABLES, read_table, table_count


ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="生成式AI背景下职业演化与就业结构变化",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="auto",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #13201d;
        --muted: #65736f;
        --teal: #0f766e;
        --cyan: #2b8a9f;
        --gold: #d8a72f;
        --rust: #c06b4e;
        --line: #d9e3df;
        --panel: #ffffff;
        --paper: #f5f7f4;
        --sidebar: #111c19;
    }
    .stApp {
        background:
            linear-gradient(90deg, rgba(15,118,110,0.035) 1px, transparent 1px),
            linear-gradient(180deg, rgba(15,118,110,0.035) 1px, transparent 1px),
            var(--paper);
        background-size: 42px 42px;
    }
    [data-testid="stAppViewContainer"] > .main .block-container {
        padding-top: 2.1rem;
        max-width: 1180px;
    }
    [data-testid="stSidebar"] {
        background:
            linear-gradient(180deg, #111c19 0%, #162622 58%, #101917 100%);
        border-right: 1px solid #2c403b;
        box-shadow: 8px 0 24px rgba(19, 32, 29, 0.08);
    }
    [data-testid="stSidebar"] * { color: #edf3f1; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2 {
        font-size: 1.16rem;
        line-height: 1.25;
        margin: 0.25rem 0 0.3rem;
        letter-spacing: 0;
    }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #a9b7b3;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 0.48rem;
        margin-top: 0.45rem;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        min-height: 3.05rem;
        padding: 0.7rem 0.78rem 0.7rem 0.92rem;
        background: rgba(255,255,255,0.055);
        border: 1px solid rgba(144,161,155,0.26);
        border-left: 4px solid #4e6760;
        border-radius: 8px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
        transition: background 160ms ease, border-color 160ms ease, transform 160ms ease, box-shadow 160ms ease;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.085);
        border-color: rgba(139,211,199,0.46);
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background: #f5fbf8;
        border-color: #d8a72f;
        border-left-color: #d8a72f;
        box-shadow: 0 10px 22px rgba(0,0,0,0.16);
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) * {
        color: #17211f !important;
        font-weight: 700;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 0.91rem;
        line-height: 1.25;
    }
    .sidebar-stage {
        margin: 0.95rem 0 0.35rem;
        padding: 0.74rem 0.78rem;
        border: 1px solid rgba(144,161,155,0.28);
        border-radius: 8px;
        background: rgba(0,0,0,0.18);
        color: #cbd8d4;
        font-size: 0.82rem;
        line-height: 1.45;
    }
    .sidebar-stage strong {
        color: #e9b949;
        display: block;
        margin-bottom: 0.18rem;
    }
    .brand {
        position: relative;
        padding: 1.05rem 1.15rem 1.12rem;
        border: 1px solid var(--line);
        border-left: 5px solid var(--teal);
        border-radius: 8px;
        margin-bottom: 1.05rem;
        background: rgba(255,255,255,0.88);
        box-shadow: 0 12px 32px rgba(19, 32, 29, 0.08);
    }
    .brand:after {
        content: "";
        position: absolute;
        right: 1.1rem;
        top: 1rem;
        width: 132px;
        height: 8px;
        border-top: 2px solid rgba(15,118,110,0.22);
        border-bottom: 2px solid rgba(216,167,47,0.35);
    }
    .brand h1 { font-size: 2.1rem; line-height: 1.12; letter-spacing: 0; margin: 0; color: var(--ink); max-width: 780px; }
    .brand p { color: var(--muted); margin: 0.55rem 0 0; font-size: 0.98rem; max-width: 840px; }
    .section-kicker {
        color: var(--teal);
        font-size: 0.76rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.34rem;
    }
    .insight {
        border-left: 4px solid var(--gold);
        padding: 0.86rem 1rem;
        background: #fff8e6;
        color: #4b4431;
        margin: 0.55rem 0 1rem;
        border-radius: 0 8px 8px 0;
        box-shadow: 0 8px 20px rgba(120, 89, 22, 0.07);
    }
    [data-testid="stMetric"] {
        background: var(--panel);
        border: 1px solid var(--line);
        border-top: 3px solid rgba(15,118,110,0.45);
        border-radius: 8px;
        padding: 0.92rem 1rem;
        box-shadow: 0 8px 22px rgba(19, 32, 29, 0.06);
    }
    [data-testid="stMetricLabel"] p { color: #43524e; font-weight: 650; }
    [data-testid="stMetricValue"] { font-size: 1.72rem; color: var(--ink); }
    [data-testid="stMetricDelta"] { font-size: 0.78rem; }
    div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 8px; overflow: hidden; box-shadow: 0 8px 22px rgba(19,32,29,0.045); }
    div[data-testid="stPlotlyChart"] {
        background: rgba(255,255,255,0.82);
        border: 1px solid rgba(217,227,223,0.88);
        border-radius: 8px;
        padding: 0.45rem;
        box-shadow: 0 10px 26px rgba(19,32,29,0.055);
    }
    div[data-testid="stTabs"] button p {
        font-weight: 650;
        color: #4c5c57;
    }
    div[data-testid="stTabs"] button[aria-selected="true"] p {
        color: var(--teal);
    }
    .stMultiSelect [data-baseweb="select"] > div {
        border-radius: 8px;
        border-color: var(--line);
        background: rgba(255,255,255,0.94);
    }
    .runtime { color: #a9b7b3; font-size: 0.72rem; overflow-wrap: anywhere; margin-top: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def ensure_database() -> None:
    path = get_database_path()
    try:
        ready = (
            path.exists()
            and table_count(path, "category_stats") > 0
            and table_count(path, "employment_forecast") > 0
            and table_count(path, "occupation_task_metrics") > 0
        )
    except (sqlite3.DatabaseError, ValueError):
        ready = False
    if not ready:
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "init_database.py"), "--path", str(path)],
            check=True,
        )


@st.cache_data(show_spinner=False)
def load_data() -> dict[str, pd.DataFrame]:
    return {table: read_table(table) for table in sorted(TABLES)}


def page_header(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="brand">
            <div class="section-kicker">{kicker}</div>
            <h1>{title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metadata_map(data: dict[str, pd.DataFrame]) -> dict[str, str]:
    return dict(data["metadata"][["key", "value"]].itertuples(index=False, name=None))


def show_evolution(data: dict[str, pd.DataFrame]) -> None:
    page_header(
        "LONGITUDINAL EVIDENCE",
        "中国就业结构真实演化",
        "基于世界银行开放数据中的 ILO 模型估计，观察 1991—2025 年三次产业就业占比变化。",
    )
    history = data["employment_history"]
    latest_year = int(history["year"].max())
    selected = history[history["year"].isin([2000, 2022, latest_year])]
    pivot = selected.pivot(index="year", columns="sector", values="employment_share")
    columns = st.columns(4)
    columns[0].metric("真实时间跨度", f"{len(history['year'].unique())} 年", f"{int(history['year'].min())}—{latest_year}")
    for index, sector in enumerate(["第一产业", "第二产业", "第三产业"], start=1):
        latest = float(pivot.loc[latest_year, sector])
        delta = latest - float(pivot.loc[2000, sector])
        columns[index].metric(f"{sector}就业占比", f"{latest:.2f}%", f"2000年以来 {delta:+.2f}点")

    st.plotly_chart(employment_evolution(history), use_container_width=True, key="evolution_history")
    st.markdown(
        '<div class="insight"><strong>如何理解“生成式AI背景”：</strong> 2022年后的数据用于描述生成式AI扩散期所处的就业结构环境，'
        "但产业占比变化同时受经济周期、人口、政策与技术进步影响，图表不把同期变化直接解释为AI的单一因果效应。</div>",
        unsafe_allow_html=True,
    )
    st.plotly_chart(category_sector_mix(data["category_sector"]), use_container_width=True, key="evolution_sector_mix")
    st.caption(
        "上图把当前真实招聘样本的行业标签映射到三次产业，用于连接长期产业演化与当前职业结构；它不是历史职业数量序列。"
    )


def show_forecast(data: dict[str, pd.DataFrame], selected_categories: list[str]) -> None:
    page_header(
        "FORECAST & SCENARIO",
        "就业结构趋势预测与职业情景",
        "用真实年度序列进行滚动回测和2026—2030年外推，再把产业趋势映射到当前职业类别。",
    )
    forecast = data["employment_forecast"]
    projected = forecast[forecast["status"] == "预测"]
    forecast_2030 = projected[projected["year"] == 2030].set_index("sector")
    columns = st.columns(4)
    for index, sector in enumerate(["第一产业", "第二产业", "第三产业"]):
        row = forecast_2030.loc[sector]
        columns[index].metric(f"2030年{sector}", f"{row['share']:.2f}%", f"回测MAE {row['backtest_mae']:.2f}点")
    columns[3].metric("预测期限", "5 年", "2026—2030 · 95%区间")
    st.plotly_chart(employment_forecast_chart(forecast), use_container_width=True, key="forecast_sector_trend")

    available = [category for category in selected_categories if category != "其他职业"]
    default = [category for category in ["AI与算法", "软件开发", "数据分析", "制造工程"] if category in available]
    chosen = st.multiselect(
        "选择职业类别查看产业结构情景",
        available,
        default=default or available[:4],
        max_selections=6,
    )
    if chosen:
        scenario = data["category_projection"]
        scenario = scenario[scenario["category"].isin(chosen)]
        st.plotly_chart(category_projection_chart(scenario), use_container_width=True, key="forecast_category_projection")
        comparison = (
            scenario[scenario["year"] == 2030]
            .merge(
                data["category_stats"][["category", "ai_share", "median_salary"]],
                on="category",
                how="left",
            )
            .sort_values("demand_index", ascending=False)
            .rename(
                columns={
                    "category": "职业类别",
                    "demand_index": "2030结构情景指数",
                    "dominant_sector": "当前主要产业",
                    "ai_share": "当前AI关联岗位占比/%",
                    "median_salary": "当前月薪中位数/K",
                }
            )
        )
        st.dataframe(
            comparison[
                ["职业类别", "2030结构情景指数", "当前主要产业", "当前AI关联岗位占比/%", "当前月薪中位数/K"]
            ],
            hide_index=True,
            use_container_width=True,
        )

    st.markdown(
        '<div class="insight"><strong>预测边界：</strong> 虚线是最近12年线性趋势外推，阴影为滚动回测残差形成的95%区间。'
        "职业指数只表示其当前产业构成在该情景下的结构环境（2025=100），不是岗位数量、失业率或AI替代概率预测。</div>",
        unsafe_allow_html=True,
    )


def show_task_metrics(
    data: dict[str, pd.DataFrame], selected_categories: list[str], with_header: bool = True
) -> None:
    if with_header:
        page_header(
            "TASK PROXY MODEL",
            "职业任务结构与AI暴露度",
            "从职位名称、关键词和行业文本构造重复性、创造性、数字化强度、人际互动与AI任务暴露代理指标。",
        )
    metrics = data["occupation_task_metrics"]
    metrics = metrics[metrics["category"].isin(selected_categories)].copy()
    highest_exposure = metrics.loc[metrics["ai_exposure"].idxmax()]
    highest_creativity = metrics.loc[metrics["creativity"].idxmax()]
    highest_routine = metrics.loc[metrics["repetitiveness"].idxmax()]
    columns = st.columns(4)
    columns[0].metric("指标维度", "5 项", "岗位文本相对指数")
    columns[1].metric("AI暴露", f"{highest_exposure['ai_exposure']:.1f}", highest_exposure["category"])
    columns[2].metric("创造性", f"{highest_creativity['creativity']:.1f}", highest_creativity["category"])
    columns[3].metric("重复性", f"{highest_routine['repetitiveness']:.1f}", highest_routine["category"])
    st.plotly_chart(task_metric_scatter(metrics), use_container_width=True, key="task_metric_scatter")
    st.plotly_chart(task_metric_heatmap(metrics), use_container_width=True, key="task_metric_heatmap")
    st.markdown(
        '<div class="insight"><strong>指标口径：</strong> 五项指标来自招聘文本术语命中率，并在13个职业类别内部做Min-Max相对缩放。'
        "AI暴露代理指数由数字化强度45%、直接AI术语30%和可数字化重复任务25%加权。它用于比较岗位任务结构，不是官方统计、自动化概率或裁员风险。</div>",
        unsafe_allow_html=True,
    )
    st.dataframe(
        metrics[
            [
                "category", "ai_exposure", "repetitiveness", "creativity",
                "digital_intensity", "human_interaction", "sample_count",
            ]
        ]
        .sort_values("ai_exposure", ascending=False)
        .rename(
            columns={
                "category": "职业类别", "ai_exposure": "AI暴露代理指数",
                "repetitiveness": "重复性", "creativity": "创造性",
                "digital_intensity": "数字化强度", "human_interaction": "人际互动",
                "sample_count": "岗位样本数",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def show_transitions(
    data: dict[str, pd.DataFrame], selected_categories: list[str], with_header: bool = True
) -> None:
    if with_header:
        page_header(
            "CAREER TRANSITION SCENARIO",
            "职业转型与能力迁移路径",
            "把当前职业类别连接到AI增强岗位，展示可复用关键词、转型准备度和需要补齐的技能。",
        )
    transitions = data["career_transitions"]
    transitions = transitions[transitions["source_category"].isin(selected_categories)].copy()
    available = transitions.sort_values("readiness_score", ascending=False)["source_category"].tolist()
    defaults = [
        category for category in
        ["AI与算法", "软件开发", "数据分析", "设计内容", "市场运营", "财务金融", "制造工程", "服务物流"]
        if category in available
    ]
    chosen = st.multiselect(
        "选择转型起点（最多8类）",
        available,
        default=defaults or available[:8],
        max_selections=8,
    )
    if not chosen:
        st.info("请选择至少一个职业类别。")
        return
    transitions = transitions[transitions["source_category"].isin(chosen)]
    st.plotly_chart(career_transition_sankey(transitions), use_container_width=True, key="career_transition_sankey")
    ranking = transitions.sort_values("readiness_score", ascending=False)
    st.dataframe(
        ranking.rename(
            columns={
                "source_category": "当前职业类别", "target_role": "AI增强目标岗位",
                "transition_type": "转型类型", "readiness_score": "转型准备度",
                "shared_keywords": "当前高频关键词", "gap_skills": "建议补齐能力",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.markdown(
        '<div class="insight"><strong>迁移边界：</strong> 图中连线是基于岗位文本指标、当前关键词和目标能力设计的转型情景，'
        "不是对真实劳动者流动的追踪统计。转型准备度由数字化强度40%、创造性30%和AI暴露代理30%构成。</div>",
        unsafe_allow_html=True,
    )


def show_overview(
    data: dict[str, pd.DataFrame],
    categories: pd.DataFrame,
    selected_categories: list[str],
    with_header: bool = True,
) -> None:
    if with_header:
        page_header(
            "REAL RECRUITMENT SAMPLE",
            "生成式AI背景下职业演化与就业结构变化",
            "基于 109,986 条中国真实招聘样本，刻画当前职业结构、薪资、就业门槛和AI关联特征。",
        )
    meta = metadata_map(data)
    columns = st.columns(4)
    columns[0].metric("真实岗位样本", f"{int(meta['record_count']):,} 条", "去重职位链接")
    columns[1].metric("覆盖城市", f"{int(meta['city_count'])} 个", "多数城市约300条")
    columns[2].metric("AI关联岗位", f"{int(meta['ai_related_count']):,} 条", "文本规则识别")
    columns[3].metric("月薪中位数", f"{float(meta['overall_median_salary']):.1f} K", "含单位换算")

    left, right = st.columns([1.15, 1])
    with left:
        st.plotly_chart(category_market(categories), use_container_width=True, key="market_category_bars")
    with right:
        st.plotly_chart(ai_market_scatter(categories), use_container_width=True, key="market_ai_scatter_overview")

    st.markdown(
        '<div class="insight"><strong>阅读边界：</strong> 这是招聘平台便利样本，不是实时接口或概率抽样。'
        "城市样本量受采集上限影响，页面重点比较样本内部的薪资、AI岗位占比和职业结构，"
        "不把300条样本解释为城市总体招聘规模。</div>",
        unsafe_allow_html=True,
    )

    samples = data["job_samples"]
    samples = samples[samples["category"].isin(selected_categories)].head(300)
    st.dataframe(
        samples[["city", "title", "company", "category", "salary_text", "education", "experience", "job_url"]]
        .rename(
            columns={
                "city": "城市",
                "title": "职位",
                "company": "公司",
                "category": "类别",
                "salary_text": "薪资",
                "education": "学历",
                "experience": "经验",
                "job_url": "原始链接",
            }
        ),
        column_config={"原始链接": st.column_config.LinkColumn("原始链接")},
        hide_index=True,
        use_container_width=True,
    )


def show_city(data: dict[str, pd.DataFrame], selected_categories: list[str], with_header: bool = True) -> None:
    if with_header:
        page_header(
            "SPATIAL SAMPLE",
            "中国城市招聘画像",
            "比较重点城市样本的薪资中位数、AI岗位占比和本科及以上学历占比。",
        )
    cities = data["city_stats"]
    st.plotly_chart(city_map(cities), use_container_width=True, key="region_city_map")

    left, right = st.columns(2)
    with left:
        ranking = cities.sort_values("median_salary")
        fig = px.bar(
            ranking,
            x="median_salary",
            y="city",
            orientation="h",
            color="ai_share",
            color_continuous_scale=["#E9B949", "#0F766E"],
            title="重点城市月薪中位数",
            labels={"median_salary": "月薪中位数(K)", "city": "", "ai_share": "AI占比/%"},
        )
        st.plotly_chart(polish(fig, 580), use_container_width=True, key="region_city_salary")
    with right:
        city = st.selectbox("查看城市职业构成", cities.sort_values("city")["city"])
        composition = data["city_category"]
        composition = composition[
            (composition["city"] == city) & (composition["category"].isin(selected_categories))
        ].sort_values("sample_count")
        fig = px.bar(
            composition,
            x="sample_count",
            y="category",
            orientation="h",
            color="category",
            color_discrete_sequence=PALETTE,
            title=f"{city}样本职业构成",
            labels={"sample_count": "样本岗位数", "category": ""},
        )
        st.plotly_chart(polish(fig, 520), use_container_width=True, key="region_city_composition_bar")


def show_ai_profile(data: dict[str, pd.DataFrame], categories: pd.DataFrame, with_header: bool = True) -> None:
    if with_header:
        page_header(
            "AI JOB PROFILE",
            "AI 关联岗位画像",
            "依据职位名称、关键词和描述中的大模型、机器学习、算法等术语识别 AI 关联岗位。",
        )
    meta = metadata_map(data)
    ai_median = float(meta["ai_median_salary"])
    other_median = float(meta["non_ai_median_salary"])
    premium = (ai_median / other_median - 1) * 100
    columns = st.columns(3)
    columns[0].metric("AI关联岗位", f"{int(meta['ai_related_count']):,} 条")
    columns[1].metric("AI岗位月薪中位数", f"{ai_median:.1f} K")
    columns[2].metric("相对薪资溢价", f"{premium:.1f}%", f"非AI岗位 {other_median:.1f} K")
    st.plotly_chart(ai_market_scatter(categories), use_container_width=True, key="market_ai_scatter_profile")

    ai_jobs = data["job_samples"].query("ai_related == 1").sort_values("avg_salary_k", ascending=False)
    st.dataframe(
        ai_jobs[["city", "title", "company", "category", "salary_text", "education", "experience"]]
        .head(250)
        .rename(
            columns={
                "city": "城市",
                "title": "职位",
                "company": "公司",
                "category": "类别",
                "salary_text": "薪资",
                "education": "学历",
                "experience": "经验",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def show_flow(data: dict[str, pd.DataFrame], selected_categories: list[str], with_header: bool = True) -> None:
    if with_header:
        page_header(
            "CITY × OCCUPATION",
            "城市与职业构成",
            "用桑基图观察真实样本中城市与职业类别的对应关系，不将其解释为人员迁移。",
        )
    available = data["city_stats"].sort_values("median_salary", ascending=False)["city"].tolist()
    cities = st.multiselect("选择城市（2-6个）", available, default=["北京", "上海", "深圳", "杭州"], max_selections=6)
    if not cities:
        st.info("请选择至少一个城市。")
        return
    flow = data["city_category"]
    flow = flow[flow["category"].isin(selected_categories)]
    st.plotly_chart(city_category_sankey(flow, cities), use_container_width=True, key="region_city_category_sankey")
    st.dataframe(
        flow[flow["city"].isin(cities)]
        .sort_values(["city", "sample_count"], ascending=[True, False])
        .rename(columns={"city": "城市", "category": "职业类别", "sample_count": "样本岗位数"}),
        hide_index=True,
        use_container_width=True,
    )


def show_clusters(categories: pd.DataFrame, with_header: bool = True) -> None:
    if with_header:
        page_header(
            "MARKET SEGMENTS",
            "职业类别聚类",
            "使用样本量、薪资、AI占比、学历与经验门槛五项真实招聘指标进行 K-Means 聚类。",
        )
    st.plotly_chart(cluster_scatter(categories), use_container_width=True, key="market_cluster_scatter")
    summary = (
        categories.groupby("cluster_name", as_index=False)
        .agg(
            类别数=("category", "count"),
            月薪中位数=("median_salary", "mean"),
            AI占比=("ai_share", "mean"),
            本科及以上占比=("bachelor_share", "mean"),
        )
        .round(2)
    )
    st.dataframe(summary, hide_index=True, use_container_width=True)


def show_thresholds(data: dict[str, pd.DataFrame], with_header: bool = True) -> None:
    if with_header:
        page_header(
            "ENTRY THRESHOLDS",
            "学历与经验门槛",
            "比较不同学历、经验要求对应的岗位样本量、薪资中位数和 AI 岗位占比。",
        )
    education_tab, experience_tab = st.tabs(["学历要求", "经验要求"])
    with education_tab:
        frame = data["education_stats"]
        st.plotly_chart(threshold_chart(frame, "education"), use_container_width=True, key="market_education_threshold")
        st.dataframe(
            frame.rename(
                columns={
                    "education": "学历要求",
                    "sample_count": "样本岗位数",
                    "median_salary": "月薪中位数/K",
                    "ai_share": "AI岗位占比/%",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )
    with experience_tab:
        frame = data["experience_stats"]
        st.plotly_chart(threshold_chart(frame, "experience"), use_container_width=True, key="market_experience_threshold")
        st.dataframe(
            frame.rename(
                columns={
                    "experience": "经验要求",
                    "sample_count": "样本岗位数",
                    "median_salary": "月薪中位数/K",
                    "ai_share": "AI岗位占比/%",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )


def show_skills(data: dict[str, pd.DataFrame], selected_categories: list[str], with_header: bool = True) -> None:
    if with_header:
        page_header(
            "OBSERVED KEYWORDS",
            "职业技能关系网络",
            "从职位关键词字段提取高频要求，展示不同职业类别之间的技能复用关系。",
        )
    default = [category for category in ["AI与算法", "软件开发", "数据分析", "产品项目"] if category in selected_categories]
    chosen = st.multiselect(
        "选择职业类别（最多5个）",
        selected_categories,
        default=default,
        max_selections=5,
    )
    if not chosen:
        st.info("请选择至少一个职业类别。")
        return
    skills = data["category_skills"]
    st.plotly_chart(skill_network(skills, chosen), use_container_width=True, key="capability_skill_network")
    st.dataframe(
        skills[skills["category"].isin(chosen)]
        .sort_values(["category", "sample_count"], ascending=[True, False])
        .rename(
            columns={
                "category": "职业类别",
                "skill": "岗位关键词",
                "sample_count": "出现次数",
                "share": "类别内占比/%",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )


def show_task_skill_dashboard(data: dict[str, pd.DataFrame], selected_categories: list[str]) -> None:
    page_header(
        "OCCUPATION CAPABILITY",
        "职业任务暴露与技能结构",
        "把AI暴露度、重复性、创造性和技能复用关系放在同一页，解释职业为什么会发生能力重组。",
    )
    task_tab, skill_tab = st.tabs(["AI暴露与任务结构", "技能关系网络"])
    with task_tab:
        show_task_metrics(data, selected_categories, with_header=False)
    with skill_tab:
        show_skills(data, selected_categories, with_header=False)


def show_region_dashboard(data: dict[str, pd.DataFrame], selected_categories: list[str]) -> None:
    page_header(
        "REGIONAL DIFFERENCE",
        "城市空间分布与职业结构",
        "从城市薪资、AI岗位占比和城市-职业构成观察生成式AI背景下的区域差异。",
    )
    map_tab, flow_tab = st.tabs(["城市热力与薪资", "城市-职业构成"])
    with map_tab:
        show_city(data, selected_categories, with_header=False)
    with flow_tab:
        show_flow(data, selected_categories, with_header=False)


def show_market_dashboard(
    data: dict[str, pd.DataFrame], categories: pd.DataFrame, selected_categories: list[str]
) -> None:
    page_header(
        "RECRUITMENT EVIDENCE",
        "招聘市场画像与就业门槛",
        "集中查看真实招聘样本中的岗位分布、AI岗位画像、职业聚类、学历经验门槛和样本明细。",
    )
    overview_tab, ai_tab, cluster_tab, threshold_tab = st.tabs(
        ["职业市场结构", "AI岗位画像", "职业聚类", "学历经验门槛"]
    )
    with overview_tab:
        show_overview(data, categories, selected_categories, with_header=False)
    with ai_tab:
        show_ai_profile(data, categories, with_header=False)
    with cluster_tab:
        show_clusters(categories, with_header=False)
    with threshold_tab:
        show_thresholds(data, with_header=False)


ensure_database()
data = load_data()
all_categories = data["category_stats"].sort_values("sample_count", ascending=False)["category"].tolist()

NAV_ITEMS = [
    {
        "key": "structure",
        "label": "01 宏观背景：就业结构演化",
        "caption": "先看中国三次产业就业结构如何变化，建立生成式AI影响就业的宏观背景。",
    },
    {
        "key": "market",
        "label": "02 市场证据：招聘样本画像",
        "caption": "先用真实招聘样本确认当前职业结构、AI岗位画像、职业聚类和学历经验门槛。",
    },
    {
        "key": "region",
        "label": "03 空间差异：城市分布格局",
        "caption": "再观察城市薪资、AI岗位占比和城市-职业构成，说明中国地区分布差异。",
    },
    {
        "key": "capability",
        "label": "04 影响机制：任务暴露与技能",
        "caption": "在现实样本基础上解释AI为什么影响职业：AI暴露度、重复性、创造性、数字强度和技能复用。",
    },
    {
        "key": "forecast",
        "label": "05 趋势预测：产业与职业情景",
        "caption": "基于宏观历史序列外推2026—2030年产业趋势，并映射到职业需求情景。",
    },
    {
        "key": "transition",
        "label": "06 转型路径：职业迁移方向",
        "caption": "最后把当前职业连接到AI增强岗位，展示技能缺口、迁移方向和转型准备度。",
    },
]
NAV_MAP = {item["key"]: item for item in NAV_ITEMS}

st.sidebar.markdown("## AI职业演化分析")
st.sidebar.caption("从现实证据到预测推演的递进式可视化")
st.sidebar.markdown(
    """
    <div class="sidebar-stage">
        <strong>研究主线</strong>
        宏观背景 → 市场证据 → 空间差异 → 影响机制 → 趋势预测 → 转型路径
    </div>
    """,
    unsafe_allow_html=True,
)
page = st.sidebar.radio(
    "分析主线",
    [item["key"] for item in NAV_ITEMS],
    format_func=lambda key: NAV_MAP[key]["label"],
)
st.sidebar.info(NAV_MAP[page]["caption"])
selected_categories = st.sidebar.multiselect("职业类别", all_categories, default=all_categories)
if not selected_categories:
    selected_categories = all_categories
filtered_categories = data["category_stats"][data["category_stats"]["category"].isin(selected_categories)]

meta = metadata_map(data)
st.sidebar.markdown(f'<div class="runtime">{describe_runtime()}</div>', unsafe_allow_html=True)
st.sidebar.caption(f"数据：{meta['source']} · {meta['license']}")
st.sidebar.caption(f"趋势：{meta['trend_source']} · {meta['trend_years']}")
st.sidebar.caption("年度趋势为官方开放数据；招聘数据为非实时便利样本。")

if page == "structure":
    show_evolution(data)
elif page == "forecast":
    show_forecast(data, selected_categories)
elif page == "capability":
    show_task_skill_dashboard(data, selected_categories)
elif page == "transition":
    show_transitions(data, selected_categories)
elif page == "region":
    show_region_dashboard(data, selected_categories)
else:
    show_market_dashboard(data, filtered_categories, selected_categories)
