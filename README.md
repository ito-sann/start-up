# 行政書士向けスタートアップイベント集約システム

47都道府県のスタートアップ支援施設のイベントを自動収集し、「補助金ニーズのある起業家」と出会えるイベントを効率的に発見するための個人専用ツールです。

## 特徴

- 🔍 **自動イベント収集**: connpass、Peatix、Doorkeeperからスタートアップ関連イベントを自動収集
- ⏰ **2ヶ月ルール**: 2ヶ月以上イベントがない施設を自動で休眠リストへ振り分け
- 📊 **スコアリング**: ピッチ・交流会など、人脈形成に有効なイベントを高スコア化
- 🆕 **2026年新施設対応**: 新規オープン施設を先行監視

## クイックスタート

### 1. 依存パッケージのインストール

```bash
cd startup-event-aggregator
pip install -r requirements.txt
```

### 2. データベースの初期化

```bash
python -c "from core.database import init_database, load_initial_facilities; init_database(); load_initial_facilities()"
```

### 3. アプリケーションの起動

```bash
streamlit run app.py
```

ブラウザで http://localhost:8501 を開きます。

## イベント収集

### 手動で今すぐ収集

```bash
python core/scheduler.py --now
```

### 自動スケジューラー（デーモン）

```bash
python core/scheduler.py --daemon
```

- 日次イベント収集: 毎朝 06:00
- 週次休眠チェック: 毎週月曜 09:00

## ディレクトリ構成

```
startup-event-aggregator/
├── app.py                    # Streamlitメインアプリ
├── config.py                 # 設定ファイル
├── requirements.txt          # 依存パッケージ
├── data/
│   ├── facilities.json       # 施設マスタデータ
│   ├── new_facilities_2026.json  # 2026年新規施設
│   └── events.db             # SQLiteデータベース
├── scrapers/
│   ├── connpass.py           # connpass API
│   ├── peatix.py             # Peatixスクレイピング
│   └── doorkeeper.py         # Doorkeeperスクレイピング
├── core/
│   ├── database.py           # DB操作
│   ├── scorer.py             # スコアリングロジック
│   ├── dormant_checker.py    # 2ヶ月ルール判定
│   └── scheduler.py          # 自動実行スケジューラ
└── docs/
    └── tips_for_gyoseishoshi.md  # 行政書士向けTips
```

## スコアリング基準

| イベントタイプ | スコア | 備考 |
|----------------|--------|------|
| ピッチイベント | 100 | 起業家と直接対話可能 |
| 交流会・ネットワーキング | 90 | 名刺交換の機会あり |
| ワークショップ | 70 | 実践的な関係構築 |
| セミナー・講演会 | 50 | 情報収集メイン |
| オンラインイベント | 30 | 対面より効果低 |

### 高プライオリティキーワード

- ピッチ、pitch、デモデイ、demo day
- 交流会、ネットワーキング、networking、懇親会
- 起業家、スタートアップ、startup
- 補助金、助成金、資金調達

## 2ヶ月ルール

施設のイベント開催状況を監視し、自動で以下のステータスに分類します：

- **active**: 直近2ヶ月以内にイベント開催あり
- **dormant**: 2ヶ月以上イベント開催なし（休眠）
- **new**: 新規施設（イベント実績なし、監視中）
- **closed**: 閉鎖済み

## カスタマイズ

### 施設の追加

`data/facilities.json` を編集して施設を追加できます：

```json
{
  "id": "unique_id",
  "name": "施設名",
  "prefecture": "東京都",
  "city": "渋谷区",
  "website": "https://example.com",
  "status": "active"
}
```

### スコアリング調整

`config.py` の `EVENT_TYPE_SCORES` と `HIGH_PRIORITY_KEYWORDS` を編集してカスタマイズできます。

## ライセンス

個人使用限定
