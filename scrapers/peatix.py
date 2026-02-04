"""
Peatix スクレイパー
Peatixからスタートアップ関連イベントを取得
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


PEATIX_SEARCH_URL = "https://peatix.com/search"
PEATIX_BASE_URL = "https://peatix.com"

SEARCH_KEYWORDS = [
    "スタートアップ",
    "起業",
    "ピッチ",
    "交流会 ビジネス",
    "資金調達",
    "補助金",
]


def generate_event_id(source: str, original_id: str) -> str:
    """イベントIDを生成"""
    return hashlib.md5(f"{source}_{original_id}".encode()).hexdigest()[:16]


def search_events(keyword: str, page: int = 1) -> list:
    """
    Peatixでイベントを検索
    
    Args:
        keyword: 検索キーワード
        page: ページ番号
        
    Returns:
        イベントリスト
    """
    params = {
        "q": keyword,
        "country": "JP",
        "p": page,
        "v": "3.4",
        "dr": "today",  # 今後のイベントのみ
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    try:
        response = requests.get(PEATIX_SEARCH_URL, params=params, headers=headers)
        response.raise_for_status()
        return parse_search_results(response.text)
    except requests.RequestException as e:
        print(f"Error searching Peatix: {e}")
        return []


def parse_search_results(html: str) -> list:
    """
    検索結果HTMLをパース
    """
    soup = BeautifulSoup(html, 'lxml')
    events = []
    
    # イベントカードを検索
    event_cards = soup.select('.event-card, .search-result-item, [data-event-id]')
    
    for card in event_cards:
        try:
            event = extract_event_from_card(card)
            if event:
                events.append(event)
        except Exception as e:
            print(f"Error parsing event card: {e}")
            continue
    
    return events


def extract_event_from_card(card) -> Optional[dict]:
    """
    イベントカードからイベント情報を抽出
    """
    # イベントID
    event_id = card.get('data-event-id') or ""
    if not event_id:
        link = card.select_one('a[href*="/event/"]')
        if link:
            href = link.get('href', '')
            match = re.search(r'/event/(\d+)', href)
            if match:
                event_id = match.group(1)
    
    if not event_id:
        return None
    
    # タイトル
    title_elem = card.select_one('.event-card-title, .event-name, h3, h2')
    title = title_elem.get_text(strip=True) if title_elem else ""
    
    # 日時
    date_elem = card.select_one('.event-card-date, .event-date, time')
    date_text = date_elem.get_text(strip=True) if date_elem else ""
    event_date, event_time = parse_date_text(date_text)
    
    # 場所
    venue_elem = card.select_one('.event-card-venue, .venue, .location')
    venue = venue_elem.get_text(strip=True) if venue_elem else ""
    
    # オンライン判定
    is_online = "オンライン" in venue or "online" in venue.lower()
    
    # URL
    link = card.select_one('a[href*="/event/"]')
    source_url = ""
    if link:
        href = link.get('href', '')
        if href.startswith('/'):
            source_url = PEATIX_BASE_URL + href
        else:
            source_url = href
    
    return {
        "id": generate_event_id("peatix", event_id),
        "original_id": event_id,
        "title": title,
        "description": "",  # 詳細ページから取得が必要
        "event_date": event_date,
        "event_time": event_time,
        "venue": venue,
        "source": "peatix",
        "source_url": source_url,
        "is_online": is_online,
        "participants_limit": None,
        "participants_count": None,
        "fee": None,
    }


def parse_date_text(date_text: str) -> tuple:
    """
    日時テキストをパース
    
    Returns:
        (event_date, event_time) タプル
    """
    if not date_text:
        return "", ""
    
    # 様々な日付フォーマットに対応
    patterns = [
        r'(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})',  # 2024年1月15日 or 2024/1/15
        r'(\d{1,2})[月/](\d{1,2})',  # 1月15日 (年なし)
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
            
            # 時刻を抽出
            time_match = re.search(r'(\d{1,2}):(\d{2})', date_text)
            event_time = f"{time_match.group(1)}:{time_match.group(2)}" if time_match else ""
            
            return event_date, event_time
    
    return "", ""


def fetch_all_startup_events() -> Generator[dict, None, None]:
    """
    全スタートアップ関連イベントを取得
    
    Yields:
        正規化されたイベント辞書
    """
    seen_ids = set()
    
    for keyword in SEARCH_KEYWORDS:
        time.sleep(REQUEST_DELAY_SECONDS)
        
        events = search_events(keyword)
        
        for event in events:
            if event['id'] not in seen_ids:
                seen_ids.add(event['id'])
                yield event


def get_event_details(event_url: str) -> dict:
    """
    イベント詳細ページから追加情報を取得
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    
    try:
        response = requests.get(event_url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 説明文
        desc_elem = soup.select_one('.event-description, .description, #event-description')
        description = desc_elem.get_text(strip=True)[:1000] if desc_elem else ""
        
        # 料金
        price_elem = soup.select_one('.ticket-price, .price')
        fee = price_elem.get_text(strip=True) if price_elem else None
        
        return {
            "description": description,
            "fee": fee,
        }
    except Exception as e:
        print(f"Error fetching event details: {e}")
        return {}


if __name__ == "__main__":
    print("=== Peatix イベント取得テスト ===")
    
    count = 0
    for event in fetch_all_startup_events():
        print(f"[{event['event_date']}] {event['title'][:50]}")
        count += 1
        if count >= 10:
            break
    
    print(f"\n取得完了: {count}件")
