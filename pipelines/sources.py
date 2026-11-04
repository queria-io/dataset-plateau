"""PLATEAU の都市ごとの CityGML の一覧を取る。

PLATEAU VIEW のデータカタログ API が、都市ごとに最新の CityGML の zip の URL・年度・
製品仕様書の版・含む地物と、G空間情報センターのデータセットのページを返す。
建物（bldg）を含む都市だけを使う。

出力: data/plateau/sources.ndjson（1 行 = 1 都市）
"""

import json
import logging
from pathlib import Path

from shared.fetch import fetch, write_atomic

logger = logging.getLogger("pipelines")

CATALOG = "https://api.plateauview.mlit.go.jp/datacatalog/plateau-datasets"
USER_AGENT = "dataset-plateau (+https://github.com/queria-io/dataset-plateau)"
SOURCES = Path("data/plateau/sources.ndjson")


def is_city(city: dict) -> bool:
    """建物を含む都市。東京都のサンプルデータ（竹芝モデル、13999）は港区と重なるので除く。"""
    return "bldg" in city["feature_types"] and "サンプル" not in city["city"]


def to_source(city: dict) -> dict:
    return {
        "city_code": city["city_code"],
        "pref_code": city["pref_code"],
        "pref": city["pref"],
        "city": city["city"],
        "year": city["year"],
        "spec": city["spec"],
        "file": Path(city["url"]).name,
        "zip_url": city["url"],
        "size": city["file_size"],
        "page_url": city["gspatialjp_dataset_url"],
    }


def list_sources() -> list[dict]:
    catalog = json.loads(fetch(CATALOG, user_agent=USER_AGENT, timeout=300))
    sources = sorted(
        (to_source(c) for c in catalog["citygml"] if is_city(c)),
        key=lambda s: s["city_code"],
    )
    SOURCES.parent.mkdir(parents=True, exist_ok=True)
    write_atomic(SOURCES, "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in sources))
    logger.info("  建物のある都市: %d", len(sources))
    return sources
