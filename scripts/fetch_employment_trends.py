from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "china_employment_structure.csv"
API_ROOT = "https://api.worldbank.org/v2/country/CHN/indicator"
INDICATORS = {
    "agriculture_share": "SL.AGR.EMPL.ZS",
    "industry_share": "SL.IND.EMPL.ZS",
    "services_share": "SL.SRV.EMPL.ZS",
}


def fetch_indicator(indicator: str, retries: int = 3) -> dict[int, float]:
    url = f"{API_ROOT}/{indicator}?format=json&per_page=100"
    request = urllib.request.Request(url, headers={"User-Agent": "ai-career-viz/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
            return {
                int(item["date"]): float(item["value"])
                for item in payload[1]
                if item.get("value") is not None
            }
        except (urllib.error.URLError, TimeoutError, ValueError, IndexError):
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
    return {}


def main() -> None:
    series = {name: fetch_indicator(code) for name, code in INDICATORS.items()}
    common_years = sorted(set.intersection(*(set(values) for values in series.values())))
    frame = pd.DataFrame(
        {
            "year": common_years,
            **{name: [values[year] for year in common_years] for name, values in series.items()},
        }
    )
    frame["total"] = frame[list(INDICATORS)].sum(axis=1)
    if not frame["total"].between(99.0, 101.0).all():
        raise ValueError("Employment sector shares do not sum to approximately 100%.")
    frame = frame.drop(columns="total").round(6)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(OUTPUT, index=False)
    print(f"Saved {len(frame)} annual observations ({frame.year.min()}-{frame.year.max()}) to {OUTPUT}")


if __name__ == "__main__":
    main()
