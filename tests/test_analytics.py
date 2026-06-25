import unittest

import pandas as pd

from scripts.prepare_real_dataset import classify_jobs, parse_salary
from scripts.init_database import build_task_metrics
from src.analytics import cluster_market_segments, forecast_employment_structure, salary_premium


class AnalyticsTests(unittest.TestCase):
    def test_salary_parser_handles_months_and_daily_rates(self):
        self.assertEqual(parse_salary("20-35K·16薪"), (20.0, 35.0, 36.67, 16))
        minimum, maximum, monthly, months = parse_salary("200-300元/天")
        self.assertEqual(months, 12)
        self.assertAlmostEqual(minimum, 4.35)
        self.assertAlmostEqual(maximum, 6.52)
        self.assertAlmostEqual(monthly, 5.44)

    def test_job_classifier_prioritizes_ai_jobs(self):
        frame = pd.DataFrame(
            {
                "title": ["大模型算法工程师", "Python后端开发", "财务会计"],
                "keywords": ["机器学习, PyTorch", "Django", "总账"],
                "industry": ["人工智能", "计算机软件", "企业服务"],
            }
        )
        self.assertEqual(classify_jobs(frame).tolist(), ["AI与算法", "软件开发", "财务金融"])

    def test_cluster_output_has_coordinates_and_names(self):
        frame = pd.DataFrame(
            {
                "category": [f"类别{i}" for i in range(8)],
                "sample_count": [900, 850, 700, 650, 500, 450, 350, 300],
                "median_salary": [6, 8, 10, 12, 18, 20, 22, 25],
                "ai_share": [0.2, 0.5, 1.0, 1.5, 5, 10, 30, 65],
                "bachelor_share": [10, 15, 20, 30, 45, 55, 70, 85],
                "experienced_share": [20, 25, 35, 40, 50, 60, 70, 80],
            }
        )
        result = cluster_market_segments(frame, n_clusters=4)
        self.assertFalse(result[["pca_x", "pca_y"]].isna().any().any())
        self.assertEqual(result["cluster_name"].nunique(), 4)

    def test_salary_premium_uses_observed_medians(self):
        frame = pd.DataFrame(
            {"avg_salary_k": [10, 12, 20, 24], "ai_related": [0, 0, 1, 1]}
        )
        self.assertAlmostEqual(salary_premium(frame), 100.0)

    def test_employment_forecast_preserves_sector_total_and_reports_backtest(self):
        years = list(range(2010, 2026))
        frame = pd.DataFrame(
            {
                "year": years,
                "agriculture_share": [30 - 0.5 * (year - 2010) for year in years],
                "industry_share": [30 + 0.1 * (year - 2010) for year in years],
                "services_share": [40 + 0.4 * (year - 2010) for year in years],
            }
        )
        result = forecast_employment_structure(frame, forecast_end=2030)
        predicted = result[result["status"] == "预测"]
        totals = predicted.groupby("year")["share"].sum()
        self.assertTrue((totals.sub(100).abs() < 0.01).all())
        self.assertEqual(predicted["year"].min(), 2026)
        self.assertEqual(predicted["year"].max(), 2030)
        self.assertTrue((predicted["lower"] <= predicted["share"]).all())
        self.assertTrue((predicted["upper"] >= predicted["share"]).all())
        self.assertTrue((result["backtest_mae"] >= 0).all())

    def test_task_proxies_are_bounded_and_ai_text_increases_exposure(self):
        frame = pd.DataFrame(
            {
                "category": ["AI与算法", "AI与算法", "服务物流", "服务物流"],
                "title": ["大模型算法工程师", "机器学习开发", "仓库分拣员", "物流打包员"],
                "keywords": ["Python,AI,模型", "算法,数据", "盘点,分拣", "打包,仓库"],
                "industry": ["人工智能", "计算机软件", "物流/仓储", "物流/仓储"],
                "ai_related": [1, 1, 0, 0],
            }
        )
        result = build_task_metrics(frame).set_index("category")
        score_columns = [
            "ai_exposure", "repetitiveness", "creativity",
            "digital_intensity", "human_interaction",
        ]
        self.assertTrue(result[score_columns].map(lambda value: 0 <= value <= 100).all().all())
        self.assertGreater(result.loc["AI与算法", "ai_exposure"], result.loc["服务物流", "ai_exposure"])


if __name__ == "__main__":
    unittest.main()
