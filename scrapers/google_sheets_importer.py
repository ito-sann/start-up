"""
ローカルCSVからスタートアップ支援施設データをインポートするモジュール

使用方法:
1. スプレッドシートを「ファイル」→「ダウンロード」→「カンマ区切り形式 (.csv)」で保存
2. ファイル名を `import_source.csv` に変更して `data/` ディレクトリに配置
3. このスクリプトを実行
"""

import csv
import re
import os
import sys
from typing import List, Dict
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.database import insert_facility, get_facility_by_url

# インポート元ファイル設定
CSV_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data',
    'import_source.csv'
)

# 都道府県リスト（正規化用マップ）
PREFECTURE_MAP = {
    '北海道': '北海道',
    '青森': '青森県', '青森県': '青森県',
    '岩手': '岩手県', '岩手県': '岩手県',
    '宮城': '宮城県', '宮城県': '宮城県',
    '秋田': '秋田県', '秋田県': '秋田県',
    '山形': '山形県', '山形県': '山形県',
    '福島': '福島県', '福島県': '福島県',
    '茨城': '茨城県', '茨城県': '茨城県',
    '栃木': '栃木県', '栃木県': '栃木県',
    '群馬': '群馬県', '群馬県': '群馬県',
    '埼玉': '埼玉県', '埼玉県': '埼玉県',
    '千葉': '千葉県', '千葉県': '千葉県',
    '東京': '東京都', '東京都': '東京都',
    '神奈川': '神奈川県', '神奈川県': '神奈川県',
    '新潟': '新潟県', '新潟県': '新潟県',
    '富山': '富山県', '富山県': '富山県',
    '石川': '石川県', '石川県': '石川県',
    '福井': '福井県', '福井県': '福井県',
    '山梨': '山梨県', '山梨県': '山梨県',
    '長野': '長野県', '長野県': '長野県',
    '岐阜': '岐阜県', '岐阜県': '岐阜県',
    '静岡': '静岡県', '静岡県': '静岡県',
    '愛知': '愛知県', '愛知県': '愛知県',
    '三重': '三重県', '三重県': '三重県',
    '滋賀': '滋賀県', '滋賀県': '滋賀県',
    '京都': '京都府', '京都府': '京都府',
    '大阪': '大阪府', '大阪府': '大阪府',
    '兵庫': '兵庫県', '兵庫県': '兵庫県',
    '奈良': '奈良県', '奈良県': '奈良県',
    '和歌山': '和歌山県', '和歌山県': '和歌山県',
    '鳥取': '鳥取県', '鳥取県': '鳥取県',
    '島根': '島根県', '島根県': '島根県',
    '岡山': '岡山県', '岡山県': '岡山県',
    '広島': '広島県', '広島県': '広島県',
    '山口': '山口県', '山口県': '山口県',
    '徳島': '徳島県', '徳島県': '徳島県',
    '香川': '香川県', '香川県': '香川県',
    '愛媛': '愛媛県', '愛媛県': '愛媛県',
    '高知': '高知県', '高知県': '高知県',
    '福岡': '福岡県', '福岡県': '福岡県',
    '佐賀': '佐賀県', '佐賀県': '佐賀県',
    '長崎': '長崎県', '長崎県': '長崎県',
    '熊本': '熊本県', '熊本県': '熊本県',
    '大分': '大分県', '大分県': '大分県',
    '宮崎': '宮崎県', '宮崎県': '宮崎県',
    '鹿児島': '鹿児島県', '鹿児島県': '鹿児島県',
    '沖縄': '沖縄県', '沖縄県': '沖縄県'
}

def is_url(text: str) -> bool:
    """文字列がURLかどうかを判定"""
    if not text:
        return False
    url_pattern = re.compile(r'^https?://')
    return bool(url_pattern.match(text.strip()))

def extract_facility_name_from_url(url: str) -> str:
    """URLから施設名を推測（ドメイン名ベース）"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        # ドメインの最初の部分を暫定的な名前とする
        name = domain.split('.')[0].title()
        return name
    except:
        return url[:20]

def parse_csv_data(rows: List[List[str]]) -> List[Dict]:
    """階層的リストCSVをパース"""
    facilities = []
    current_region = None
    current_prefecture = None
    current_priority = False
    
    for row_idx, row in enumerate(rows):
        if not row: continue
        
        # 列データの取得（インデックスエラー回避）
        col_a = row[0].strip() if len(row) > 0 else ""
        col_b = row[1].strip() if len(row) > 1 else ""
        
        # A列: 優先度または地域
        if col_a == "★":
            current_priority = True
        elif col_a and not is_url(col_a):
            current_region = col_a
            current_priority = False
            
        # B列: 都道府県判定（MAPにあるキーと一致するか）
        if col_b in PREFECTURE_MAP:
            current_prefecture = PREFECTURE_MAP[col_b]
            continue
            
        # B列: URL判定（施設データ）
        if is_url(col_b):
            facility_name = extract_facility_name_from_url(col_b)
            
            # 都道府県が未設定の場合のフォールバック
            prefecture_to_use = current_prefecture or '不明'
            
            facility_data = {
                'id': f"csv_{row_idx}",
                'name': facility_name,
                'prefecture': prefecture_to_use,
                'website': col_b,
                'region': current_region,
                'priority': current_priority,
                'source': 'csv_import'
            }
            facilities.append(facility_data)
            print(f"  [{prefecture_to_use}] {facility_name} ({col_b})")

    return facilities

def import_from_csv() -> List[Dict]:
    """CSVからインポート"""
    print(f"\n=== CSVインポート開始: {CSV_FILE_PATH} ===\n")
    
    if not os.path.exists(CSV_FILE_PATH):
        print(f"⚠ ファイルが見つかりません: {CSV_FILE_PATH}")
        print("スプレッドシートをCSV形式でダウンロードし、上記パスに配置してください。")
        return []
        
    try:
        with open(CSV_FILE_PATH, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
            
        print(f"✓ {len(rows)} 行を読み込みました")
        facilities = parse_csv_data(rows)
        return facilities
    except Exception as e:
        print(f"✗ CSV読み込みエラー: {e}")
        return []

def merge_to_database(facilities: List[Dict]) -> Dict:
    """DBマージ"""
    stats = {'added': 0, 'skipped': 0}
    
    for facility in facilities:
        existing = get_facility_by_url(facility['website'])
        if existing:
            stats['skipped'] += 1
        else:
            if insert_facility(facility):
                stats['added'] += 1
                
    return stats

def main():
    facilities = import_from_csv()
    if facilities:
        print(f"\n=== データベースへの登録 ===\n")
        stats = merge_to_database(facilities)
        print(f"完了: 新規追加 {stats['added']} 件 / スキップ(重複) {stats['skipped']} 件")

if __name__ == '__main__':
    main()
