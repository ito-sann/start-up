"""
Doorkeeper スクレイパー
Doorkeeperからスタートアップ関連イベントを取得
"""
import requests
from bs4 import BeautifulSoup
import time
from datetime import datetime
from typing import Generator, Optional
import hashlib
import re

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import REQUEST_DELAY_SECONDS


DOORKEEPER_SEARCH_URL = "https://www.doorkeeper.jp/events"
DOORKEEPER_BASE_URL = "https://www.doorkeeper.jp"

SEARCH_KEYWORDS = [
    "スタートアップ",
    "起業",
    "ピッチ",
    "networking",
    "資金調達",
]


def generate_event_id(source: str, original_id: str) -> str:
    """イベントIDを生成"""
    return hashlib.md5(f"{source}_{original_id}".encode()).hexdigest()[:16]


def search_events(keyword: str, page: int = 1) -> list:
    """
    Doorkeeperでイベントを検索
    """
    params = {
        "q": keyword,
        "page": page,
        "utf8": "✓",
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        response = requests.get(DOORKEEPER_SEARCH_URL, params=params, headers=headers)
        response.raise_for_status()
        return parse_search_results(response.text)
    except requests.RequestException as e:
        print(f"Error searching Doorkeeper: {e}")
        return []


def parse_search_results(html: str) -> list:
    """
    検索結果HTMLをパース
    """
    soup = BeautifulSoup(html, 'lxml')
    events = []
    
    # イベントカードを検索
    event_cards = soup.select('.event, .event-item, article.event')
    
    for card in event_cards:
        try:
            event = extract_event_from_card(card)
            if event:
                events.append(event)
        except Exception as e:
            print(f"Error parsing Doorkeeper event card: {e}")
            continue
    
    return events


def extract_event_from_card(card) -> Optional[dict]:
    """
    イベントカードからイベント情報を抽出
    """
    # URL/ID
    link = card.select_one('a[href*="/events/"]')
    if not link:
        return None
    
    href = link.get('href', '')
    # URLからイベントIDを抽出
    match = re.search(r'/events/(\d+)', href)
    if not match:
        return None
    
    event_id = match.group(1)
    
    if href.startswith('/'):
        source_url = DOORKEEPER_BASE_URL + href
    else:
        source_url = href
    
    # タイトル
    title_elem = card.select_one('.event-title, .title, h3, h2 a')
    title = title_elem.get_text(strip=True) if title_elem else ""
    
    # 日時
    date_elem = card.select_one('.event-date, time, .date')
    date_text = date_elem.get_text(strip=True) if date_elem else ""
    event_date, event_time = parse_date_text(date_text)
    
    # 場所
    venue_elem = card.select_one('.event-place, .venue, .location')
    venue = venue_elem.get_text(strip=True) if venue_elem else ""
    
    # オンライン判定
    is_online = "オンライン" in venue or "online" in venue.lower() or "Zoom" in venue
    
    return {
        "id": generate_event_id("doorkeeper", event_id),
        "original_id": event_id,
        "title": title,
        "description": "",
        "event_date": event_date,
        "event_time": event_time,
        "venue": venue,
        "source": "doorkeeper",
        "source_url": source_url,
        "is_online": is_online,
        "participants_limit": None,
        "participants_count": None,
        "fee": None,
    }


def parse_date_text(date_text: str) -> tuple:
    """
    日時テキストをパース
    """
    if not date_text:
        return "", ""
    
    patterns = [
        r'(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})',
        r'(\d{1,2})[月/](\d{1,2})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, date_text)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                year, month, day = groups
                event_date = f"{year}-{int(month):02d}-{int(day):02d}"
            else:
                month, day = groups
                year = datetime.now().year
                event_date = f"{year}-{int(month):02d}-{int(day):02d}"
            
            time_match = re.search(r'(\d{1,2}):(\d{2})', date_text)
            event_time = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else ""
            
            return event_date, event_time
    
    return "", ""


def fetch_all_startup_events() -> Generator[dict, None, None]:
    """
    全スタートアップ関連イベントを取得
    """
    seen_ids = set()
    
    for keyword in SEARCH_KEYWORDS:
        time.sleep(REQUEST_DELAY_SECONDS)
        
        events = search_events(keyword)
        
        for event in events:
            if event['id'] not in seen_ids:
                seen_ids.add(event['id'])
                yield event


if __name__ == "__main__":
    print("=== Doorkeeper イベント取得テスト ===")
    
    count = 0
    for event in fetch_all_startup_events():
        print(f"[{event['event_date']}] {event['title'][:50]}")
        count += 1
        if count >= 10:
            break
    
    print(f"\n取得完了: {count}件")
