# dataset-plateau

Queria のデータセット `plateau`（PLATEAU 3D 都市モデルの建物）のリポジトリです。データセットの説明は [docs/index.md](docs/index.md) にあります。

## ビルド

```bash
git submodule update --init
uv sync
scripts/build.sh   # fdl checkout → python main.py → fdl commit → fdl push
```

原典は市区町村ごとに不定期に更新されます。`.github/workflows/check.yml` が毎週カタログと公開中の `bldg.source` を比較し、変わった市区町村があれば通知します。取り込みは自動では実行せず、通知を受けてから `scripts/build.sh` を実行します。
