# 設定ファイル
from pathlib import Path
from datetime import timedelta

# パス設定
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "events.db"

# スクレイピング設定
SCRAPE_INTERVAL_HOURS = 24  # 1日1回
REQUEST_DELAY_SECONDS = 2   # リクエスト間隔

# 2ヶ月ルール設定
DORMANT_THRESHOLD_DAYS = 60  # 休眠判定の閾値

# スコアリング設定
EVENT_TYPE_SCORES = {
    "pitch": 100,       # ピッチイベント
    "networking": 90,   # 交流会・ネットワーキング
    "workshop": 70,     # ワークショップ
    "seminar": 50,      # セミナー・講演会
    "online": 30,       # オンラインイベント
    "other": 40,        # その他
}

# 高プライオリティキーワード
HIGH_PRIORITY_KEYWORDS = [
    # ピッチ関連
    "ピッチ", "pitch", "デモデイ", "demo day", "demoday",
    # 交流会関連
    "交流会", "ネットワーキング", "networking", "懇親会", 
    "ミートアップ", "meetup", "meet up",
    # 起業家関連
    "起業家", "スタートアップ", "startup", "アントレ",
    # 補助金関連
    "補助金", "助成金", "資金調達", "ファンディング",
]

# 除外キーワード（補助金ニーズが低いイベント）
EXCLUDE_KEYWORDS = [
    "初心者向けプログラミング", "もくもく会", 
    "読書会", "LT大会",
]

# connpass API設定
CONNPASS_API_URL = "https://connpass.com/api/v1/event/"
CONNPASS_SEARCH_KEYWORDS = [
    "スタートアップ", "起業", "ピッチ", "資金調達",
    "ベンチャー", "創業", "補助金",
]

# 地域設定
REGIONS = {
    "hokkaido": ["北海道"],
    "tohoku": ["青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県"],
    "kanto": ["茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県"],
    "chubu": ["新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県", "静岡県", "愛知県"],
    "kinki": ["三重県", "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県"],
    "chugoku": ["鳥取県", "島根県", "岡山県", "広島県", "山口県"],
    "shikoku": ["徳島県", "香川県", "愛媛県", "高知県"],
    "kyushu": ["福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"],
}
