"""
行政書士向けスタートアップイベント集約システム
Streamlit メインダッシュボード
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from pathlib import Path

# パス設定
import sys
sys.path.insert(0, str(Path(__file__).parent))

from config import DATA_DIR, HIGH_PRIORITY_KEYWORDS
from core.database import (
    init_database, 
    get_all_facilities, 
    get_upcoming_events, 
    get_statistics,
    get_events,
    load_initial_facilities
)
from core.scorer import get_priority_label, get_priority_color, rank_events
from core.dormant_checker import (
    get_facility_health_report, 
    update_all_facility_statuses,
    get_active_facilities,
    get_dormant_facilities,
    get_new_facilities
)


# ページ設定
st.set_page_config(
    page_title="スタートアップイベント集約システム",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    .priority-high {
        background-color: #ff4444;
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
    }
    .priority-medium {
        background-color: #ffcc00;
        color: #333;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
    }
    .event-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        transition: box-shadow 0.2s;
    }
    .event-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .facility-status-active {
        color: #28a745;
        font-weight: bold;
    }
    .facility-status-dormant {
        color: #ffc107;
    }
    .facility-status-new {
        color: #17a2b8;
    }
</style>
""", unsafe_allow_html=True)


def init_app():
    """アプリケーション初期化"""
    if 'initialized' not in st.session_state:
        init_database()
        load_initial_facilities()
        st.session_state.initialized = True


