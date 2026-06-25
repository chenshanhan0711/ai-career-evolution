from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analytics import SECTOR_COLUMNS, cluster_market_segments, forecast_employment_structure
from src.config import get_database_path
from src.database import initialize_schema


DATA_FILE = ROOT / "data" / "china_jobs_clean.csv.gz"
EMPLOYMENT_FILE = ROOT / "data" / "china_employment_structure.csv"

CITY_COORDINATES = {
    "北京": (116.4074, 39.9042),
    "上海": (121.4737, 31.2304),
    "深圳": (114.0579, 22.5431),
    "广州": (113.2644, 23.1291),
    "杭州": (120.1551, 30.2741),
    "成都": (104.0665, 30.5723),
    "南京": (118.7969, 32.0603),
    "武汉": (114.3054, 30.5931),
    "苏州": (120.5853, 31.2989),
    "重庆": (106.5516, 29.5630),
    "西安": (108.9398, 34.3416),
    "天津": (117.2009, 39.0842),
    "长沙": (112.9388, 28.2282),
    "合肥": (117.2272, 31.8206),
    "宁波": (121.5504, 29.8746),
    "郑州": (113.6254, 34.7466),
    "青岛": (120.3826, 36.0671),
    "厦门": (118.0894, 24.4798),
    "济南": (117.1201, 36.6512),
    "福州": (119.2965, 26.0745),
    "香港": (114.1694, 22.3193),
    "澳门": (113.5439, 22.1987),
}

EDUCATION_ORDER = ["学历不限", "初中及以下", "高中", "中专/中技", "大专", "本科", "硕士", "博士"]
EXPERIENCE_ORDER = ["经验不限", "在校/应届", "1年以内", "1-3年", "3-5年", "5-10年", "10年以上"]
SKILL_STOPWORDS = {
    "不限",
    "其他",
    "全职",
    "兼职",
    "学历不限",
    "经验不限",
    "接受无经验",
    "沟通能力",
    "团队合作",
    "责任心强",
    "有相关经验",
}

PRIMARY_SECTOR_TERMS = ("农/林/牧/渔", "农业", "林业", "畜牧", "渔业")
SECONDARY_SECTOR_TERMS = (
    "制造",
    "加工",
    "机械",
    "设备",
    "机电",
    "重工",
    "建筑",
    "施工",
    "装修",
    "材料",
    "钢铁",
    "金属",
    "矿产",
    "采掘",
    "化工",
    "能源",
    "电力",
    "燃气",
    "水利",
    "汽车零部件",
    "食品/饮料/烟酒",
    "服装/纺织",
    "家具/家电/家居",
    "日化",
    "原材料",
    "新能源",
    "环保",
)

DIGITAL_TERMS = (
    "AI", "人工智能", "算法", "数据", "Python", "SQL", "软件", "系统", "平台",
    "互联网", "自动化", "数字化", "模型", "编程", "开发", "云计算", "智能",
)
ROUTINE_TERMS = (
    "录入", "审核", "核算", "盘点", "分拣", "打包", "接听", "客服", "跟单",
    "流水线", "操作工", "收银", "保洁", "仓库", "质检", "文员", "标准化", "排班",
)
CREATIVE_TERMS = (
    "设计", "创意", "策划", "研发", "研究", "架构", "写作", "内容", "产品",
    "算法", "建模", "方案", "艺术", "视觉", "创新", "导演", "编辑",
)
INTERACTION_TERMS = (
    "销售", "沟通", "客户", "咨询", "教师", "培训", "管理", "协调", "谈判",
    "服务", "医生", "护理", "招聘", "运营", "商务", "顾问",
)

