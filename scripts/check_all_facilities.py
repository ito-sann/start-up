#!/usr/bin/env python3
"""
全施設の活動状況をチェックし、データベースを更新するバッチスクリプト
3日に1回のスケジュール実行を想定
"""

import asyncio
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.activity_checker import SimpleActivityChecker
from core.database import get_all_facilities, update_facility_status, init_database


async def run_activity_check():
    """全施設の活動チェックを実行"""
    print(f"\n{'='*60}")
    print(f"🔍 活動状況チェック開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    # データベース初期化
    init_database()
    
    # 全施設取得
    facilities = get_all_facilities()
    total = len(facilities)
    
    if not facilities:
        print("⚠ チェック対象の施設がありません")
        return
    
    print(f"📊 チェック対象: {total} 施設\n")
    
    # チェッカー初期化
    checker = SimpleActivityChecker(threshold_days=60)
    
    # 結果カウンター
    stats = {
        'active': 0,
        'dormant': 0,
        'unknown': 0,
        'error': 0
    }
    
    # 全施設をチェック
    for i, facility in enumerate(facilities, 1):
        url = facility.get('website')
        name = facility.get('name', '')
        facility_id = facility.get('id')
        
        print(f"[{i}/{total}] ", end="")
        
        if not url:
            print(f"⚠ {name}: URLなし")
            stats['unknown'] += 1
            continue
        
        try:
            result = await checker.check_facility(url, name)
            
            status = result.get('status', 'unknown')
            stats[status] = stats.get(status, 0) + 1
            
            # ステータス更新
            if status in ['active', 'dormant']:
                update_facility_status(
                    facility_id,
                    status,
                    result.get('latest_date'),
                    result.get('reason')
                )
            
            # 結果表示
            emoji = "✅" if status == 'active' else "💤" if status == 'dormant' else "❓"
            print(f"{emoji} {name}: {result.get('reason', status)}")
            
        except Exception as e:
            print(f"✗ {name}: エラー - {e}")
            stats['error'] += 1
        
        # レート制限
        await asyncio.sleep(1.5)
    
    # サマリー表示
    print(f"\n{'='*60}")
    print(f"📈 チェック結果サマリー")
    print(f"{'='*60}")
    print(f"  ✅ アクティブ: {stats['active']} 施設")
    print(f"  💤 休眠: {stats['dormant']} 施設")
    print(f"  ❓ 不明: {stats['unknown']} 施設")
    print(f"  ✗ エラー: {stats['error']} 施設")
    print(f"{'='*60}\n")
    
    return stats


def main():
    """メイン実行"""
    asyncio.run(run_activity_check())


if __name__ == "__main__":
    main()
