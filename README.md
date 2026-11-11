# PLATEAU 3D 都市モデルの建物

国土交通省の PLATEAU（3D 都市モデル）の建物を、SQL で集計・地図表示できるテーブルにしたデータセットです。1 行が 1 棟で、外形（LOD0）・計測高さ・地上と地下の階数・用途・構造・建築年・延べ面積・住所（町丁目まで）を持ちます。建物ごとの浸水深や土砂災害警戒区域も別のテーブルに持ちます。

外形の上の代表点から、国勢調査の小地域コード（e_stat）、町字 ID（japan_address_code）、3 次メッシュコードを付けているため、人口や地価など地域の数字と結合できます。

## 出典と利用条件

国土交通省と各地方公共団体が [G空間情報センター](https://www.geospatial.jp/ckan/dataset/plateau) で公開している「3D都市モデル（Project PLATEAU）」を加工しています。市区町村ごとの zip に、3 次メッシュごとの CityGML が入っています。

- [PLATEAU のサイトポリシー](https://www.mlit.go.jp/plateau/site-policy/)にしたがって、使うときは出典と、加工したものであることを明記してください。市区町村ごとのデータセットのページ URL は `bldg.source` の `page_url` にあります

## テーブル

| テーブル | 内容 |
| --- | --- |
| `bldg.building` | 1 行が 1 棟。外形（LOD0）、計測高さ、階数、用途、構造、建築年、延べ面積、住所（町丁目まで）。代表点の小地域コード・町字 ID・3 次メッシュコード |
| `bldg.building_risk` | 1 行が 1 棟の 1 想定。洪水・津波・高潮・内水の浸水深とランク、土砂災害警戒区域 |
| `bldg.source` | 取り込んだ市区町村のデータ。年度・製品仕様書のバージョン・出典のページ URL |

## 使い方

日野市で、想定最大規模の洪水で 0.5m 以上浸水する建物を用途ごとに数える:

```sql
SELECT b.usage, count(DISTINCT b.gml_id) AS buildings
FROM plateau.bldg.building b
JOIN plateau.bldg.building_risk r USING (gml_id)
WHERE b.city_code = '13212'
  AND r.hazard = '洪水' AND r.scale LIKE 'L2%' AND r.depth >= 0.5
GROUP BY b.usage
ORDER BY buildings DESC;
```

外形を `measured_height` で押し出すと LOD1 の立体になります。屋根の形（LOD2）は持ちません。`gml_id` は PLATEAU が配る 3D Tiles・MVT の地物と同じ値で、PLATEAU の表示用データと結合できます。

## 収録範囲の注意

- PLATEAU が整備した市区町村（2026 年 11 月時点で 305）だけを収録しています。年度は市区町村ごとに違い（2020〜2025 年度）、`bldg.source` に市区町村ごとの年度があります
- どの項目が入っているかは市区町村によって違います。属性の多くは都市計画基礎調査から来ていて、用途・高さはほぼすべての市区町村にあり、住所・建築年・延べ面積・構造は一部にしかありません
- 住所は町丁目まで（「東京都日野市旭が丘一丁目」）で、番地は入っていません
- 原典が不明を表すのに使う値（計測高さ・面積の -9999、階数の 9999、建築年・調査年の 1 など）は NULL にしています
- 外形は LOD0 の平面の形です。原典に LOD0 がないときは LOD1 の立体の底面を使っています
- `building_risk` の洪水は、河川（`description`）と想定の規模（`scale`：計画規模・想定最大規模）ごとに 1 行あり、同じ建物に何行も付きます。津波・高潮・内水も想定ごとに 1 行です。土砂災害は、建物が入る区域の種類（`description`：急傾斜地の崩壊など）と区域（`area_type`：警戒区域・特別警戒区域）を持ちます
- `building_risk` に行がない建物は「浸水しない」とは限りません。その市区町村のデータに想定が載っていないことがあります

## 変換方法

市区町村の一覧と zip の URL は PLATEAU VIEW のデータカタログ API（`https://api.plateauview.mlit.go.jp/datacatalog/plateau-datasets`）から取得します。zip は HTTP の Range で読み、建物の CityGML（`udx/bldg/*.gml`）と符号表（`codelists/*.xml`）だけを取得します。写真の貼り付けや地形は読みません。

CityGML は lxml で建物ごとに読み、用途などの符号を同じ zip の符号表で名前に変換します。座標は緯度・経度の順なので経度・緯度に変換します。製品仕様書のバージョンによって名前の違う要素（3.x までの `BuildingRiverFloodingRiskAttribute` など）は両方読みます。

市区町村のデータは 3 次メッシュの単位で作られていて、境のメッシュに隣の市区町村の建物も含みます。同じ `gml_id` の建物は 1 つにし、隣の市区町村が自分のデータを持っているときはそちらを使います（`models/work/building_key.sql`）。小地域と町字は、Queria の公開データセット e_stat と japan_address_code の形に代表点（`ST_PointOnSurface`）を当てて付けます。

Parquet の名前は zip の名前から作ります。zip の名前には年度とバージョンが入るため、原典が作り直されると新しい名前になり、その市区町村だけを取得し直します。

## ビルド

```bash
git submodule update --init
uv sync
scripts/build.sh   # fdl checkout → python main.py → fdl commit → fdl push
```

原典は市区町村ごとに不定期に更新されます。`.github/workflows/check.yml` が毎週カタログと公開中の `bldg.source` を比較し、変わった市区町村があれば通知します。取り込みは自動では実行せず、通知を受けてから `scripts/build.sh` を実行します。