TRANSITION_TARGETS = {
    "AI与算法": ("大模型应用工程师", "技术升级", "RAG、模型评测、智能体开发"),
    "软件开发": ("AI应用开发工程师", "技术升级", "模型API、向量数据库、AI工程化"),
    "数据分析": ("智能数据分析师", "AI增强转型", "机器学习、提示工程、因果分析"),
    "产品项目": ("AI产品经理", "AI增强转型", "AI产品设计、模型评测、数据合规"),
    "设计内容": ("AIGC内容设计师", "AI增强转型", "生成式设计、版权合规、工作流编排"),
    "市场运营": ("AI营销运营师", "AI增强转型", "营销自动化、实验设计、内容评测"),
    "销售商务": ("智能销售顾问", "职能数字化", "CRM分析、智能获客、方案提示工程"),
    "财务金融": ("智能财务分析师", "职能数字化", "数据治理、异常检测、模型风险"),
    "人事行政": ("人力资源数据分析师", "职能数字化", "人才分析、流程自动化、隐私合规"),
    "制造工程": ("智能制造工程师", "技术升级", "工业数据、机器视觉、预测性维护"),
    "医疗教育": ("智能教育与医疗服务专员", "AI增强转型", "领域知识库、人机协同、伦理合规"),
    "服务物流": ("智能物流调度师", "职能数字化", "路径优化、预测分析、自动化调度"),
    "其他职业": ("数字化业务专员", "基础数字化", "数据素养、办公自动化、AI工具验证"),
}


def percentage(series: pd.Series) -> float:
    return round(float(series.mean() * 100), 2)


def build_city_stats(frame: pd.DataFrame) -> pd.DataFrame:
    selected = frame[frame["city"].isin(CITY_COORDINATES)].copy()
    selected["bachelor_plus"] = selected["education"].isin(["本科", "硕士", "博士"])
    stats = (
        selected.groupby("city", as_index=False)
        .agg(
            sample_count=("title", "size"),
            median_salary=("avg_salary_k", "median"),
            ai_share=("ai_related", percentage),
            bachelor_share=("bachelor_plus", percentage),
        )
        .round({"median_salary": 2})
    )
    stats["longitude"] = stats["city"].map(lambda city: CITY_COORDINATES[city][0])
    stats["latitude"] = stats["city"].map(lambda city: CITY_COORDINATES[city][1])
    return stats[
        ["city", "longitude", "latitude", "sample_count", "median_salary", "ai_share", "bachelor_share"]
    ]


