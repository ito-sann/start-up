# スプレッドシートデータインポート手順

## 概要
GoogleスプレッドシートのデータをCSVファイルとしてダウンロードし、システムに取り込む手順です。Google APIの設定は不要で、無料で実施できます。

## 手順

### 1. スプレッドシートをCSVとしてダウンロード
1. インポートしたいGoogleスプレッドシートを開く
2. メニューの「ファイル」→「ダウンロード」→「カンマ区切り形式 (.csv)」を選択
3. ダウンロードされたファイル（例: `スタートアップ支援施設一覧.csv`）を確認

### 2. ファイルの配置
1. ダウンロードしたファイルを `import_source.csv` という名前に変更
2. 以下の `data` ディレクトリに配置
   ```
   /Users/itouyuutarou/.gemini/antigravity/scratch/startup-event-aggregator/data/import_source.csv
   ```

### 3. インポートスクリプトの実行
ターミナルで以下のコマンドを実行します：

```bash
cd /Users/itouyuutarou/.gemini/antigravity/scratch/startup-event-aggregator
python3 scrapers/google_sheets_importer.py
```

### 4. 結果の確認
成功すると以下のように表示されます：

```
=== CSVインポート開始: .../data/import_source.csv ===

✓ 140 行を読み込みました
  [北海道] SAPPORO Incubation Hub DRIVE (https://...)
  [東京都] Startup Hub Tokyo (https://...)
  ...

=== データベースへの登録 ===

完了: 新規追加 XX 件 / スキップ(重複) YY 件
```

## 注意点
- **CSVファイル名**: 必ず `import_source.csv` にしてください。
- **データ更新**: 新しいデータを反映させたい場合は、再度ダウンロードしてファイルを上書き配置し、スクリプトを実行してください。
