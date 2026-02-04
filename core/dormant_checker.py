"""
休眠施設チェッカー
2ヶ月ルールに基づいて施設の休眠状態を判定
"""
from datetime import datetime, timedelta
from typing import Literal

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DORMANT_THRESHOLD_DAYS
from core.database import (
    get_all_facilities, 
    get_latest_event_date, 
    update_facility_status,
    get_connection
)


FacilityStatus = Literal["active", "dormant", "new", "closed"]


def check_facility_status(facility_id: str) -> FacilityStatus:
    """
    施設の休眠状態を判定
    
    Returns:
        "active" - 直近2ヶ月以内にイベントあり
        "dormant" - 2ヶ月以上イベントなし
        "new" - 新規施設（イベント実績なし）
        "closed" - 閉鎖済み
    """
    threshold_date = datetime.now() - timedelta(days=DORMANT_THRESHOLD_DAYS)
    
    latest_event_date = get_latest_event_date(facility_id)
    
    if latest_event_date is None:
        return "new"
    
    try:
        latest_date = datetime.fromisoformat(latest_event_date)
        if latest_date >= threshold_date:
            return "active"
        else:
            return "dormant"
    except ValueError:
        return "new"


def update_all_facility_statuses():
    """全施設のステータスを一括更新"""
    facilities = get_all_facilities()
    
    status_counts = {"active": 0, "dormant": 0, "new": 0, "unchanged": 0}
    
    for facility in facilities:
        facility_id = facility['id']
        current_status = facility.get('status', 'active')
        
        # 閉鎖済みはスキップ
        if current_status == 'closed':
            continue
        
        new_status = check_facility_status(facility_id)
        
        if new_status != current_status:
            reason = generate_status_change_reason(current_status, new_status)
            update_facility_status(facility_id, new_status, reason)
            status_counts[new_status] = status_counts.get(new_status, 0) + 1
            print(f"[STATUS CHANGED] {facility['name']}: {current_status} -> {new_status}")
        else:
            status_counts['unchanged'] += 1
    
    return status_counts


def generate_status_change_reason(old_status: str, new_status: str) -> str:
    """ステータス変更理由を生成"""
    if new_status == "dormant":
        return f"直近{DORMANT_THRESHOLD_DAYS}日間にイベント開催なし"
    elif new_status == "active" and old_status == "dormant":
        return "新規イベントが検出されました"
    elif new_status == "active" and old_status == "new":
        return "初回イベントが開催されました"
    else:
        return "自動ステータス更新"


def get_dormant_facilities() -> list:
    """休眠施設一覧を取得"""
    return get_all_facilities(status="dormant")


def get_active_facilities() -> list:
    """アクティブ施設一覧を取得"""
    return get_all_facilities(status="active")


def get_new_facilities() -> list:
    """新規施設（監視中）一覧を取得"""
    return get_all_facilities(status="new")


def reactivate_facility(facility_id: str, reason: str = "手動で再アクティブ化"):
    """休眠施設を手動でアクティブに戻す"""
    update_facility_status(facility_id, "active", reason)


def mark_as_closed(facility_id: str, reason: str = "閉鎖確認"):
    """施設を閉鎖済みとしてマーク"""
    update_facility_status(facility_id, "closed", reason)


def get_facility_health_report() -> dict:
    """施設の健全性レポートを生成"""
    facilities = get_all_facilities()
    
    report = {
        "total": len(facilities),
        "active": 0,
        "dormant": 0,
        "new": 0,
        "closed": 0,
        "by_prefecture": {},
        "dormant_list": [],
        "check_date": datetime.now().isoformat()
    }
    
    for facility in facilities:
        status = facility.get('status', 'active')
        report[status] = report.get(status, 0) + 1
        
        prefecture = facility.get('prefecture', '不明')
        if prefecture not in report["by_prefecture"]:
            report["by_prefecture"][prefecture] = {"active": 0, "dormant": 0, "new": 0}
        report["by_prefecture"][prefecture][status] = report["by_prefecture"][prefecture].get(status, 0) + 1
        
        if status == "dormant":
            latest_date = get_latest_event_date(facility['id'])
            report["dormant_list"].append({
                "id": facility['id'],
                "name": facility['name'],
                "prefecture": prefecture,
                "last_event": latest_date
            })
    
    return report


if __name__ == "__main__":
    print("=== 施設ステータス更新 ===")
    counts = update_all_facility_statuses()
    print(f"\n更新結果: {counts}")
    
    print("\n=== 健全性レポート ===")
    report = get_facility_health_report()
    print(f"総施設数: {report['total']}")
    print(f"アクティブ: {report['active']}")
    print(f"休眠中: {report['dormant']}")
    print(f"新規: {report['new']}")
