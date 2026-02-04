"""
高度版 活動判定エージェント
- 1階層以上のページ遷移
- Peatix/connpass/Facebookイベント検知
- 和暦・相対表記の日付正規化
- イベントリストの構造化出力
"""

import re
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from playwright.async_api import async_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# 現在の基準日
CURRENT_DATE = datetime(2026, 2, 4)
THRESHOLD_DATE = CURRENT_DATE - timedelta(days=60)  # 2025-12-04

# 日付パターン（優先度順）
DATE_PATTERNS = [
    # 2026年2月4日, 2026年02月04日
    (r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日', 'ymd'),
    # 2026/2/4, 2026/02/04
    (r'(\d{4})/(\d{1,2})/(\d{1,2})', 'ymd'),
    # 2026-02-04
    (r'(\d{4})-(\d{2})-(\d{2})', 'ymd'),
    # 2026.02.04
    (r'(\d{4})\.(\d{1,2})\.(\d{1,2})', 'ymd'),
    # 令和8年2月4日
    (r'令和(\d{1,2})年\s*(\d{1,2})月\s*(\d{1,2})日', 'reiwa'),
    # R8.2.4
    (r'R(\d{1,2})\.(\d{1,2})\.(\d{1,2})', 'reiwa'),
    # 2/4（今年と仮定）
    (r'(\d{1,2})/(\d{1,2})(?!\d)', 'md'),
    # 2月4日
    (r'(\d{1,2})月\s*(\d{1,2})日', 'md'),
]

# イベントページを示すキーワード
EVENT_KEYWORDS = [
    'event', 'events', 'イベント', 'セミナー', 'seminar',
    'news', 'お知らせ', 'ニュース', '新着', 'topics',
    'calendar', 'カレンダー', 'schedule', 'スケジュール',
    'report', '活動報告', 'activity'
]

# 外部プラットフォームのドメイン
EXTERNAL_PLATFORMS = {
    'peatix.com': 'Peatix',
    'connpass.com': 'connpass',
    'facebook.com/events': 'Facebook',
    'fb.me': 'Facebook',
    'eventbrite.com': 'Eventbrite',
    'doorkeeper.jp': 'Doorkeeper'
}


def parse_date_string(text: str) -> Optional[datetime]:
    """様々な形式の日付文字列をdatetimeに変換"""
    text = text.strip()
    
    for pattern, date_type in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            try:
                if date_type == 'ymd':
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                elif date_type == 'reiwa':
                    # 令和変換（令和1年 = 2019年）
                    year = 2018 + int(groups[0])
                    month, day = int(groups[1]), int(groups[2])
                elif date_type == 'md':
                    # 月日のみの場合、今年または来年と仮定
                    month, day = int(groups[0]), int(groups[1])
                    year = CURRENT_DATE.year
                    # 月が現在より前なら来年の可能性
                    if month < CURRENT_DATE.month:
                        year += 1
                else:
                    continue
                
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return datetime(year, month, day)
            except:
                continue
    
    return None


def extract_all_dates(text: str) -> List[Tuple[datetime, str]]:
    """テキストから全ての日付とその周辺文脈を抽出"""
    results = []
    lines = text.split('\n')
    
    for line in lines:
        for pattern, date_type in DATE_PATTERNS:
            for match in re.finditer(pattern, line):
                parsed = parse_date_string(match.group())
                if parsed and 2020 <= parsed.year <= 2030:
                    # 周辺のテキスト（タイトル候補）を取得
                    context = line.strip()[:100]
                    results.append((parsed, context))
    
    # 重複除去して日付降順でソート
    seen = set()
    unique_results = []
    for date, context in sorted(results, key=lambda x: x[0], reverse=True):
        date_str = date.strftime('%Y-%m-%d')
        if date_str not in seen:
            seen.add(date_str)
            unique_results.append((date, context))
    
    return unique_results


class AdvancedActivityChecker:
    """高度版活動判定エージェント"""
    
    def __init__(self):
        self.current_date = CURRENT_DATE
        self.threshold_date = THRESHOLD_DATE
    
    async def find_event_links(self, page: Page, base_url: str) -> List[Dict]:
        """イベント関連ページへのリンクを探索"""
        links = await page.evaluate("""
            Array.from(document.querySelectorAll('a')).map(a => ({
                text: a.innerText.trim().toLowerCase(),
                href: a.href,
                ariaLabel: a.getAttribute('aria-label') || ''
            })).filter(a => a.href && a.href.startsWith('http'))
        """)
        
        event_links = []
        external_links = []
        
        for link in links:
            href = link['href']
            text = link['text']
            
            # 外部プラットフォームチェック
            for domain, platform in EXTERNAL_PLATFORMS.items():
                if domain in href:
                    external_links.append({
                        'url': href,
                        'platform': platform,
                        'text': text
                    })
                    break
            
            # 内部イベントページチェック
            for keyword in EVENT_KEYWORDS:
                if keyword in text or keyword in href.lower():
                    if urlparse(href).netloc == urlparse(base_url).netloc:
                        event_links.append({
                            'url': href,
                            'text': text,
                            'type': 'internal'
                        })
                    break
        
        return event_links, external_links
    
    async def get_page_text(self, page: Page) -> str:
        """ページからテキストを抽出"""
        await page.evaluate("""
            document.querySelectorAll('script, style, nav, footer, header').forEach(el => el.remove());
        """)
        return await page.evaluate("document.body.innerText")
    
    async def extract_events_from_page(self, page: Page, url: str) -> List[Dict]:
        """ページからイベント情報を抽出"""
        text = await self.get_page_text(page)
        dates_with_context = extract_all_dates(text)
        
        events = []
        for date, context in dates_with_context[:20]:  # 最新20件まで
            # イベントタイトルを推測
            title = context.split('|')[0].split('【')[0].strip()[:50]
            if not title or len(title) < 3:
                title = f"イベント ({date.strftime('%Y-%m-%d')})"
            
            events.append({
                'title': title,
                'date': date.strftime('%Y-%m-%d'),
                'link': url
            })
        
        return events
    
    async def check_external_platform(self, page: Page, platform_url: str, platform_name: str) -> List[Dict]:
        """外部プラットフォームからイベント情報を取得"""
        try:
            await page.goto(platform_url, timeout=30000, wait_until='domcontentloaded')
            await asyncio.sleep(2)  # 動的コンテンツ待ち
            
            text = await self.get_page_text(page)
            dates_with_context = extract_all_dates(text)
            
            events = []
            for date, context in dates_with_context[:10]:
                events.append({
                    'title': context[:50] if context else f"{platform_name}イベント",
                    'date': date.strftime('%Y-%m-%d'),
                    'link': platform_url,
                    'platform': platform_name
                })
            
            return events
        except Exception as e:
            print(f"    ⚠ {platform_name}アクセスエラー: {e}")
            return []
    
    async def check_facility(self, url: str, facility_name: str = "") -> Dict[str, Any]:
        """施設の活動状況を詳細に判定"""
        print(f"\n🔍 調査開始: {facility_name or url}")
        
        result = {
            "facility_name": facility_name,
            "url": url,
            "status": "dormant",
            "last_event_date": None,
            "event_list": [],
            "external_platforms": [],
            "checked_pages": []
        }
        
        if not PLAYWRIGHT_AVAILABLE:
            result["error"] = "Playwrightがインストールされていません"
            return result
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await context.new_page()
            
            try:
                # 1. トップページアクセス
                print(f"  📄 トップページ: {url}")
                await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                await asyncio.sleep(1)
                
                # トップページからイベント抽出
                top_events = await self.extract_events_from_page(page, url)
                result["event_list"].extend(top_events)
                result["checked_pages"].append(url)
                
                # 2. イベントページリンクと外部プラットフォームを探索
                event_links, external_links = await self.find_event_links(page, url)
                result["external_platforms"] = [e['platform'] for e in external_links]
                
                # 3. 内部イベントページを1階層遷移
                for link in event_links[:3]:  # 最大3ページ
                    link_url = link['url']
                    if link_url in result["checked_pages"]:
                        continue
                    
                    print(f"  📄 イベントページ: {link_url[:60]}...")
                    try:
                        await page.goto(link_url, timeout=30000, wait_until='domcontentloaded')
                        await asyncio.sleep(1)
                        
                        page_events = await self.extract_events_from_page(page, link_url)
                        result["event_list"].extend(page_events)
                        result["checked_pages"].append(link_url)
                    except:
                        continue
                
                # 4. 外部プラットフォームをチェック
                for ext_link in external_links[:2]:  # 最大2プラットフォーム
                    print(f"  🔗 外部プラットフォーム: {ext_link['platform']}")
                    ext_events = await self.check_external_platform(
                        page, ext_link['url'], ext_link['platform']
                    )
                    result["event_list"].extend(ext_events)
                
            except Exception as e:
                print(f"  ✗ エラー: {e}")
                result["error"] = str(e)
            finally:
                await browser.close()
        
        # 5. イベントリストを日付でソートし、重複除去
        seen_dates = set()
        unique_events = []
        for event in sorted(result["event_list"], key=lambda x: x['date'], reverse=True):
            if event['date'] not in seen_dates:
                seen_dates.add(event['date'])
                unique_events.append(event)
        result["event_list"] = unique_events[:20]  # 最新20件
        
        # 6. 2ヶ月ルールの適用
        if result["event_list"]:
            latest_date_str = result["event_list"][0]['date']
            result["last_event_date"] = latest_date_str
            
            latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d')
            if latest_date >= self.threshold_date:
                result["status"] = "active"
                print(f"  ✅ アクティブ (最新: {latest_date_str})")
            else:
                print(f"  💤 休眠 (最新: {latest_date_str})")
        else:
            print(f"  ❓ イベント情報なし")
        
        return result
    
    async def check_multiple_facilities(self, facilities: List[Dict]) -> List[Dict]:
        """複数施設を一括チェック"""
        results = []
        
        for facility in facilities:
            result = await self.check_facility(
                facility.get('website', facility.get('url', '')),
                facility.get('name', '')
            )
            result['facility_id'] = facility.get('id', '')
            results.append(result)
            
            # レート制限
            await asyncio.sleep(2)
        
        return results


async def main():
    """テスト実行"""
    checker = AdvancedActivityChecker()
    
    # テスト施設
    test_url = "https://tib.metro.tokyo.lg.jp/"
    result = await checker.check_facility(test_url, "Tokyo Innovation Base")
    
    print("\n" + "="*60)
    print("📊 調査結果 (JSON)")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
