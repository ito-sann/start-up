#!/usr/bin/env python3
"""
3日間隔で活動チェックを自動実行するスケジューラー
バックグラウンドで常駐実行する場合に使用
"""

import schedule
import time
import asyncio
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.check_all_facilities import run_activity_check


def job():
    """定期ジョブ"""
    print(f"\n🔔 定期チェック開始: {datetime.now()}")
    asyncio.run(run_activity_check())
    print(f"✅ 定期チェック完了: {datetime.now()}")


def main():
    """メイン実行"""
    print("""
╔════════════════════════════════════════════════════════════╗
║       スタートアップ施設 活動チェック スケジューラー            ║
║                  3日間隔で自動実行                          ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # 3日ごとに実行（毎日6:00にチェックし、3日経過していれば実行）
    schedule.every(3).days.at("06:00").do(job)
    
    print(f"📅 次回実行予定: {schedule.next_run()}")
    print("💡 停止するには Ctrl+C を押してください\n")
    
    # 初回は即座に実行するかどうか
    run_now = input("今すぐ実行しますか？ (y/N): ").strip().lower()
    if run_now == 'y':
        job()
    
    # スケジューラーループ
    while True:
        schedule.run_pending()
        time.sleep(60)  # 1分ごとにチェック


if __name__ == "__main__":
    main()
