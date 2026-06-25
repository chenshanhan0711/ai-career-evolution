from __future__ import annotations

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


PALETTE = ["#0F766E", "#E76F51", "#E9B949", "#3B82A0", "#6B7280", "#8B5E83"]
CHART_BG = "rgba(0,0,0,0)"
SECTOR_COLORS = {"第一产业": "#E9B949", "第二产业": "#3B82A0", "第三产业": "#0F766E"}
SECTOR_FILLS = {
    "第一产业": "rgba(233,185,73,0.14)",
    "第二产业": "rgba(59,130,160,0.14)",
    "第三产业": "rgba(15,118,110,0.14)",
}


def polish(fig: go.Figure, height: int = 430) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=55, b=30),
        paper_bgcolor=CHART_BG,
        plot_bgcolor=CHART_BG,
        font=dict(family="Arial, PingFang SC, Microsoft YaHei", color="#25312F"),
        title_font=dict(size=17, color="#17211F"),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    fig.update_xaxes(gridcolor="#E3E8E5", zeroline=False)
    fig.update_yaxes(gridcolor="#E3E8E5", zeroline=False)
    return fig


def category_market(frame: pd.DataFrame) -> go.Figure:
    data = frame.sort_values("sample_count")
    fig = px.bar(
        data,
        x="sample_count",
        y="category",
        orientation="h",
        color="median_salary",
        color_continuous_scale=["#E9B949", "#0F766E"],
        labels={"sample_count": "样本岗位数", "category": "", "median_salary": "薪资中位数/K"},
        title="职业类别样本量与月薪中位数",
        hover_data={"ai_share": ":.2f", "bachelor_share": ":.1f"},
    )
    return polish(fig, 520)


def employment_evolution(frame: pd.DataFrame) -> go.Figure:
    data = frame[frame["year"] >= 2000].sort_values("year")
    fig = px.area(
        data,
        x="year",
        y="employment_share",
        color="sector",
        color_discrete_map=SECTOR_COLORS,
        category_orders={"sector": ["第一产业", "第二产业", "第三产业"]},
        title="2000—2025年中国三次产业就业结构演化",
        labels={"year": "年份", "employment_share": "就业人员占比(%)", "sector": ""},
    )
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(range=[0, 100])
    return polish(fig, 520)


def employment_forecast_chart(frame: pd.DataFrame) -> go.Figure:
    data = frame[frame["year"] >= 2010].copy()
    fig = go.Figure()
    for sector, color in SECTOR_COLORS.items():
        sector_data = data[data["sector"] == sector].sort_values("year")
        actual = sector_data[sector_data["status"] == "实际"]
        predicted = sector_data[sector_data["status"] == "预测"]
        anchor = actual.tail(1)
        forecast_line = pd.concat([anchor, predicted], ignore_index=True)
        band = pd.concat([anchor.assign(lower=anchor["share"], upper=anchor["share"]), predicted])
        fig.add_trace(
            go.Scatter(
                x=band["year"],
                y=band["upper"],
                mode="lines",
                line=dict(width=0),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=band["year"],
                y=band["lower"],
                mode="lines",
                line=dict(width=0),
                fill="tonexty",
                fillcolor=SECTOR_FILLS[sector],
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=actual["year"],
                y=actual["share"],
                mode="lines",
                name=f"{sector}（实际）",
                line=dict(color=color, width=3),
                hovertemplate="%{x}年<br>%{y:.2f}%<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=forecast_line["year"],
                y=forecast_line["share"],
                mode="lines+markers",
                name=f"{sector}（预测）",
                line=dict(color=color, width=3, dash="dash"),
                marker=dict(size=6),
                hovertemplate="%{x}年<br>%{y:.2f}%<extra></extra>",
            )
        )
    fig.add_vline(x=2025.5, line_dash="dot", line_color="#6B7280")
    fig.add_annotation(x=2026, y=56, text="预测区间", showarrow=False, xanchor="left")
    fig.update_layout(
        title="中国三次产业就业占比：历史序列与2026—2030年趋势外推",
        xaxis_title="年份",
        yaxis_title="就业人员占比(%)",
        hovermode="x unified",
    )
    return polish(fig, 560)


def category_projection_chart(frame: pd.DataFrame) -> go.Figure:
    fig = px.line(
        frame,
        x="year",
        y="demand_index",
        color="category",
        markers=True,
        color_discrete_sequence=PALETTE,
        title="职业类别产业结构情景指数（2025年=100）",
        labels={"year": "年份", "demand_index": "结构情景指数", "category": ""},
        hover_data={"dominant_sector": True},
    )
    fig.add_hline(y=100, line_dash="dot", line_color="#6B7280")
    fig.update_layout(hovermode="x unified")
    return polish(fig, 500)