def build_category_stats(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    working["bachelor_plus"] = working["education"].isin(["本科", "硕士", "博士"])
    working["experienced"] = working["experience"].isin(["1-3年", "3-5年", "5-10年", "10年以上"])
    stats = (
        working.groupby("category", as_index=False)
        .agg(
            sample_count=("title", "size"),
            median_salary=("avg_salary_k", "median"),
            ai_share=("ai_related", percentage),
            bachelor_share=("bachelor_plus", percentage),
            experienced_share=("experienced", percentage),
        )
        .fillna({"median_salary": 0})
        .round({"median_salary": 2})
    )
    return cluster_market_segments(stats)


def build_city_category(frame: pd.DataFrame) -> pd.DataFrame:
    cities = list(CITY_COORDINATES)
    return (
        frame[frame["city"].isin(cities)]
        .groupby(["city", "category"], as_index=False)
        .size()
        .rename(columns={"size": "sample_count"})
    )


def build_threshold_stats(frame: pd.DataFrame, column: str, order: list[str]) -> pd.DataFrame:
    working = frame[frame[column].isin(order)].copy()
    result = (
        working.groupby(column, as_index=False)
        .agg(
            sample_count=("title", "size"),
            median_salary=("avg_salary_k", "median"),
            ai_share=("ai_related", percentage),
        )
        .fillna({"median_salary": 0})
        .round({"median_salary": 2})
    )
    rank = {value: index for index, value in enumerate(order)}
    result["sort_order"] = result[column].map(rank)
    return result.sort_values("sort_order").drop(columns="sort_order")


def clean_skill(value: object) -> list[str]:
    if pd.isna(value):
        return []
    output = []
    for skill in re.split(r"[,，、|；;]", str(value)):
        skill = re.sub(r"\s+", " ", skill).strip(" -/·")
        if not 2 <= len(skill) <= 24 or skill in SKILL_STOPWORDS:
            continue
        if re.fullmatch(r"[\d.%-]+", skill):
            continue
        output.append(skill)
    return list(dict.fromkeys(output))


def build_category_skills(frame: pd.DataFrame, limit: int = 30) -> pd.DataFrame:
    skills = frame[["category", "keywords"]].copy()
    skills["skill"] = skills["keywords"].map(clean_skill)
    skills = skills.drop(columns="keywords").explode("skill").dropna(subset=["skill"])
    counts = (
        skills.groupby(["category", "skill"], as_index=False)
        .size()
        .rename(columns={"size": "sample_count"})
    )
    totals = frame.groupby("category").size()
    counts["share"] = counts.apply(
        lambda row: round(row["sample_count"] / totals[row["category"]] * 100, 2), axis=1
    )
    return (
        counts.sort_values(["category", "sample_count"], ascending=[True, False])
        .groupby("category", as_index=False, group_keys=False)
        .head(limit)
    )


def build_job_samples(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "city",
        "title",
        "company",
        "category",
        "salary_text",
        "avg_salary_k",
        "experience",
        "education",
        "industry",
        "ai_related",
        "job_url",
    ]
    featured = frame.sort_values(["ai_related", "avg_salary_k"], ascending=False)
    featured = featured.groupby("category", group_keys=False).head(250)
    samples = featured[columns].drop_duplicates(subset=["job_url"]).head(3500).copy()
    samples.insert(0, "id", range(1, len(samples) + 1))
    return samples


def map_industry_sector(industry: object) -> str:
    value = "" if pd.isna(industry) else str(industry)
    if any(term in value for term in PRIMARY_SECTOR_TERMS):
        return "第一产业"
    if any(term in value for term in SECONDARY_SECTOR_TERMS):
        return "第二产业"
    return "第三产业"


def build_category_sector(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame[["category", "industry"]].copy()
    working["sector"] = working["industry"].map(map_industry_sector)
    counts = (
        working.groupby(["category", "sector"], as_index=False)
        .size()
        .rename(columns={"size": "sample_count"})
    )
    totals = counts.groupby("category")["sample_count"].transform("sum")
    counts["share"] = (counts["sample_count"] / totals * 100).round(4)
    return counts


def build_employment_tables(
    employment: pd.DataFrame, category_sector: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    history = employment.melt(
        id_vars="year",
        value_vars=list(SECTOR_COLUMNS.values()),
        var_name="indicator",
        value_name="employment_share",
    )
    column_to_sector = {column: sector for sector, column in SECTOR_COLUMNS.items()}
    history["sector"] = history["indicator"].map(column_to_sector)
    history = history[["year", "sector", "employment_share"]].round(4)

    forecast = forecast_employment_structure(employment, forecast_end=2030)
    latest_year = int(employment["year"].max())
    baseline = (
        forecast[(forecast["year"] == latest_year) & (forecast["status"] == "实际")]
        .set_index("sector")["share"]
        .to_dict()
    )
    projected = forecast[forecast["year"] >= latest_year]
    factors = {
        (int(row.year), row.sector): float(row.share) / baseline[row.sector]
        for row in projected.itertuples()
    }

    projection_rows = []
    for category, group in category_sector.groupby("category"):
        weights = dict(zip(group["sector"], group["share"] / 100))
        dominant_sector = group.loc[group["share"].idxmax(), "sector"]
        for year in range(latest_year, 2031):
            index = sum(
                weight * factors[(year, sector)] for sector, weight in weights.items()
            ) * 100
            projection_rows.append(
                {
                    "category": category,
                    "year": year,
                    "demand_index": round(index, 3),
                    "dominant_sector": dominant_sector,
                }
            )
    return history, forecast, pd.DataFrame(projection_rows)


def _contains_any(text: pd.Series, terms: tuple[str, ...]) -> pd.Series:
    pattern = "|".join(re.escape(term) for term in terms)
    return text.str.contains(pattern, case=False, regex=True, na=False)


def _scaled_proxy(series: pd.Series, lower: float = 10, upper: float = 90) -> pd.Series:
    minimum, maximum = float(series.min()), float(series.max())
    if maximum == minimum:
        return pd.Series(50.0, index=series.index)
    return lower + (series - minimum) / (maximum - minimum) * (upper - lower)


def build_task_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame[["category", "title", "keywords", "industry", "ai_related"]].copy()
    text_columns = working[["title", "keywords", "industry"]].fillna("").astype(str)
    working["text"] = text_columns.agg(" ".join, axis=1)
    working["digital_match"] = _contains_any(working["text"], DIGITAL_TERMS)
    working["routine_match"] = _contains_any(working["text"], ROUTINE_TERMS)
    working["creative_match"] = _contains_any(working["text"], CREATIVE_TERMS)
    working["interaction_match"] = _contains_any(working["text"], INTERACTION_TERMS)
    rates = (
        working.groupby("category", as_index=False)
        .agg(
            sample_count=("title", "size"),
            direct_ai_rate=("ai_related", "mean"),
            digital_match_rate=("digital_match", "mean"),
            routine_match_rate=("routine_match", "mean"),
            creative_match_rate=("creative_match", "mean"),
            interaction_match_rate=("interaction_match", "mean"),
        )
    )
    rates["digital_intensity"] = _scaled_proxy(rates["digital_match_rate"])
    rates["repetitiveness"] = _scaled_proxy(rates["routine_match_rate"])
    rates["creativity"] = _scaled_proxy(rates["creative_match_rate"])
    rates["human_interaction"] = _scaled_proxy(rates["interaction_match_rate"])
    direct_ai_score = _scaled_proxy(rates["direct_ai_rate"])
    rates["ai_exposure"] = (
        0.45 * rates["digital_intensity"]
        + 0.30 * direct_ai_score
        + 0.25 * rates["digital_intensity"] * rates["repetitiveness"] / 100
    ).clip(0, 100)
    rate_columns = [
        "direct_ai_rate", "routine_match_rate", "creative_match_rate"
    ]
    rates[rate_columns] = (rates[rate_columns] * 100).round(3)
    return rates[
        [
            "category", "sample_count", "ai_exposure", "repetitiveness", "creativity",
            "digital_intensity", "human_interaction", "direct_ai_rate",
            "routine_match_rate", "creative_match_rate",
        ]
    ].round(3)


def build_career_transitions(
    task_metrics: pd.DataFrame, category_skills: pd.DataFrame
) -> pd.DataFrame:
    top_keywords = (
        category_skills.sort_values(["category", "sample_count"], ascending=[True, False])
        .groupby("category")["skill"]
        .apply(lambda values: "、".join(values.head(3)))
        .to_dict()
    )
    rows = []
    for metric in task_metrics.itertuples():
        target, transition_type, gap_skills = TRANSITION_TARGETS[metric.category]
        readiness = (
            0.40 * metric.digital_intensity
            + 0.30 * metric.creativity
            + 0.30 * metric.ai_exposure
        )
        rows.append(
            {
                "source_category": metric.category,
                "target_role": target,
                "transition_type": transition_type,
                "readiness_score": round(readiness, 2),
                "shared_keywords": top_keywords.get(metric.category, "暂无高频关键词"),
                "gap_skills": gap_skills,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the real China recruitment database.")
    parser.add_argument("--path", type=Path, help="Optional explicit database path.")
    args = parser.parse_args()
    db_path = args.path.resolve() if args.path else get_database_path()
    if db_path.exists():
        with sqlite3.connect(db_path) as connection:
            for legacy_table in [
                "occupations",
                "city_jobs",
                "demand_history",
                "migrations",
                "occupation_skills",
            ]:
                connection.execute(f"DROP TABLE IF EXISTS {legacy_table}")
    initialize_schema(db_path)

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing processed real dataset: {DATA_FILE}. See data/README.md for preparation steps."
        )
    if not EMPLOYMENT_FILE.exists():
        raise FileNotFoundError(
            f"Missing official employment series: {EMPLOYMENT_FILE}. "
            "Run scripts/fetch_employment_trends.py first."
        )
    frame = pd.read_csv(DATA_FILE)
    employment = pd.read_csv(EMPLOYMENT_FILE)

    city_stats = build_city_stats(frame)
    category_stats = build_category_stats(frame)
    city_category = build_city_category(frame)
    education_stats = build_threshold_stats(frame, "education", EDUCATION_ORDER)
    experience_stats = build_threshold_stats(frame, "experience", EXPERIENCE_ORDER)
    category_skills = build_category_skills(frame)
    job_samples = build_job_samples(frame)
    occupation_task_metrics = build_task_metrics(frame)
    career_transitions = build_career_transitions(occupation_task_metrics, category_skills)
    category_sector = build_category_sector(frame)
    employment_history, employment_forecast, category_projection = build_employment_tables(
        employment, category_sector
    )
    metadata = pd.DataFrame(
        [
            ("data_version", "BOSS_Zhipin_Sample_Data-2025-04-18"),
            ("source", "Kaggle BOSS_Zhipin_Sample_Data by jeanshendev"),
            ("source_url", "https://www.kaggle.com/datasets/jeanshendev/boss-zhipin-sample-data"),
            ("license", "MIT (as declared on the dataset page)"),
            ("record_count", f"{len(frame)}"),
            ("city_count", f"{frame['city'].nunique()}"),
            ("salary_valid_count", f"{frame['avg_salary_k'].notna().sum()}"),
            ("ai_related_count", f"{int(frame['ai_related'].sum())}"),
            ("overall_median_salary", f"{frame['avg_salary_k'].median():.2f}"),
            (
                "ai_median_salary",
                f"{frame.loc[frame['ai_related'] == 1, 'avg_salary_k'].median():.2f}",
            ),
            (
                "non_ai_median_salary",
                f"{frame.loc[frame['ai_related'] == 0, 'avg_salary_k'].median():.2f}",
            ),
            ("sampling_note", "Convenience sample; most cities contain about 300 records"),
            ("collection_date", "Not specified by the dataset publisher"),
            ("ai_definition", "Rule-based match on AI-related terms in titles, keywords and descriptions"),
            ("trend_source", "World Bank Open Data / ILO modeled estimate"),
            (
                "trend_source_url",
                "https://data.worldbank.org/indicator/SL.SRV.EMPL.ZS?locations=CN",
            ),
            (
                "trend_years",
                f"{int(employment['year'].min())}-{int(employment['year'].max())}",
            ),
            (
                "forecast_method",
                "12-year linear trend; five-year rolling-origin backtest; 95% residual interval",
            ),
            (
                "projection_note",
                "Category scenario index combines current recruitment industry mix with sector forecasts; 2025=100",
            ),
            (
                "task_proxy_note",
                "Text-derived relative proxies; AI exposure weights digital intensity, direct AI terms and digitally addressable routine tasks",
            ),
            (
                "transition_note",
                "Scenario pathways, not observed worker migration; readiness combines digital, creative and AI-exposure proxies",
            ),
        ],
        columns=["key", "value"],
    )

    with sqlite3.connect(db_path) as connection:
        city_stats.to_sql("city_stats", connection, if_exists="replace", index=False)
        category_stats.to_sql("category_stats", connection, if_exists="replace", index=False)
        city_category.to_sql("city_category", connection, if_exists="replace", index=False)
        education_stats.to_sql("education_stats", connection, if_exists="replace", index=False)
        experience_stats.to_sql("experience_stats", connection, if_exists="replace", index=False)
        category_skills.to_sql("category_skills", connection, if_exists="replace", index=False)
        job_samples.to_sql("job_samples", connection, if_exists="replace", index=False)
        employment_history.to_sql("employment_history", connection, if_exists="replace", index=False)
        employment_forecast.to_sql("employment_forecast", connection, if_exists="replace", index=False)
        category_sector.to_sql("category_sector", connection, if_exists="replace", index=False)
        category_projection.to_sql("category_projection", connection, if_exists="replace", index=False)
        occupation_task_metrics.to_sql(
            "occupation_task_metrics", connection, if_exists="replace", index=False
        )
        career_transitions.to_sql("career_transitions", connection, if_exists="replace", index=False)
        metadata.to_sql("metadata", connection, if_exists="replace", index=False)
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_city_category_city ON city_category(city);
            CREATE INDEX IF NOT EXISTS idx_skills_category ON category_skills(category);
            CREATE INDEX IF NOT EXISTS idx_samples_category_city ON job_samples(category, city);
            CREATE INDEX IF NOT EXISTS idx_employment_year ON employment_forecast(year);
            CREATE INDEX IF NOT EXISTS idx_projection_category ON category_projection(category);
            """
        )

    print(f"Database initialized from licensed real sample: {db_path}")
    print(
        f"Records analyzed: {len(frame):,}; cities: {frame['city'].nunique()}; "
        f"AI-related postings: {int(frame['ai_related'].sum()):,}"
    )


if __name__ == "__main__":
    main()
