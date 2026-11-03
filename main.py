"""PLATEAU 3D 都市モデルの建物のパイプライン。

1. list: データカタログ API から、建物を含む都市の CityGML の zip の一覧を取る
2. convert: zip の中の建物を読み、都市ごとに 1 棟 1 行の Parquet にする
3. dbt: 都市をまたいで重なる建物を 1 つにし、小地域・町字・メッシュを付ける

Parquet の名前は zip の名前から作る。zip の名前には年度と版が入るので、原典が作り直されると
新しい名前になる。Parquet が既にある都市は取り直さない。
"""

import logging
from multiprocessing import Pool
from pathlib import Path

from dbt.cli.main import dbtRunner

from pipelines.convert import convert
from pipelines.sources import list_sources

# dbt を読み込むとルートロガーが先に設定されるので、force で上書きする
logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
logger = logging.getLogger("pipelines")

DATA = Path("data/plateau")


def outputs(source: dict) -> tuple[Path, Path]:
    name = f"{Path(source['zip_url']).stem}.parquet"
    return DATA / "building" / name, DATA / "building_risk" / name


def convert_one(source: dict) -> tuple[dict, tuple[int, int] | str]:
    """変換した行数か、失敗したときはその理由を返す。

    lxml の例外はプロセスをまたいで渡せず、どの都市かも分からなくなるので、ここで文字にする。
    """
    try:
        return source, convert(source, *outputs(source))
    except Exception as e:  # noqa: BLE001
        return source, f"{type(e).__name__}: {e}"


def convert_all(sources: list[dict]) -> None:
    """Parquet の無い都市を変換する。今回の一覧に無い Parquet は消す。並列は都市単位。"""
    wanted = {path for s in sources for path in outputs(s)}
    for stale in {*DATA.glob("building/*.parquet"), *DATA.glob("building_risk/*.parquet")} - wanted:
        stale.unlink()
    todo = [s for s in sources if not all(p.exists() for p in outputs(s))]
    logger.info("  変換するのは %d 都市", len(todo))
    failed = []
    with Pool() as pool:
        for done, (source, result) in enumerate(pool.imap_unordered(convert_one, todo), 1):
            name = f"{source['city_code']} {source['city']}"
            if isinstance(result, str):
                failed.append(f"{name}: {result}")
                logger.error("  [%d/%d] %s: %s", done, len(todo), name, result)
            else:
                logger.info("  [%d/%d] %s: %d 棟、災害リスク %d 件", done, len(todo), name, *result)
    # 1 都市でも欠けたまま公開しない。済んだ都市の Parquet は残るので、直して流し直せば続きから回る
    if failed:
        raise SystemExit("変換に失敗した都市:\n" + "\n".join(failed))


def dbt_build():
    dbt = dbtRunner()
    for command in (["deps"], ["build"], ["docs", "generate"]):
        result = dbt.invoke(command)
        if not result.success:
            raise SystemExit(f"dbt {' '.join(command)} failed")


def main():
    logger.info("1/3: list (PLATEAU の都市)")
    sources = list_sources()

    logger.info("2/3: convert (CityGML → Parquet)")
    convert_all(sources)

    logger.info("3/3: dbt build")
    dbt_build()


if __name__ == "__main__":
    main()