def category_sector_mix(frame: pd.DataFrame) -> go.Figure:
    data = frame.sort_values(["category", "sector"])
    fig = px.bar(
        data,
        x="category",
        y="share",
        color="sector",
        color_discrete_map=SECTOR_COLORS,
        category_orders={"sector": ["第一产业", "第二产业", "第三产业"]},
        title="当前招聘样本的职业类别—产业构成映射",
        labels={"category": "", "share": "类别内样本占比(%)", "sector": ""},
    )
    return polish(fig, 470)


def task_metric_scatter(frame: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        frame,
        x="repetitiveness",
        y="creativity",
        size="sample_count",
        color="ai_exposure",
        text="category",
        color_continuous_scale=["#E9B949", "#E76F51", "#0F766E"],
        size_max=48,
        title="职业任务结构：重复性、创造性与AI任务暴露代理指数",
        labels={
            "repetitiveness": "重复性代理指数",
            "creativity": "创造性代理指数",
            "ai_exposure": "AI暴露代理指数",
            "sample_count": "样本数",
        },
        hover_data={"digital_intensity": ":.1f", "human_interaction": ":.1f"},
    )
    fig.update_traces(textposition="top center")
    fig.update_xaxes(range=[0, 100])
    fig.update_yaxes(range=[0, 100])
    return polish(fig, 570)


def task_metric_heatmap(frame: pd.DataFrame) -> go.Figure:
    columns = [
        "ai_exposure", "repetitiveness", "creativity", "digital_intensity", "human_interaction"
    ]
    labels = ["AI暴露", "重复性", "创造性", "数字化强度", "人际互动"]
    data = frame.sort_values("ai_exposure", ascending=False)
    fig = go.Figure(
        go.Heatmap(
            z=data[columns].to_numpy(),
            x=labels,
            y=data["category"],
            zmin=0,
            zmax=100,
            colorscale=[[0, "#F7E8C6"], [0.5, "#D9E7ED"], [1, "#0F766E"]],
            text=data[columns].round(1).to_numpy(),
            texttemplate="%{text}",
            colorbar=dict(title="指数"),
            hovertemplate="%{y}<br>%{x}: %{z:.1f}<extra></extra>",
        )
    )
    fig.update_layout(title="五维岗位文本代理指标热力图")
    return polish(fig, 560)


def career_transition_sankey(frame: pd.DataFrame) -> go.Figure:
    labels = list(dict.fromkeys(frame["source_category"].tolist() + frame["target_role"].tolist()))
    indexes = {label: index for index, label in enumerate(labels)}
    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=17,
                thickness=16,
                label=labels,
                color=[PALETTE[index % len(PALETTE)] for index in range(len(labels))],
                line=dict(color="white", width=1),
            ),
            link=dict(
                source=frame["source_category"].map(indexes),
                target=frame["target_role"].map(indexes),
                value=frame["readiness_score"],
                color="rgba(15,118,110,0.22)",
                customdata=frame[["transition_type", "gap_skills"]].to_numpy(),
                hovertemplate=(
                    "%{source.label} → %{target.label}<br>转型准备度: %{value:.1f}"
                    "<br>类型: %{customdata[0]}<br>能力缺口: %{customdata[1]}<extra></extra>"
                ),
            ),
        )
    )
    fig.update_layout(title="职业类别向AI增强岗位的情景转型路径")
    return polish(fig, 650)


def city_map(frame: pd.DataFrame) -> go.Figure:
    data = frame.copy()
    data["bubble_size"] = data["ai_share"].clip(lower=0.2) + 0.8
    fig = px.scatter_geo(
        data,
        lon="longitude",
        lat="latitude",
        size="bubble_size",
        color="median_salary",
        hover_name="city",
        hover_data={
            "sample_count": True,
            "median_salary": ":.1f",
            "ai_share": ":.2f",
            "bachelor_share": ":.1f",
            "bubble_size": False,
        },
        color_continuous_scale=["#E9B949", "#0F766E", "#3B82A0"],
        size_max=38,
        title="重点城市真实招聘样本：薪资与 AI 岗位占比",
        labels={"median_salary": "月薪中位数/K", "ai_share": "AI岗位占比/%"},
    )
    fig.update_geos(
        projection_type="natural earth",
        fitbounds="locations",
        showland=True,
        landcolor="#EEF2F0",
        showocean=True,
        oceancolor="#F7FAF9",
        showcountries=True,
        countrycolor="#B9C6C1",
        coastlinecolor="#B9C6C1",
        showframe=False,
    )
    return polish(fig, 560)


