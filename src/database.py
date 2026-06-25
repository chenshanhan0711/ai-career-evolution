from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import get_database_path


TABLES = {
    "city_stats",
    "category_stats",
    "city_category",
    "education_stats",
    "experience_stats",
    "category_skills",
    "job_samples",
    "employment_history",
    "employment_forecast",
    "category_sector",
    "category_projection",
    "occupation_task_metrics",
    "career_transitions",
    "metadata",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS city_stats (
    city TEXT PRIMARY KEY,
    longitude REAL NOT NULL,
    latitude REAL NOT NULL,
    sample_count INTEGER NOT NULL,
    median_salary REAL NOT NULL,
    ai_share REAL NOT NULL,
    bachelor_share REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS category_stats (
    category TEXT PRIMARY KEY,
    sample_count INTEGER NOT NULL,
    median_salary REAL NOT NULL,
    ai_share REAL NOT NULL,
    bachelor_share REAL NOT NULL,
    experienced_share REAL NOT NULL,
    cluster_id INTEGER,
    cluster_name TEXT,
    pca_x REAL,
    pca_y REAL
);

CREATE TABLE IF NOT EXISTS city_category (
    city TEXT NOT NULL,
    category TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    PRIMARY KEY (city, category)
);

CREATE TABLE IF NOT EXISTS education_stats (
    education TEXT PRIMARY KEY,
    sample_count INTEGER NOT NULL,
    median_salary REAL NOT NULL,
    ai_share REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS experience_stats (
    experience TEXT PRIMARY KEY,
    sample_count INTEGER NOT NULL,
    median_salary REAL NOT NULL,
    ai_share REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS category_skills (
    category TEXT NOT NULL,
    skill TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    share REAL NOT NULL,
    PRIMARY KEY (category, skill)
);

CREATE TABLE IF NOT EXISTS job_samples (
    id INTEGER PRIMARY KEY,
    city TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    category TEXT NOT NULL,
    salary_text TEXT,
    avg_salary_k REAL,
    experience TEXT,
    education TEXT,
    industry TEXT,
    ai_related INTEGER NOT NULL,
    job_url TEXT
);

CREATE TABLE IF NOT EXISTS employment_history (
    year INTEGER NOT NULL,
    sector TEXT NOT NULL,
    employment_share REAL NOT NULL,
    PRIMARY KEY (year, sector)
);

CREATE TABLE IF NOT EXISTS employment_forecast (
    year INTEGER NOT NULL,
    sector TEXT NOT NULL,
    share REAL NOT NULL,
    lower REAL NOT NULL,
    upper REAL NOT NULL,
    status TEXT NOT NULL,
    backtest_mae REAL NOT NULL,
    PRIMARY KEY (year, sector)
);

CREATE TABLE IF NOT EXISTS category_sector (
    category TEXT NOT NULL,
    sector TEXT NOT NULL,
    sample_count INTEGER NOT NULL,
    share REAL NOT NULL,
    PRIMARY KEY (category, sector)
);

CREATE TABLE IF NOT EXISTS category_projection (
    category TEXT NOT NULL,
    year INTEGER NOT NULL,
    demand_index REAL NOT NULL,
    dominant_sector TEXT NOT NULL,
    PRIMARY KEY (category, year)
);

CREATE TABLE IF NOT EXISTS occupation_task_metrics (
    category TEXT PRIMARY KEY,
    sample_count INTEGER NOT NULL,
    ai_exposure REAL NOT NULL,
    repetitiveness REAL NOT NULL,
    creativity REAL NOT NULL,
    digital_intensity REAL NOT NULL,
    human_interaction REAL NOT NULL,
    direct_ai_rate REAL NOT NULL,
    routine_match_rate REAL NOT NULL,
    creative_match_rate REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS career_transitions (
    source_category TEXT PRIMARY KEY,
    target_role TEXT NOT NULL,
    transition_type TEXT NOT NULL,
    readiness_score REAL NOT NULL,
    shared_keywords TEXT NOT NULL,
    gap_skills TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    db_path = path or get_database_path()
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_schema(path: Path | None = None) -> Path:
    db_path = path or get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as connection:
        connection.executescript(SCHEMA)
    return db_path


def table_count(path: Path | None = None, table: str = "category_stats") -> int:
    if table not in TABLES:
        raise ValueError(f"Unsupported table: {table}")
    with connect(path) as connection:
        row = connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
    return int(row["count"])


def read_table(table: str, path: Path | None = None) -> pd.DataFrame:
    if table not in TABLES:
        raise ValueError(f"Unsupported table: {table}")
    with connect(path) as connection:
        return pd.read_sql_query(f"SELECT * FROM {table}", connection)
