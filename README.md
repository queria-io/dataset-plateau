# dataset-plateau

国土交通省の PLATEAU（3D 都市モデル）の建物を Queria のカタログ（[data.queria.io](https://data.queria.io/)）へ取り込むデータセットです。

## データ出典

国土交通省と各地方公共団体が [G空間情報センター](https://www.geospatial.jp/ckan/dataset/plateau) で公開している「3D都市モデル（Project PLATEAU）」。市区町村ごとの zip に、3 次メッシュごとの CityGML が入っています。

使うときは、[PLATEAU のサイトポリシー](https://www.mlit.go.jp/plateau/site-policy/)にしたがって出典と、加工したものであることを書いてください。市区町村ごとのデータセットのページ URL は `bldg.source` にあります。

## 収録テーブル

| テーブル | 内容 |
| --- | --- |
| `bldg.building` | 1 行が 1 棟。外形（LOD0）、計測高さ、階数、用途、構造、建築年、延べ面積、住所（町丁目まで）。代表点の小地域コード・町字 ID・3 次メッシュコード |
| `bldg.building_risk` | 1 行が 1 棟 × 1 想定。洪水・津波・高潮・内水の浸水深とランク、土砂災害警戒区域 |
| `bldg.source` | 取り込んだ市区町村のデータ。年度・製品仕様書の版・出典のページ URL |

- PLATEAU が整備した市区町村だけを収録しています
- どの項目が入っているかは市区町村によって違います。用途・高さはほぼすべてにあり、住所・建築年・延べ面積・構造は一部にしかありません
- 外形を `measured_height` で押し出すと LOD1 の立体になります。屋根の形（LOD2）は持ちません。`gml_id` は PLATEAU が配る 3D Tiles の地物と同じ値です

```sql
-- 日野市で、想定最大規模の洪水で 0.5m 以上浸水する建物を用途ごとに数える
SELECT b.usage, count(DISTINCT b.gml_id) AS buildings
FROM plateau.bldg.building b
JOIN plateau.bldg.building_risk r USING (gml_id)
WHERE b.city_code = '13212'
  AND r.hazard = '洪水' AND r.scale LIKE 'L2%' AND r.depth >= 0.5
GROUP BY b.usage
ORDER BY buildings DESC;
```

## 変換のしかた

市区町村の一覧と zip の URL は PLATEAU VIEW のデータカタログ API（`https://api.plateauview.mlit.go.jp/datacatalog/plateau-datasets`）から取ります。zip は HTTP の Range で読み、建物の CityGML（`udx/bldg/*.gml`）と符号表（`codelists/*.xml`）だけを取ります。写真の貼り付けや地形は読みません。

CityGML は lxml で建物ごとに読み、用途などの符号を同じ zip の符号表で名前に直します。座標は緯度・経度の順なので経度・緯度に直します。製品仕様書の版によって名前の違う要素（3.x までの `BuildingRiverFloodingRiskAttribute` など）は両方読みます。

市区町村のデータは境のメッシュに隣の市区町村の建物も含みます。同じ `gml_id` の建物は 1 つにし、隣の市区町村が自分のデータを持っているときはそちらを使います（`models/work/building_key.sql`）。小地域と町字は、Queria の公開データセット e_stat と japan_address_code の形に代表点を当てて付けます。

Parquet の名前は zip の名前から作ります。zip の名前には年度と版が入るので、原典が作り直されると新しい名前になり、その市区町村だけを取り直します。

## ビルド

```bash
git submodule update --init
uv sync
scripts/build.sh   # queria sync -- python main.py
```

原典は市区町村ごとに不定期に更新されます。`.github/workflows/check.yml` が毎週カタログと公開中の `bldg.source` を比べ、変わった市区町村があれば知らせます。取り込みは自動では回さず、知らせを受けてから `scripts/build.sh` を流します。
