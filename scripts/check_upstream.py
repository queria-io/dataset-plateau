"""公開中の plateau と PLATEAU のデータカタログを比べ、取り込み直しが要る市区町村を出す。

全国の取り込みは重いので、原典が変わったときにだけ流す。ここは確かめるだけで、
新しく載った・作り直された・消えた市区町村を 1 行ずつ出す（何も出なければ取り込まなくてよい）。
"""

import json
import os
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipelines.sources import CATALOG, USER_AGENT, is_city, to_source  # noqa: E402
from shared.fetch import fetch  # noqa: E402

PUBLISHED = "ducklake:https://data.queria.io/datasets/queria/plateau/ducklake.duckdb"


def published() -> dict[str, str]:
    c = duckdb.connect(config={"custom_user_agent": os.environ.get("QUERIA_USER_AGENT", "queria-build/check")})
    c.execute("INSTALL ducklake; LOAD ducklake; INSTALL httpfs; LOAD httpfs")
    c.execute(f"ATTACH '{PUBLISHED}' AS plateau (READ_ONLY)")
    return dict(c.execute("SELECT city_code, file FROM plateau.bldg.source").fetchall())


def upstream() -> dict[str, dict]:
    catalog = json.loads(fetch(CATALOG, user_agent=USER_AGENT, timeout=300))
    return {s["city_code"]: s for s in (to_source(c) for c in catalog["citygml"] if is_city(c))}


def main() -> None:
    old, new = published(), upstream()
    changes = [
        f"{code} {s['city']}（{s['year']} 年度）" for code, s in sorted(new.items()) if old.get(code) != s["file"]
    ] + [f"{code}（カタログから消えた）" for code in sorted(old.keys() - new.keys())]
    print("\n".join(changes))


if __name__ == "__main__":
    main()
