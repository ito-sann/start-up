#!/usr/bin/env python3
"""
中小機構（SMRJ）インキュベーション施設スクレイパー（Playwright版）
https://www.smrj.go.jp/incubation/ から施設情報を収集
"""

import asyncio
import re
import sys
import os
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from core.database import init_database, insert_facility, get_facility_by_url

# 中小機構インキュベーション施設一覧ページ
BASE_URL = "https://www.smrj.go.jp/incubation/"

# 手動でまとめた中小機構インキュベーション施設リスト
# （サイトからの動的取得が困難なため、確認済みデータを使用）
SMRJ_FACILITIES = [
    {"name": "北大ビジネス・スプリング", "prefecture": "北海道", "city": "札幌市", "url": "https://www.smrj.go.jp/incubation/ho-bis/index.html", "type": "大学連携型"},
    {"name": "東北大学連携ビジネスインキュベータ", "prefecture": "宮城県", "city": "仙台市", "url": "https://www.smrj.go.jp/incubation/t-biz/index.html", "type": "大学連携型"},
    {"name": "東大柏ベンチャープラザ", "prefecture": "千葉県", "city": "柏市", "url": "https://www.smrj.go.jp/incubation/tkv/index.html", "type": "大学連携型"},
    {"name": "Science Tokyo 横浜ベンチャープラザ", "prefecture": "神奈川県", "city": "横浜市", "url": "https://www.smrj.go.jp/incubation/yvp/index.html", "type": "大学連携型"},
    {"name": "慶應藤沢イノベーションビレッジ", "prefecture": "神奈川県", "city": "藤沢市", "url": "https://www.smrj.go.jp/incubation/sfc-iv/index.html", "type": "大学連携型"},
    {"name": "ベンチャープラザ船橋", "prefecture": "千葉県", "city": "船橋市", "url": "https://www.smrj.go.jp/incubation/vpf/index.html", "type": "新事業創出型"},
    {"name": "千葉大亥鼻イノベーションプラザ", "prefecture": "千葉県", "city": "千葉市", "url": "https://www.smrj.go.jp/incubation/ciip/index.html", "type": "大学連携型"},
    {"name": "和光理研インキュベーションプラザ", "prefecture": "埼玉県", "city": "和光市", "url": "https://www.smrj.go.jp/incubation/wrip/index.html", "type": "新事業創出型"},
    {"name": "農工大・多摩小金井ベンチャーポート", "prefecture": "東京都", "city": "小金井市", "url": "https://www.smrj.go.jp/incubation/tama-koganei/index.html", "type": "大学連携型"},
    {"name": "浜松イノベーションキューブ", "prefecture": "静岡県", "city": "浜松市", "url": "https://www.smrj.go.jp/incubation/hi-cube/index.html", "type": "新事業創出型"},
    {"name": "クリエイション・コア名古屋", "prefecture": "愛知県", "city": "名古屋市", "url": "https://www.smrj.go.jp/incubation/nagoya/index.html", "type": "新事業創出型"},
    {"name": "名古屋医工連携インキュベータ", "prefecture": "愛知県", "city": "名古屋市", "url": "https://www.smrj.go.jp/incubation/nalic/index.html", "type": "大学連携型"},
    {"name": "いしかわ大学連携インキュベータ", "prefecture": "石川県", "city": "野々市市", "url": "https://www.smrj.go.jp/incubation/i-bird/index.html", "type": "大学連携型"},
    {"name": "立命館大学BKCインキュベータ", "prefecture": "滋賀県", "city": "草津市", "url": "https://www.smrj.go.jp/incubation/rits-bkci/index.html", "type": "大学連携型"},
    {"name": "D-egg", "prefecture": "京都府", "city": "京田辺市", "url": "https://www.smrj.go.jp/incubation/d-egg/index.html", "type": "大学連携型"},
    {"name": "京大桂ベンチャープラザ", "prefecture": "京都府", "city": "京都市", "url": "https://www.smrj.go.jp/incubation/kkvp/index.html", "type": "新事業創出型"},
    {"name": "クリエイション・コア京都御車", "prefecture": "京都府", "city": "京都市", "url": "https://www.smrj.go.jp/incubation/cckm/index.html", "type": "新事業創出型"},
    {"name": "神戸医療機器開発センター", "prefecture": "兵庫県", "city": "神戸市", "url": "https://www.smrj.go.jp/incubation/meddec/index.html", "type": "新事業創出型"},
    {"name": "神戸健康産業開発センター", "prefecture": "兵庫県", "city": "神戸市", "url": "https://www.smrj.go.jp/incubation/hi-dec/index.html", "type": "新事業創出型"},
    {"name": "彩都バイオインキュベータ", "prefecture": "大阪府", "city": "茨木市", "url": "https://www.bs-capital.co.jp/saito/incu1.html", "type": "大学連携型"},
    {"name": "彩都バイオイノベーションセンター", "prefecture": "大阪府", "city": "茨木市", "url": "https://www.bs-capital.co.jp/saito/inno1.html", "type": "新事業創出型"},
    {"name": "クリエイション・コア東大阪", "prefecture": "大阪府", "city": "東大阪市", "url": "https://www.smrj.go.jp/incubation/higashi-osaka/index.html", "type": "新事業創出型"},
    {"name": "岡山大インキュベータ", "prefecture": "岡山県", "city": "岡山市", "url": "https://www.smrj.go.jp/incubation/od-plus/index.html", "type": "大学連携型"},
    {"name": "福岡システムLSI総合開発センター", "prefecture": "福岡県", "city": "福岡市", "url": "https://lsi.ist.or.jp/", "type": "大学連携型"},
    {"name": "クリエイション・コア福岡", "prefecture": "福岡県", "city": "筑紫野市", "url": "https://www.smrj.go.jp/incubation/fukuoka/index.html", "type": "新事業創出型"},
    {"name": "くまもと大学連携インキュベータ", "prefecture": "熊本県", "city": "熊本市", "url": "https://www.smrj.go.jp/incubation/kdri/index.html", "type": "大学連携型"},
    {"name": "ながさき出島インキュベータ", "prefecture": "長崎県", "city": "長崎市", "url": "https://www.smrj.go.jp/incubation/d-flag/index.html", "type": "大学連携型"},
]


def import_smrj_facilities() -> Dict:
    """中小機構施設データをデータベースにインポート"""
    init_database()
    
    print(f"\n{'='*60}")
    print("🏢 中小機構インキュベーション施設インポート")
    print(f"{'='*60}\n")
    
    stats = {'added': 0, 'skipped': 0}
    
    for i, f in enumerate(SMRJ_FACILITIES):
        facility = {
            'id': f"smrj_{i + 1}",
            'name': f['name'],
            'prefecture': f['prefecture'],
            'city': f['city'],
            'website': f['url'],
            'notes': f"中小機構インキュベーション施設 ({f['type']})",
            'status': 'new'
        }
        
        existing = get_facility_by_url(facility['website'])
        if existing:
            print(f"  ⏭ [{f['prefecture']}] {f['name']} (既存)")
            stats['skipped'] += 1
        else:
            if insert_facility(facility):
                print(f"  ✅ [{f['prefecture']}] {f['name']} (追加)")
                stats['added'] += 1
    
    print(f"\n{'='*60}")
    print(f"📈 結果: 追加 {stats['added']} 件 / スキップ {stats['skipped']} 件")
    print(f"{'='*60}\n")
    
    return stats


def main():
    """メイン実行"""
    import_smrj_facilities()


if __name__ == "__main__":
    main()
