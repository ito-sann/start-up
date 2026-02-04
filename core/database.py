"""
データベース操作モジュール
SQLiteを使用して施設・イベント情報を管理
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_PATH, DATA_DIR


def get_connection() -> sqlite3.Connection:
    """データベース接続を取得"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """データベースの初期化（テーブル作成）"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 施設テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facilities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            prefecture TEXT NOT NULL,
            city TEXT,
            address TEXT,
            website TEXT,
            connpass_group TEXT,
            peatix_group TEXT,
            doorkeeper_group TEXT,
            twitter TEXT,
            status TEXT DEFAULT 'active',
            last_event_date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    """)
    
    # イベントテーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            facility_id TEXT,
            title TEXT NOT NULL,
            description TEXT,
            event_date TEXT NOT NULL,
            event_time TEXT,
            venue TEXT,
            event_type TEXT,
            source TEXT,
            source_url TEXT,
            priority_score INTEGER DEFAULT 0,
            is_online INTEGER DEFAULT 0,
            participants_limit INTEGER,
            participants_count INTEGER,
            fee TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (facility_id) REFERENCES facilities(id)
        )
    """)
    
    # 施設ステータス履歴テーブル
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facility_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            facility_id TEXT,
            old_status TEXT,
            new_status TEXT,
            changed_at TEXT DEFAULT CURRENT_TIMESTAMP,
            reason TEXT,
            FOREIGN KEY (facility_id) REFERENCES facilities(id)
        )
    """)
    
    conn.commit()
    conn.close()


def insert_facility(facility: dict) -> bool:
    """施設を追加"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO facilities 
            (id, name, prefecture, city, address, website, connpass_group, 
             peatix_group, doorkeeper_group, twitter, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            facility.get('id'),
            facility.get('name'),
            facility.get('prefecture'),
            facility.get('city'),
            facility.get('address'),
            facility.get('website'),
            facility.get('connpass_group'),
            facility.get('peatix_group'),
            facility.get('doorkeeper_group'),
            facility.get('twitter'),
            facility.get('status', 'active'),
            facility.get('notes'),
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error inserting facility: {e}")
        return False
    finally:
        conn.close()


def insert_event(event: dict) -> bool:
    """イベントを追加"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT OR REPLACE INTO events 
            (id, facility_id, title, description, event_date, event_time, 
             venue, event_type, source, source_url, priority_score, 
             is_online, participants_limit, participants_count, fee)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get('id'),
            event.get('facility_id'),
            event.get('title'),
            event.get('description'),
            event.get('event_date'),
            event.get('event_time'),
            event.get('venue'),
            event.get('event_type'),
            event.get('source'),
            event.get('source_url'),
            event.get('priority_score', 0),
            1 if event.get('is_online') else 0,
            event.get('participants_limit'),
            event.get('participants_count'),
            event.get('fee'),
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error inserting event: {e}")
        return False
    finally:
        conn.close()


def get_all_facilities(status: Optional[str] = None) -> list:
    """全施設を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    
    if status:
        cursor.execute("SELECT * FROM facilities WHERE status = ? ORDER BY prefecture, name", (status,))
    else:
        cursor.execute("SELECT * FROM facilities ORDER BY prefecture, name")
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_facility_by_id(facility_id: str) -> Optional[dict]:
    """IDで施設を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM facilities WHERE id = ?", (facility_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_facility_by_url(url: str) -> Optional[dict]:
    """指定されたURLの施設情報を取得（重複チェック用）"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM facilities WHERE website = ?', (url,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_events(
    facility_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    min_score: Optional[int] = None,
    limit: int = 100
) -> list:
    """イベントを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM events WHERE 1=1"
    params = []
    
    if facility_id:
        query += " AND facility_id = ?"
        params.append(facility_id)
    
    if from_date:
        query += " AND event_date >= ?"
        params.append(from_date)
    
    if to_date:
        query += " AND event_date <= ?"
        params.append(to_date)
    
    if min_score is not None:
        query += " AND priority_score >= ?"
        params.append(min_score)
    
    query += " ORDER BY event_date DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_latest_event_date(facility_id: str) -> Optional[str]:
    """施設の最新イベント日を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT MAX(event_date) as latest_date 
        FROM events 
        WHERE facility_id = ?
    """, (facility_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    return row['latest_date'] if row and row['latest_date'] else None


def update_facility_status(facility_id: str, new_status: str, last_event_date: str = None, reason: str = None):
    """施設のステータスを更新"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 現在のステータスを取得
    cursor.execute("SELECT status FROM facilities WHERE id = ?", (facility_id,))
    row = cursor.fetchone()
    old_status = row['status'] if row else None
    
    # ステータス更新
    if last_event_date:
        cursor.execute("""
            UPDATE facilities 
            SET status = ?, last_event_date = ?, updated_at = ? 
            WHERE id = ?
        """, (new_status, last_event_date, datetime.now().isoformat(), facility_id))
    else:
        cursor.execute("""
            UPDATE facilities 
            SET status = ?, updated_at = ? 
            WHERE id = ?
        """, (new_status, datetime.now().isoformat(), facility_id))
    
    # 履歴を記録
    cursor.execute("""
        INSERT INTO facility_status_history 
        (facility_id, old_status, new_status, reason)
        VALUES (?, ?, ?, ?)
    """, (facility_id, old_status, new_status, reason))
    
    conn.commit()
    conn.close()


def get_upcoming_events(days: int = 30, min_score: int = 0) -> list:
    """今後のイベントを取得"""
    conn = get_connection()
    cursor = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now().replace(day=1) + 
              __import__('dateutil.relativedelta', fromlist=['relativedelta']).relativedelta(months=1, days=days)).strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT e.*, f.name as facility_name, f.prefecture
        FROM events e
        LEFT JOIN facilities f ON e.facility_id = f.id
        WHERE e.event_date >= ? AND e.event_date <= ?
        AND e.priority_score >= ?
        ORDER BY e.priority_score DESC, e.event_date ASC
    """, (today, future, min_score))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results


def get_statistics() -> dict:
    """統計情報を取得"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 施設数
    cursor.execute("SELECT status, COUNT(*) as count FROM facilities GROUP BY status")
    facility_stats = {row['status']: row['count'] for row in cursor.fetchall()}
    
    # イベント数
    cursor.execute("SELECT COUNT(*) as count FROM events")
    event_count = cursor.fetchone()['count']
    
    # 都道府県別施設数
    cursor.execute("""
        SELECT prefecture, COUNT(*) as count 
        FROM facilities 
        WHERE status = 'active'
        GROUP BY prefecture 
        ORDER BY count DESC
    """)
    prefecture_stats = {row['prefecture']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        'facility_stats': facility_stats,
        'event_count': event_count,
        'prefecture_stats': prefecture_stats,
    }


def load_initial_facilities():
    """初期施設データをJSONから読み込み"""
    facilities_file = DATA_DIR / "facilities.json"
    new_facilities_file = DATA_DIR / "new_facilities_2026.json"
    
    for file_path in [facilities_file, new_facilities_file]:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                facilities = json.load(f)
                for facility in facilities:
                    insert_facility(facility)


if __name__ == "__main__":
    init_database()
    print("Database initialized successfully!")
