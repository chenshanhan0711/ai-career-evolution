from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd


COLUMN_MAP = {
    "发布城市": "city",
    "城市代码": "city_code",
    "职位链接": "job_url",
    "职位名称": "title",
    "薪资": "salary_text",
    "工作地点": "work_location",
    "经验要求": "experience",
    "学历要求": "education",
    "公司名称": "company",
    "职位关键字": "keywords",
    "职位描述": "description",
    "融资情况": "finance_stage",
    "公司规模": "company_size",
    "公司行业": "industry",
}

CATEGORY_PATTERNS = [
    ("AI与算法", r"人工智能|AIGC|大模型|机器学习|深度学习|神经网络|自然语言|NLP|计算机视觉|算法|智能体"),
    ("软件开发", r"开发|程序员|前端|后端|软件|测试|运维|网络工程|Java|Python|C\+\+|Android|iOS|嵌入式"),
    ("数据分析", r"数据分析|数据开发|数据治理|数据仓库|商业分析|统计分析|数据库|BI工程|数据运营"),
    ("产品项目", r"产品经理|产品运营|项目经理|项目管理|需求分析|产品设计"),
    ("设计内容", r"设计|文案|编辑|内容|视觉|视频|摄影|美术|UI|UX"),
    ("市场运营", r"运营|市场|推广|营销|策划|新媒体|电商"),
    ("销售商务", r"销售|商务|客户经理|招商|渠道"),
    ("财务金融", r"财务|会计|审计|金融|银行|证券|风控|投资|保险"),
    ("人事行政", r"人力|招聘|行政|助理|秘书|法务"),
    ("医疗教育", r"医生|护士|医师|医疗|药师|教师|老师|讲师|教育|培训"),
    ("制造工程", r"工程师|机械|电气|工艺|生产|制造|质量|采购|供应链|建筑|施工|技术员"),
    ("服务物流", r"客服|物流|仓储|配送|司机|服务员|店员|保安|保洁|快递|骑手"),
]

AI_PATTERN = re.compile(
    r"人工智能|AIGC|大模型|机器学习|深度学习|神经网络|自然语言|NLP|计算机视觉|"
    r"ChatGPT|智能体|算法工程师|模型训练|推荐算法|语音识别",
    re.IGNORECASE,
)


def parse_salary(value: object) -> tuple[float, float, float, int]:
    text = "" if pd.isna(value) else str(value).strip()
    months_match = re.search(r"[·x×](\d{2})薪", text, re.IGNORECASE)
    salary_months = int(months_match.group(1)) if months_match else 12

    patterns = [
        (r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)K", 1.0),
        (r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)元/月", 0.001),
        (r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)元/天", 21.75 / 1000),
        (r"(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)元/时", 174 / 1000),
    ]
    for pattern, factor in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        minimum = float(match.group(1)) * factor
        maximum = float(match.group(2)) * factor
        monthly = (minimum + maximum) / 2 * salary_months / 12
        if 1 <= minimum <= maximum <= 300 and 1 <= monthly <= 300:
            return round(minimum, 2), round(maximum, 2), round(monthly, 2), salary_months
    return np.nan, np.nan, np.nan, salary_months


def classify_jobs(frame: pd.DataFrame) -> pd.Series:
    text = (
        frame["title"].fillna("")
        + " "
        + frame["keywords"].fillna("")
        + " "
        + frame["industry"].fillna("")
    )
    result = pd.Series("其他职业", index=frame.index, dtype="object")
    unmatched = pd.Series(True, index=frame.index)
    for category, pattern in CATEGORY_PATTERNS:
        matches = unmatched & text.str.contains(pattern, case=False, regex=True)
        result.loc[matches] = category
        unmatched.loc[matches] = False
    return result


def prepare(source: Path, output: Path) -> pd.DataFrame:
    frame = pd.read_excel(source, usecols=list(COLUMN_MAP)).rename(columns=COLUMN_MAP)
    frame = frame.drop_duplicates(subset=["job_url"]).copy()

    salary = frame["salary_text"].apply(parse_salary)
    frame[["salary_min_k", "salary_max_k", "avg_salary_k", "salary_months"]] = pd.DataFrame(
        salary.tolist(), index=frame.index
    )
    frame["category"] = classify_jobs(frame)
    searchable = (
        frame["title"].fillna("")
        + " "
        + frame["keywords"].fillna("")
        + " "
        + frame["description"].fillna("")
    )
    frame["ai_related"] = searchable.map(lambda value: int(bool(AI_PATTERN.search(value))))
    frame["job_url"] = frame["job_url"].fillna("").str.split("?").str[0]

    output.parent.mkdir(parents=True, exist_ok=True)
    export_columns = [
        "city",
        "city_code",
        "job_url",
        "title",
        "salary_text",
        "salary_min_k",
        "salary_max_k",
        "avg_salary_k",
        "salary_months",
        "experience",
        "education",
        "company",
        "keywords",
        "finance_stage",
        "company_size",
        "industry",
        "category",
        "ai_related",
    ]
    frame[export_columns].to_csv(output, index=False, compression="gzip")
    return frame[export_columns]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the licensed BOSS Zhipin sample.")
    parser.add_argument("source", type=Path, help="Path to BOSS_Zhipin_Sample_Data.xlsx")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/china_jobs_clean.csv.gz"),
        help="Processed gzip CSV path",
    )
    args = parser.parse_args()
    result = prepare(args.source, args.output)
    print(f"Prepared {len(result):,} unique real job postings: {args.output}")
    print(f"Cities: {result['city'].nunique()}, categories: {result['category'].nunique()}")


if __name__ == "__main__":
    main()

