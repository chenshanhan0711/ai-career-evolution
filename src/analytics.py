from __future__ import annotations

import os

if not os.environ.get("LOKY_MAX_CPU_COUNT"):
    os.environ["LOKY_MAX_CPU_COUNT"] = str(os.cpu_count() or 1)

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


MARKET_FEATURES = [
    "sample_count",
    "median_salary",
    "ai_share",
    "bachelor_share",
    "experienced_share",
]

SECTOR_COLUMNS = {
    "第一产业": "agriculture_share",
    "第二产业": "industry_share",
    "第三产业": "services_share",
}


def cluster_market_segments(frame: pd.DataFrame, n_clusters: int = 4) -> pd.DataFrame:
    """Cluster occupation categories using observed recruitment indicators."""
    if len(frame) < n_clusters:
        raise ValueError("The category sample is smaller than the requested cluster count.")

    features = frame[MARKET_FEATURES].astype(float)
    scaled = StandardScaler().fit_transform(features)
    labels = KMeans(n_clusters=n_clusters, random_state=42, n_init=20).fit_predict(scaled)
    coordinates = PCA(n_components=2, random_state=42).fit_transform(scaled)

    result = frame.copy()
    result["cluster_id"] = labels
    result["pca_x"] = coordinates[:, 0]
    result["pca_y"] = coordinates[:, 1]

    summaries = result.groupby("cluster_id")[
        ["median_salary", "ai_share", "bachelor_share"]
    ].mean()
    remaining = set(summaries.index)
    names: dict[int, str] = {}

    ai_cluster = summaries.loc[list(remaining), "ai_share"].idxmax()
    names[ai_cluster] = "AI密集型"
    remaining.remove(ai_cluster)

    salary_cluster = summaries.loc[list(remaining), "median_salary"].idxmax()
    names[salary_cluster] = "高薪专业型"
    remaining.remove(salary_cluster)

    education_cluster = summaries.loc[list(remaining), "bachelor_share"].idxmax()
    names[education_cluster] = "知识门槛型"
    remaining.remove(education_cluster)

    for cluster_id in remaining:
        names[cluster_id] = "综合就业型"

    result["cluster_name"] = result["cluster_id"].map(names)
    return result


def salary_premium(frame: pd.DataFrame) -> float:
    """Return the median salary premium of AI-related jobs over other jobs."""
    valid = frame.dropna(subset=["avg_salary_k"])
    ai_salary = valid.loc[valid["ai_related"] == 1, "avg_salary_k"].median()
    other_salary = valid.loc[valid["ai_related"] == 0, "avg_salary_k"].median()
    if not other_salary:
        return 0.0
    return float((ai_salary / other_salary - 1) * 100)


def _linear_prediction(years: np.ndarray, values: np.ndarray, target: int) -> float:
    slope, intercept = np.polyfit(years.astype(float), values.astype(float), 1)
    return float(slope * target + intercept)


def forecast_employment_structure(
    frame: pd.DataFrame,
    forecast_end: int = 2030,
    window: int = 12,
    backtest_years: int = 5,
) -> pd.DataFrame:
    """Forecast sector shares with rolling-origin validation and linear trends."""
    required = {"year", *SECTOR_COLUMNS.values()}
    if missing := required.difference(frame.columns):
        raise ValueError(f"Missing employment structure columns: {sorted(missing)}")

    history = frame.sort_values("year").dropna(subset=list(required)).copy()
    if len(history) < max(8, backtest_years + 3):
        raise ValueError("At least eight annual observations are required.")

    last_year = int(history["year"].max())
    future_years = list(range(last_year + 1, forecast_end + 1))
    errors: dict[str, list[float]] = {sector: [] for sector in SECTOR_COLUMNS}

    test_years = history["year"].tail(backtest_years).astype(int).tolist()
    for test_year in test_years:
        training = history[history["year"] < test_year].tail(window)
        for sector, column in SECTOR_COLUMNS.items():
            prediction = _linear_prediction(
                training["year"].to_numpy(), training[column].to_numpy(), test_year
            )
            actual = float(history.loc[history["year"] == test_year, column].iloc[0])
            errors[sector].append(actual - prediction)

    actual_rows: list[dict[str, float | int | str]] = []
    for row in history.itertuples(index=False):
        for sector, column in SECTOR_COLUMNS.items():
            share = float(getattr(row, column))
            actual_rows.append(
                {
                    "year": int(row.year),
                    "sector": sector,
                    "share": share,
                    "lower": share,
                    "upper": share,
                    "status": "实际",
                    "backtest_mae": float(np.mean(np.abs(errors[sector]))),
                }
            )

    raw_predictions: dict[int, dict[str, float]] = {}
    training = history.tail(window)
    for year in future_years:
        raw_predictions[year] = {
            sector: max(
                0.0,
                _linear_prediction(
                    training["year"].to_numpy(), training[column].to_numpy(), year
                ),
            )
            for sector, column in SECTOR_COLUMNS.items()
        }

    forecast_rows: list[dict[str, float | int | str]] = []
    for year, sector_values in raw_predictions.items():
        total = sum(sector_values.values())
        horizon = year - last_year
        for sector, raw_share in sector_values.items():
            share = raw_share / total * 100
            residuals = np.asarray(errors[sector], dtype=float)
            rmse = float(np.sqrt(np.mean(residuals**2))) if residuals.size else 0.0
            interval = 1.96 * rmse * np.sqrt(horizon)
            forecast_rows.append(
                {
                    "year": year,
                    "sector": sector,
                    "share": share,
                    "lower": max(0.0, share - interval),
                    "upper": min(100.0, share + interval),
                    "status": "预测",
                    "backtest_mae": float(np.mean(np.abs(residuals))) if residuals.size else 0.0,
                }
            )

    return pd.DataFrame(actual_rows + forecast_rows).round(
        {"share": 4, "lower": 4, "upper": 4, "backtest_mae": 4}
    )
