"""
connpass APIスクレイパー
公式APIを使用してスタートアップ関連イベントを取得
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Optional, Generator
import hashlib

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import CONNPASS_API_URL, CONNPASS_SEARCH_KEYWORDS, REQUEST_DELAY_SECONDS


def generate_event_id(source: str, original_id: str) -> str:
    """イベントIDを生成"""
    return hashlib.md5(f"{source}_{original_id}".encode()).hexdigest()[:16]


def fetch_events(
    keyword: Optional[str] = None,
    keyword_or: Optional[list] = None,
    ym: Optional[str] = None,
    ymd: Optional[str] = None,
    count: int = 100,
    order: int = 1,
    start: int = 1
) -> dict:
    """
    connpass APIからイベントを取得
    
    Args:
        keyword: 検索キーワード（AND検索）
        keyword_or: 検索キーワードリスト（OR検索）
        ym: 年月 (YYYYMM形式)
        ymd: 年月日 (YYYYMMDD形式)
        count: 取得件数 (最大100)
        order: 並び順 (1=更新日時順, 2=開催日時順, 3=新着順)
        start: 取得開始位置
    
    Returns:
        APIレスポンス
    """
    params = {
        "count": min(count, 100),
        "order": order,
        "start": start
    }
    
    if keyword:
        params["keyword"] = keyword
    if keyword_or:
        params["keyword_or"] = ",".join(keyword_or)
    if ym:
        params["ym"] = ym
    if ymd:
        params["ymd"] = ymd
    
    try:
        response = requests.get(
            CONNPASS_API_URL, 
            params=params,
            headers={"User-Agent": "StartupEventAggregator/1.0"}
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching from connpass: {e}")
        return {"results_returned": 0, "events": []}


def fetch_startup_events(months_ahead: int = 2) -> Generator[dict, None, None]:
    """
    スタートアップ関連イベントを取得
    
    Args:
        months_ahead: 何ヶ月先まで取得するか
    
    Yields:
        正規化されたイベント辞書
    """
    today = datetime.now()
    
    # 取得対象の年月リストを生成
    target_months = []
    for i in range(months_ahead + 1):
        target_date = today + timedelta(days=30 * i)
        target_months.append(target_date.strftime("%Y%m"))
    
    seen_ids = set()
    
    for ym in target_months:
        for keyword in CONNPASS_SEARCH_KEYWORDS:
            time.sleep(REQUEST_DELAY_SECONDS)  # APIレート制限対策
            
            result = fetch_events(keyword=keyword, ym=ym, count=100, order=2)
            
            for event in result.get("events", []):
                event_id = event.get("event_id")
                if event_id in seen_ids:
                    continue
                seen_ids.add(event_id)
                
                yield normalize_event(event)


def fetch_events_by_group(series_id: int) -> list:
    """
    グループ（シリーズ）のイベントを取得
    
    Args:
        series_id: connpassのシリーズID
    
    Returns:
        イベントリスト
    """
    params = {
        "series_id": series_id,
        "count": 100,
        "order": 2
    }
    
    try:
        response = requests.get(
            CONNPASS_API_URL,
            params=params,
            headers={"User-Agent": "StartupEventAggregator/1.0"}
        )
        response.raise_for_status()
        data = response.json()
        return [normalize_event(e) for e in data.get("events", [])]
    except requests.RequestException as e:
        print(f"Error fetching group events: {e}")
        return []


def normalize_event(raw_event: dict) -> dict:
    """
    connpassのイベントデータを正規化
    """
    started_at = raw_event.get("started_at", "")
    event_date = ""
    event_time = ""
    
    if started_at:
        try:
            dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            event_date = dt.strftime("%Y-%m-%d")
            event_time = dt.strftime("%H:%M")
        except ValueError:
            pass
    
    is_online = False
    place = raw_event.get("place", "")
    address = raw_event.get("address", "")
    
    if place:
        online_keywords = ["オンライン", "online", "Zoom", "zoom", "Teams", "teams", "ウェビナー"]
        is_online = any(kw.lower() in place.lower() for kw in online_keywords)
    
    return {
        "id": generate_event_id("connpass", str(raw_event.get("event_id", ""))),
        "original_id": raw_event.get("event_id"),
        "title": raw_event.get("title", ""),
        "description": raw_event.get("description", "")[:1000],  # 説明は1000文字まで
        "event_date": event_date,
        "event_time": event_time,
        "venue": place or address,
        "source": "connpass",
        "source_url": raw_event.get("event_url", ""),
        "is_online": is_online,
        "participants_limit": raw_event.get("limit"),
        "participants_count": raw_event.get("accepted"),
        "fee": "無料" if raw_event.get("event_type") == "participation" else "有料",
        "series_id": raw_event.get("series", {}).get("id") if raw_event.get("series") else None,
        "series_title": raw_event.get("series", {}).get("title") if raw_event.get("series") else None,
        "owner_nickname": raw_event.get("owner_nickname"),
        "prefecture": extract_prefecture(address),
    }


def extract_prefecture(address: str) -> Optional[str]:
    """住所から都道府県を抽出"""
    prefectures = [
        "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
        "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
        "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
        "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
        "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
        "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
        "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
    ]
    
    for pref in prefectures:
        if pref in address:
            return pref
    return None


if __name__ == "__main__":
    print("=== connpass イベント取得テスト ===")
    
    count = 0
    for event in fetch_startup_events(months_ahead=1):
        print(f"[{event['event_date']}] {event['title'][:50]}")
        count += 1
        if count >= 10:
            break
    
    print(f"\n取得完了: {count}件")