def ai_market_scatter(frame: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        frame,
        x="ai_share",
        y="median_salary",
        size="sample_count",
        color="category",
        color_discrete_sequence=PALETTE,
        size_max=45,
        title="AI 关联岗位占比与薪资中位数",
        labels={"ai_share": "AI关联岗位占比(%)", "median_salary": "月薪中位数(K)"},
        hover_data={"bachelor_share": ":.1f", "experienced_share": ":.1f"},
    )
    return polish(fig, 530)


def city_category_sankey(frame: pd.DataFrame, cities: list[str]) -> go.Figure:
    data = frame[frame["city"].isin(cities)].copy()
    data = data[data["category"] != "其他职业"]
    labels = list(dict.fromkeys(data["city"].tolist() + data["category"].tolist()))
    index = {label: position for position, label in enumerate(labels)}
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(labels))]
    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=18,
                thickness=16,
                line=dict(color="#FFFFFF", width=1),
                label=labels,
                color=colors,
            ),
            link=dict(
                source=data["city"].map(index),
                target=data["category"].map(index),
                value=data["sample_count"],
                color="rgba(15,118,110,0.23)",
            ),
        )
    )
    fig.update_layout(title="城市样本与职业类别构成")
    return polish(fig, 580)


def cluster_scatter(frame: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        frame,
        x="pca_x",
        y="pca_y",
        size="sample_count",
        color="cluster_name",
        hover_name="category",
        hover_data={
            "median_salary": ":.1f",
            "ai_share": ":.2f",
            "bachelor_share": ":.1f",
            "experienced_share": ":.1f",
            "pca_x": False,
            "pca_y": False,
        },
        color_discrete_sequence=PALETTE,
        title="真实招聘指标 K-Means 聚类（PCA 二维投影）",
        labels={"pca_x": "主成分 1", "pca_y": "主成分 2"},
        size_max=42,
    )
    return polish(fig, 540)


def threshold_chart(frame: pd.DataFrame, dimension: str) -> go.Figure:
    fig = px.bar(
        frame,
        x=dimension,
        y="median_salary",
        color="ai_share",
        color_continuous_scale=["#E9B949", "#E76F51"],
        text="sample_count",
        title=f"{dimension}对应的薪资中位数与样本量",
        labels={"median_salary": "月薪中位数(K)", "ai_share": "AI岗位占比(%)"},
    )
    fig.update_traces(texttemplate="%{text:,}条", textposition="outside")
    return polish(fig, 450)


def skill_network(frame: pd.DataFrame, categories: list[str]) -> go.Figure:
    data = frame[frame["category"].isin(categories)].copy()
    data = data.sort_values(["category", "sample_count"], ascending=[True, False])
    data = data.groupby("category", group_keys=False).head(8)
    graph = nx.Graph()
    for row in data.itertuples():
        graph.add_node(row.category, node_type="category")
        graph.add_node(row.skill, node_type="skill")
        graph.add_edge(row.category, row.skill, weight=row.sample_count)

    category_nodes = [node for node, attrs in graph.nodes(data=True) if attrs["node_type"] == "category"]
    skill_nodes = [node for node, attrs in graph.nodes(data=True) if attrs["node_type"] == "skill"]
    positions = nx.bipartite_layout(graph, category_nodes, align="vertical", scale=1.3, aspect_ratio=1.8)

    edge_x: list[float | None] = []
    edge_y: list[float | None] = []
    for source, target in graph.edges():
        x0, y0 = positions[source]
        x1, y1 = positions[target]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    traces: list[go.Scatter] = [
        go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(width=1.2, color="#B9C6C1"),
            hoverinfo="skip",
            showlegend=False,
        )
    ]
    for nodes, color, size, label, position in [
        (skill_nodes, "#E9B949", 14, "真实岗位关键词", "middle right"),
        (category_nodes, "#0F766E", 25, "职业类别", "middle left"),
    ]:
        traces.append(
            go.Scatter(
                x=[positions[node][0] for node in nodes],
                y=[positions[node][1] for node in nodes],
                text=nodes,
                hovertext=nodes,
                mode="markers+text",
                textposition=position,
                name=label,
                marker=dict(size=size, color=color, line=dict(width=1.5, color="white")),
            )
        )

    fig = go.Figure(traces)
    fig.update_layout(
        title="职业类别与高频招聘关键词网络",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        showlegend=True,
    )
    return polish(fig, 620)