def main():
    """メイン関数"""
    init_app()
    
    # サイドバー
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/rocket.png", width=60)
        st.title("🚀 イベント集約")
        st.markdown("---")
        
        page = st.radio(
            "ページ選択",
            ["📊 ダッシュボード", "📅 イベント一覧", "📆 カレンダー", "🏢 施設管理", "📈 分析", "📖 Tips"]
        )
        
        st.markdown("---")
        st.caption(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        if st.button("🔄 データ更新", use_container_width=True):
            with st.spinner("更新中..."):
                update_all_facility_statuses()
            st.success("更新完了!")
    
    # ページ表示
    if page == "📊 ダッシュボード":
        show_dashboard()
    elif page == "📅 イベント一覧":
        show_events()
    elif page == "📆 カレンダー":
        show_calendar()
    elif page == "🏢 施設管理":
        show_facilities()
    elif page == "📈 分析":
        show_analytics()
    elif page == "📖 Tips":
        show_tips()


def show_dashboard():
    """ダッシュボード表示"""
    st.markdown('<h1 class="main-header">📊 ダッシュボード</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">補助金ニーズのある起業家と出会えるイベントを効率的に発見</p>', unsafe_allow_html=True)
    
    # 統計カード
    col1, col2, col3, col4 = st.columns(4)
    
    stats = get_statistics()
    facility_stats = stats.get('facility_stats', {})
    
    with col1:
        st.metric("🏢 アクティブ施設", facility_stats.get('active', 0))
    
    with col2:
        st.metric("💤 休眠施設", facility_stats.get('dormant', 0))
    
    with col3:
        st.metric("🆕 新規施設", facility_stats.get('new', 0))
    
    with col4:
        st.metric("📅 登録イベント", stats.get('event_count', 0))
    
    st.markdown("---")
    
    # 今後のおすすめイベント
    st.subheader("🔥 今後のおすすめイベント（高プライオリティ）")
    
    events = get_upcoming_events(days=30, min_score=50)
    ranked_events = rank_events(events) if events else []
    
    if ranked_events:
        for event in ranked_events[:10]:
            col1, col2 = st.columns([5, 1])
            with col1:
                priority_label = event.get('priority_label', '📋 -')
                score = event.get('priority_score', 0)
                st.markdown(f"""
                **{priority_label}** [{score}点] **{event.get('title', 'タイトル不明')}**  
                📅 {event.get('event_date', '日付不明')} | 🏢 {event.get('facility_name', '施設不明')} | 📍 {event.get('prefecture', '')}
                """)
            with col2:
                if event.get('source_url'):
                    st.link_button("詳細 →", event['source_url'])
            st.markdown("---")
    else:
        st.info("今後のイベントはまだ登録されていません。データを取得してください。")
    
    # 2026年新規施設
    st.subheader("🆕 2026年注目の新拠点")
    
    new_facilities_file = DATA_DIR / "new_facilities_2026.json"
    if new_facilities_file.exists():
        with open(new_facilities_file, 'r', encoding='utf-8') as f:
            new_facilities = json.load(f)
        
        for facility in new_facilities[:5]:
            priority = facility.get('priority', 'medium')
            priority_emoji = "🔥" if priority == 'high' else "📌"
            
            st.markdown(f"""
            {priority_emoji} **{facility.get('name', '')}** ({facility.get('prefecture', '')} {facility.get('city', '')})  
            📅 開業: {facility.get('opening_date', '不明')} | 💡 {facility.get('notes', '')[:50]}...  
            🎯 **アプローチ戦略**: {facility.get('approach_strategy', '')}
            """)
            st.markdown("---")


def show_events():
    """イベント一覧表示"""
    st.markdown('<h1 class="main-header">📅 イベント一覧</h1>', unsafe_allow_html=True)
    
    # フィルター
    col1, col2, col3 = st.columns(3)
    
    with col1:
        min_score = st.slider("最低スコア", 0, 100, 30, step=10)
    
    with col2:
        from_date = st.date_input("開始日", datetime.now())
    
    with col3:
        to_date = st.date_input("終了日", datetime.now() + timedelta(days=60))
    
    # イベント取得
    events = get_events(
        from_date=from_date.strftime("%Y-%m-%d"),
        to_date=to_date.strftime("%Y-%m-%d"),
        min_score=min_score
    )
    
    ranked_events = rank_events(events) if events else []
    
    if ranked_events:
        # DataFrameで表示
        df = pd.DataFrame([
            {
                "優先度": e.get('priority_label', '-'),
                "スコア": e.get('priority_score', 0),
                "タイトル": e.get('title', '')[:40],
                "日付": e.get('event_date', ''),
                "場所": e.get('venue', '')[:20],
                "ソース": e.get('source', ''),
                "URL": e.get('source_url', '')
            }
            for e in ranked_events
        ])
        
        st.dataframe(
            df,
            column_config={
                "URL": st.column_config.LinkColumn("リンク")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("条件に一致するイベントがありません。")


def show_calendar():
    """カレンダー表示"""
    st.markdown('<h1 class="main-header">📆 イベントカレンダー</h1>', unsafe_allow_html=True)
    
    import calendar
    
    # 月選択
    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("年", [2025, 2026, 2027], index=1)
    with col2:
        month = st.selectbox("月", list(range(1, 13)), index=datetime.now().month - 1)
    
    # イベント取得
    first_day = f"{year}-{month:02d}-01"
    last_day = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"
    
    events = get_events(from_date=first_day, to_date=last_day)
    
    # 日付ごとにグループ化
    events_by_date = {}
    for event in events:
        date = event.get('event_date', '')
        if date not in events_by_date:
            events_by_date[date] = []
        events_by_date[date].append(event)
    
    st.markdown(f"### {year}年{month}月")
    
    # カレンダーグリッド表示
    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり
    weeks = cal.monthdayscalendar(year, month)
    
    # ヘッダー
    header_cols = st.columns(7)
    for i, day_name in enumerate(['日', '月', '火', '水', '木', '金', '土']):
        color = '#ff6b6b' if i == 0 else '#4dabf7' if i == 6 else '#333'
        header_cols[i].markdown(f"<div style='text-align:center;color:{color};font-weight:bold;'>{day_name}</div>", unsafe_allow_html=True)
    
    # カレンダー本体
    for week in weeks:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].markdown("")
            else:
                date_str = f"{year}-{month:02d}-{day:02d}"
                day_events = events_by_date.get(date_str, [])
                
                # スタイル決定
                if day_events:
                    bg_color = '#e8f5e9'
                    badge = f"<span style='background:#4caf50;color:white;border-radius:4px;padding:2px 6px;font-size:0.8em;'>{len(day_events)}</span>"
                else:
                    bg_color = '#fff'
                    badge = ""
                
                with cols[i]:
                    st.markdown(f"""
                    <div style='background:{bg_color};padding:8px;border-radius:8px;min-height:60px;border:1px solid #eee;'>
                        <strong>{day}</strong> {badge}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # イベントがあればポップオーバー的に表示
                    if day_events:
                        with st.expander(f"📅 {len(day_events)}件", expanded=False):
                            for ev in day_events[:3]:
                                st.caption(f"• {ev.get('title', '')[:30]}")
    
    st.markdown("---")
    
    # 今月のイベントリスト
    st.subheader("📋 今月のイベント一覧")
    if events:
        for event in sorted(events, key=lambda x: x.get('event_date', ''))[:20]:
            st.markdown(f"""
            **{event.get('event_date', '')}** - {event.get('title', '')}  
            🏢 {event.get('venue', '会場不明')[:30]}
            """)
    else:
        st.info("今月のイベントはありません。")


def show_facilities():
    """施設管理表示"""
    st.markdown('<h1 class="main-header">🏢 施設管理</h1>', unsafe_allow_html=True)
    
    # 活動チェック実行ボタン
    col1, col2, col3 = st.columns([2, 2, 4])
    with col1:
        if st.button("🔍 活動状況をチェック", use_container_width=True):
            st.info("活動チェックはコマンドラインから実行してください:")
            st.code("python3 scripts/check_all_facilities.py", language="bash")
            st.caption("※ 122施設のチェックに約5〜10分かかります")
    
    with col2:
        total_count = len(get_all_facilities())
        st.metric("登録施設数", total_count)
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["✅ アクティブ", "💤 休眠", "🆕 新規（監視中）"])
    
    with tab1:
        facilities = get_active_facilities()
        if facilities:
            df = pd.DataFrame(facilities)
            # ソースカラムを追加
            df['source_type'] = df['id'].apply(lambda x: 'CSV取込' if str(x).startswith('csv_') else '初期データ')
            
            display_cols = ['name', 'prefecture', 'city', 'website', 'last_event_date', 'source_type']
            available_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[available_cols], hide_index=True, use_container_width=True)
        else:
            st.info("アクティブな施設はありません。")
    
    with tab2:
        facilities = get_dormant_facilities()
        if facilities:
            st.warning("⚠️ 以下の施設は2ヶ月以上イベントがありません")
            
            for facility in facilities:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"**{facility.get('name', '')}** ({facility.get('prefecture', '')}) - 最終: {facility.get('last_event_date', '不明')}")
                with col2:
                    if st.button("復活 ↩️", key=f"restore_{facility.get('id')}"):
                        from core.database import update_facility_status
                        update_facility_status(facility['id'], 'active', None, '手動復活')
                        st.success(f"✅ {facility.get('name')} をアクティブに戻しました")
                        st.rerun()
        else:
            st.success("休眠施設はありません！")
    
    with tab3:
        facilities = get_new_facilities()
        if facilities:
            st.info("🔍 以下の施設は監視中です（イベント実績なし）")
            df = pd.DataFrame(facilities)
            display_cols = ['name', 'prefecture', 'notes']
            available_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[available_cols], hide_index=True, use_container_width=True)
        else:
            st.info("新規監視中の施設はありません。")


def show_analytics():
    """分析表示"""
    st.markdown('<h1 class="main-header">📈 分析</h1>', unsafe_allow_html=True)
    
    report = get_facility_health_report()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("施設ステータス分布")
        status_data = {
            'アクティブ': report.get('active', 0),
            '休眠': report.get('dormant', 0),
            '新規': report.get('new', 0),
        }
        st.bar_chart(status_data)
    
    with col2:
        st.subheader("都道府県別施設数")
        pref_data = report.get('by_prefecture', {})
        if pref_data:
            pref_df = pd.DataFrame([
                {'都道府県': k, 'アクティブ': v.get('active', 0), '休眠': v.get('dormant', 0)}
                for k, v in pref_data.items()
            ])
            st.dataframe(pref_df, hide_index=True)


def show_tips():
    """行政書士向けTips表示"""
    st.markdown('<h1 class="main-header">📖 行政書士向けTips</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">「補助金の人」として認識されるための最短コミュニケーション術</p>', unsafe_allow_html=True)
    
    st.markdown("""
    ## 🎯 自己紹介テンプレート
    
    > 「行政書士の○○です。**スタートアップ向けの補助金申請を専門**にしています。
    > 創業助成金やものづくり補助金など、**採択率80%以上**の実績があります。」
    
    ---
    
    ## 🎪 イベント別アプローチ戦略
    
    ### 🔥 ピッチイベント（スコア: 100点）
    - **タイミング**: 登壇者のピッチ終了直後
    - **アプローチ**: 「素晴らしいプレゼンでした！資金調達の次のステップとして補助金という選択肢もありますよ」
    - **ポイント**: 審査員や投資家と同じタイミングで名刺交換
    
    ### 🤝 交流会・ネットワーキング（スコア: 90点）
    - **会話の入り方**: 「何のビジネスをされていますか？」
    - **展開**: 「その事業なら○○補助金が使えるかもしれません」
    - **クロージング**: 「詳しくお話しませんか？名刺交換させてください」
    
    ### 🛠️ ワークショップ（スコア: 70点）
    - グループワーク中にさりげなく専門性をアピール
    - 「資金面で悩んでいる方がいたら、補助金のことなら相談に乗りますよ」
    
    ---
    
    ## 📋 持ち物チェックリスト
    
    - [ ] **名刺** - 裏面に「スタートアップ支援専門」と記載
    - [ ] **採択実績リスト** - 直近5件の採択事例を1枚にまとめる
    - [ ] **補助金カレンダー** - 次回締切の補助金一覧
    - [ ] **QRコード付き資料** - LINE公式や予約ページへ誘導
    
    ---
    
    ## 💡 声かけフレーズ集
    
    | シーン | フレーズ |
    |--------|----------|
    | 開始時 | 「どんな事業をされていますか？」 |
    | 興味を引く | 「最大○○万円の補助金があるんですよ」 |
    | 具体化 | 「申請書類は私が全部作成しますので、ご負担は最小限です」 |
    | クロージング | 「一度30分だけ無料相談しませんか？」 |
    
    ---
    
    ## 🎯 狙うべき起業家の特徴
    
    1. **資金調達を検討中** - VCへのピッチ準備をしている
    2. **新製品・サービス開発中** - 開発費用がかかるフェーズ
    3. **海外展開を検討中** - 海外ビジネス関連の補助金
    4. **IT投資を検討中** - IT導入補助金の対象
    5. **設備投資を検討中** - ものづくり補助金の対象
    """)


if __name__ == "__main__":
    main()
