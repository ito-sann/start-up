"""
自動実行スケジューラー
定期的にイベント情報を収集し、休眠判定を行う
"""
import schedule
import time
from datetime import datetime
import threading

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import init_database, insert_event, load_initial_facilities
from core.scorer import calculate_priority_score
from core.dormant_checker import update_all_facility_statuses


def collect_events_from_connpass():
    """connpassからイベントを収集"""
    print(f"[{datetime.now()}] connpassからイベント収集開始...")
    
    try:
        from scrapers.connpass import fetch_startup_events
        
        count = 0
        for event in fetch_startup_events(months_ahead=2):
            event['priority_score'] = calculate_priority_score(event)
            if insert_event(event):
                count += 1
        
        print(f"[{datetime.now()}] connpassから{count}件のイベントを収集")
    except Exception as e:
        print(f"[{datetime.now()}] connpassエラー: {e}")


def collect_events_from_peatix():
    """Peatixからイベントを収集"""
    print(f"[{datetime.now()}] Peatixからイベント収集開始...")
    
    try:
        from scrapers.peatix import fetch_all_startup_events
        
        count = 0
        for event in fetch_all_startup_events():
            event['priority_score'] = calculate_priority_score(event)
            if insert_event(event):
                count += 1
        
        print(f"[{datetime.now()}] Peatixから{count}件のイベントを収集")
    except Exception as e:
        print(f"[{datetime.now()}] Peatixエラー: {e}")


def collect_events_from_doorkeeper():
    """Doorkeeperからイベントを収集"""
    print(f"[{datetime.now()}] Doorkeeperからイベント収集開始...")
    
    try:
        from scrapers.doorkeeper import fetch_all_startup_events
        
        count = 0
        for event in fetch_all_startup_events():
            event['priority_score'] = calculate_priority_score(event)
            if insert_event(event):
                count += 1
        
        print(f"[{datetime.now()}] Doorkeeperから{count}件のイベントを収集")
    except Exception as e:
        print(f"[{datetime.now()}] Doorkeeperエラー: {e}")


def run_full_collection():
    """全ソースからイベントを収集"""
    print(f"\n{'='*50}")
    print(f"[{datetime.now()}] 全体収集開始")
    print(f"{'='*50}\n")
    
    collect_events_from_connpass()
    time.sleep(5)  # API負荷軽減
    
    collect_events_from_peatix()
    time.sleep(5)
    
    collect_events_from_doorkeeper()
    
    print(f"\n[{datetime.now()}] 全体収集完了")


def run_dormant_check():
    """休眠チェックを実行"""
    print(f"\n[{datetime.now()}] 休眠チェック開始...")
    counts = update_all_facility_statuses()
    print(f"[{datetime.now()}] 休眠チェック完了: {counts}")


def run_daily_job():
    """日次ジョブを実行"""
    print(f"\n{'='*50}")
    print(f"[{datetime.now()}] 日次ジョブ開始")
    print(f"{'='*50}\n")
    
    run_full_collection()
    run_dormant_check()
    
    print(f"\n[{datetime.now()}] 日次ジョブ完了")


def start_scheduler():
    """スケジューラーを開始"""
    print("スケジューラーを開始します...")
    
    # 初期化
    init_database()
    load_initial_facilities()
    
    # 日次ジョブ（毎朝6時）
    schedule.every().day.at("06:00").do(run_daily_job)
    
    # 週次休眠チェック（毎週月曜9時）
    schedule.every().monday.at("09:00").do(run_dormant_check)
    
    print("スケジュール設定完了:")
    print("  - 日次イベント収集: 毎朝 06:00")
    print("  - 週次休眠チェック: 毎週月曜 09:00")
    print("\nCtrl+C で停止")
    
    while True:
        schedule.run_pending()
        time.sleep(60)


def run_scheduler_in_background():
    """バックグラウンドでスケジューラーを実行"""
    thread = threading.Thread(target=start_scheduler, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="イベント収集スケジューラー")
    parser.add_argument("--now", action="store_true", help="今すぐ収集を実行")
    parser.add_argument("--daemon", action="store_true", help="デーモンモードで実行")
    args = parser.parse_args()
    
    if args.now:
        init_database()
        load_initial_facilities()
        run_daily_job()
    elif args.daemon:
        start_scheduler()
    else:
        parser.print_help()
