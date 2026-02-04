"""
簡易版 活動状況判定モジュール（APIキー不要）
Playwrightでサイトを巡回し、正規表現で日付を抽出して2ヶ月ルールを適用する。
"""

import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Playwright（非同期）
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠ Playwrightがインストールされていません。pip install playwright && playwright install を実行してください。")


# 日付パターン（日本語サイト向け）
DATE_PATTERNS = [
    # 2026年2月4日, 2026年02月04日
    r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日',
    # 2026/2/4, 2026/02/04
    r'(\d{4})/(\d{1,2})/(\d{1,2})',
    # 2026-02-04
    r'(\d{4})-(\d{2})-(\d{2})',
    # 2026.02.04
    r'(\d{4})\.(\d{2})\.(\d{2})',
    # R8.2.4 (令和8年)
    r'R(\d{1,2})\.(\d{1,2})\.(\d{1,2})',
    # 令和8年2月4日
    r'令和(\d{1,2})年\s*(\d{1,2})月\s*(\d{1,2})日',
]

# ニュース・イベントページを示すキーワード
NEWS_KEYWORDS = ['news', 'topic', 'event', 'seminar', 'お知らせ', 'ニュース', 'イベント', '新着', '活動報告']


def parse_date(match: tuple, pattern_index: int) -> Optional[datetime]:
    """マッチした日付をdatetimeに変換"""
    try:
        if pattern_index in [4, 5]:  # 令和パターン
            year = 2018 + int(match[0])  # 令和1年 = 2019年
        else:
            year = int(match[0])
        month = int(match[1])
        day = int(match[2])
        
        if 1 <= month <= 12 and 1 <= day <= 31 and 2020 <= year <= 2030:
            return datetime(year, month, day)
    except:
        pass
    return None


def extract_dates_from_text(text: str) -> List[datetime]:
    """テキストから全ての日付を抽出"""
    dates = []
    
    for i, pattern in enumerate(DATE_PATTERNS):
        matches = re.findall(pattern, text)
        for match in matches:
            parsed = parse_date(match, i)
            if parsed:
                dates.append(parsed)
    
    return dates


class SimpleActivityChecker:
    """APIキー不要の簡易版活動判定クラス"""
    
    def __init__(self, threshold_days: int = 60):
        self.threshold_days = threshold_days
        self.threshold_date = datetime.now() - timedelta(days=threshold_days)
    
    async def get_page_content(self, url: str) -> Optional[str]:
        """ページのテキストコンテンツを取得"""
        if not PLAYWRIGHT_AVAILABLE:
            return None
            
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
                page = await context.new_page()
                
                await page.goto(url, timeout=30000, wait_until='domcontentloaded')
                
                # ニュースページへのリンクを探す
                links = await page.evaluate("""
                    Array.from(document.querySelectorAll('a')).map(a => ({
                        text: a.innerText.toLowerCase(),
                        href: a.href
                    }))
                """)
                
                news_url = None
                for link in links:
                    for kw in NEWS_KEYWORDS:
                        if kw in link['text'] or kw in link['href'].lower():
                            news_url = link['href']
                            break
                    if news_url:
                        break
                
                # ニュースページがあれば移動
                if news_url and news_url != url:
                    try:
                        await page.goto(news_url, timeout=30000, wait_until='domcontentloaded')
                    except:
                        pass
                
                # テキスト取得
                text = await page.evaluate("document.body.innerText")
                return text
                
            except Exception as e:
                print(f"  ✗ アクセスエラー: {e}")
                return None
            finally:
                await browser.close()
    
    async def check_facility(self, url: str, facility_name: str = "") -> Dict[str, Any]:
        """施設の活動状況を判定"""
        print(f"  チェック中: {facility_name or url}")
        
        content = await self.get_page_content(url)
        
        if not content:
            return {
                "facility_name": facility_name,
                "url": url,
                "status": "unknown",
                "reason": "ページにアクセスできませんでした",
                "latest_date": None
            }
        
        # 日付抽出
        dates = extract_dates_from_text(content)
        
        if not dates:
            return {
                "facility_name": facility_name,
                "url": url,
                "status": "unknown",
                "reason": "日付情報が見つかりませんでした",
                "latest_date": None
            }
        
        # 最新日付を取得
        latest_date = max(dates)
        is_active = latest_date >= self.threshold_date
        
        return {
            "facility_name": facility_name,
            "url": url,
            "status": "active" if is_active else "dormant",
            "reason": f"最新更新: {latest_date.strftime('%Y-%m-%d')}",
            "latest_date": latest_date.strftime('%Y-%m-%d'),
            "is_active": is_active
        }
    
    async def check_all_facilities(self, facilities: List[Dict]) -> List[Dict]:
        """全施設をチェック"""
        results = []
        
        for facility in facilities:
            url = facility.get('website')
            name = facility.get('name', '')
            
            if not url:
                continue
                
            result = await self.check_facility(url, name)
            result['facility_id'] = facility.get('id')
            results.append(result)
            
            # レート制限（1秒待機）
            await asyncio.sleep(1)
        
        return results


async def main():
    """テスト実行"""
    checker = SimpleActivityChecker()
    
    # テスト用施設
    test_facilities = [
        {"id": "test1", "name": "Tokyo Innovation Base", "website": "https://tib.metro.tokyo.lg.jp/"},
        {"id": "test2", "name": "Venture Cafe Tokyo", "website": "https://venturecafetokyo.org/"},
    ]
    
    print("\n=== 簡易版 活動判定テスト ===\n")
    results = await checker.check_all_facilities(test_facilities)
    
    print("\n=== 結果 ===")
    for r in results:
        status_emoji = "✅" if r.get('is_active') else "💤" if r['status'] == 'dormant' else "❓"
        print(f"{status_emoji} {r['facility_name']}: {r['status']} ({r['reason']})")


if __name__ == "__main__":
    asyncio.run(main())
