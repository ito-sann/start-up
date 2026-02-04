#!/usr/bin/env python3
"""
施設の活動状況を調査し、JSON形式でイベントデータを出力するスクリプト
GitHub PagesやAPIエンドポイントとして利用可能
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.advanced_activity_checker import AdvancedActivityChecker
from core.database import get_all_facilities, init_database


async def generate_event_data(output_file: str = None, limit: int = 10):
    """施設のイベントデータをJSON形式で生成"""
    
    print(f"""
╔════════════════════════════════════════════════════════════╗
║     イベントデータ生成スクリプト                              ║
║     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                 ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    init_database()
    checker = AdvancedActivityChecker()
    
    # 施設取得
    facilities = get_all_facilities()
    
    if limit:
        facilities = facilities[:limit]
    
    print(f"📊 調査対象: {len(facilities)} 施設\n")
    
    all_results = []
    all_events = []
    
    for facility in facilities:
        url = facility.get('website')
        if not url:
            continue
        
        result = await checker.check_facility(url, facility.get('name', ''))
        result['facility_id'] = facility.get('id', '')
        result['prefecture'] = facility.get('prefecture', '')
        
        all_results.append(result)
        
        # イベントを統合リストに追加
        for event in result.get('event_list', []):
            event['facility_name'] = facility.get('name', '')
            event['facility_id'] = facility.get('id', '')
            event['prefecture'] = facility.get('prefecture', '')
            all_events.append(event)
        
        # レート制限
        await asyncio.sleep(2)
    
    # 統計サマリー
    active_count = sum(1 for r in all_results if r.get('status') == 'active')
    dormant_count = sum(1 for r in all_results if r.get('status') == 'dormant')
    
    output = {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_facilities": len(all_results),
            "active": active_count,
            "dormant": dormant_count,
            "total_events": len(all_events)
        },
        "facilities": all_results,
        "events": sorted(all_events, key=lambda x: x.get('date', ''), reverse=True)
    }
    
    # 出力
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 出力完了: {output_file}")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    
    # サマリー表示
    print(f"""
{'='*60}
📈 調査結果サマリー
{'='*60}
  ✅ アクティブ: {active_count} 施設
  💤 休眠: {dormant_count} 施設
  📅 イベント総数: {len(all_events)} 件
{'='*60}
    """)
    
    return output


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='施設イベントデータ生成')
    parser.add_argument('-o', '--output', help='出力ファイルパス (例: data/events.json)')
    parser.add_argument('-n', '--limit', type=int, default=10, help='調査施設数の上限 (デフォルト: 10)')
    
    args = parser.parse_args()
    
    asyncio.run(generate_event_data(args.output, args.limit))


if __name__ == "__main__":
    main()
