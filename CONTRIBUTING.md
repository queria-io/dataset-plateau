# ビルドと更新

データセットの概要は [README.md](README.md) にあります。ここにはこのリポジトリでデータセットをビルド・更新する手順を書きます。

## ビルド

```bash
git clone https://github.com/queria-io/dataset-shared.git shared  # 更新は git -C shared pull
uv sync
scripts/build.sh   # fdl checkout → python main.py → fdl commit → fdl push
```

原典は市区町村ごとに不定期に更新されます。`.github/workflows/check.yml` が毎週カタログと公開中の `bldg.source` を比較し、変わった市区町村があれば通知します。取り込みは自動では実行せず、通知を受けてから `scripts/build.sh` を実行します。
