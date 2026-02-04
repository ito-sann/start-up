"""
イベントスコアリングモジュール
イベントの人脈価値を評価
"""
import re
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import EVENT_TYPE_SCORES, HIGH_PRIORITY_KEYWORDS, EXCLUDE_KEYWORDS


def calculate_priority_score(event: dict) -> int:
    """
    イベントの優先度スコアを計算
    
    Args:
        event: イベント情報の辞書
        
    Returns:
        優先度スコア (0-100+)
    """
    score = 0
    
    title = event.get('title', '').lower()
    description = event.get('description', '').lower()
    combined_text = f"{title} {description}"
    
    # 除外キーワードチェック
    for keyword in EXCLUDE_KEYWORDS:
        if keyword.lower() in combined_text:
            return 0
    
    # イベントタイプによるベーススコア
    event_type = detect_event_type(event)
    score += EVENT_TYPE_SCORES.get(event_type, EVENT_TYPE_SCORES['other'])
    
    # 高プライオリティキーワードによるボーナス
    keyword_match_count = 0
    for keyword in HIGH_PRIORITY_KEYWORDS:
        if keyword.lower() in combined_text:
            keyword_match_count += 1
    
    # キーワードマッチによるボーナス（最大30点）
    score += min(keyword_match_count * 10, 30)
    
    # 参加者数によるボーナス
    participants_limit = event.get('participants_limit', 0)
    if participants_limit:
        if 10 <= participants_limit <= 50:
            score += 15  # 少人数制は濃い交流が期待できる
        elif 50 < participants_limit <= 100:
            score += 10
        elif participants_limit > 100:
            score += 5   # 大規模イベントは個別交流しにくい
    
    # オフラインイベントはボーナス
    if not event.get('is_online', False):
        score += 20
    
    # 無料イベントは参加しやすい
    fee = event.get('fee', '')
    if fee and ('無料' in str(fee) or '0円' in str(fee) or fee == '0'):
        score += 5
    
    return min(score, 150)  # 最大150点


def detect_event_type(event: dict) -> str:
    """
    イベントタイプを自動判定
    
    Returns:
        "pitch", "networking", "workshop", "seminar", "online", "other"
    """
    title = event.get('title', '').lower()
    description = event.get('description', '').lower()
    combined_text = f"{title} {description}"
    
    # オンラインイベント
    if event.get('is_online', False):
        online_keywords = ['オンライン', 'online', 'ウェビナー', 'webinar', 'zoom', 'teams']
        for keyword in online_keywords:
            if keyword in combined_text:
                return "online"
    
    # ピッチイベント
    pitch_keywords = ['ピッチ', 'pitch', 'デモデイ', 'demo day', 'demoday', '発表会', 'プレゼン大会']
    for keyword in pitch_keywords:
        if keyword in combined_text:
            return "pitch"
    
    # ネットワーキング・交流会
    networking_keywords = [
        '交流会', 'ネットワーキング', 'networking', '懇親会', 
        'ミートアップ', 'meetup', 'meet up', '名刺交換',
        '異業種交流', 'マッチング'
    ]
    for keyword in networking_keywords:
        if keyword in combined_text:
            return "networking"
    
    # ワークショップ
    workshop_keywords = ['ワークショップ', 'workshop', 'ハンズオン', 'hands-on', '実践', '体験']
    for keyword in workshop_keywords:
        if keyword in combined_text:
            return "workshop"
    
    # セミナー
    seminar_keywords = ['セミナー', 'seminar', '講演', '講座', 'ウェビナー', 'webinar', '勉強会']
    for keyword in seminar_keywords:
        if keyword in combined_text:
            return "seminar"
    
    return "other"


def get_priority_label(score: int) -> str:
    """スコアからラベルを取得"""
    if score >= 100:
        return "🔥 最優先"
    elif score >= 80:
        return "⭐ 高"
    elif score >= 50:
        return "📌 中"
    elif score >= 30:
        return "📋 低"
    else:
        return "⬜ 対象外"


def get_priority_color(score: int) -> str:
    """スコアから色コードを取得"""
    if score >= 100:
        return "#ff4444"
    elif score >= 80:
        return "#ff8800"
    elif score >= 50:
        return "#ffcc00"
    elif score >= 30:
        return "#88cc00"
    else:
        return "#cccccc"


def should_attend(event: dict, min_score: int = 50) -> bool:
    """イベントに参加すべきか判定"""
    score = calculate_priority_score(event)
    return score >= min_score


def rank_events(events: list) -> list:
    """イベントリストをスコア順にソート"""
    for event in events:
        if 'priority_score' not in event or event['priority_score'] == 0:
            event['priority_score'] = calculate_priority_score(event)
        event['priority_label'] = get_priority_label(event['priority_score'])
    
    return sorted(events, key=lambda x: x['priority_score'], reverse=True)


if __name__ == "__main__":
    # テスト
    test_events = [
        {
            "title": "スタートアップピッチ大会 & 交流会",
            "description": "起業家によるピッチと投資家との交流会",
            "participants_limit": 30,
            "is_online": False,
            "fee": "無料"
        },
        {
            "title": "プログラミング初心者向けもくもく会",
            "description": "初心者向けのプログラミング勉強会",
            "participants_limit": 20,
            "is_online": False,
            "fee": "500円"
        },
        {
            "title": "補助金セミナー〜ものづくり補助金の申請方法〜",
            "description": "中小企業向け補助金の申請方法を解説",
            "participants_limit": 50,
            "is_online": True,
            "fee": "無料"
        }
    ]
    
    ranked = rank_events(test_events)
    for event in ranked:
        print(f"{event['priority_label']} [{event['priority_score']}点] {event['title']}")
