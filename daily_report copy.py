# daily_report.py
import os
import requests
import pandas as pd
import datetime
import json

# 引用你的現有模組
# 注意：utils.preprocess 裡面有 import streamlit，這在腳本模式下沒問題，但要確保環境有安裝 streamlit
from utils.preprocess import load_data, filter_and_prepare_data
from utils.regression import calculate_r_squared
from analysis.trend import analyze_trend
from analysis.patterns import detect_patterns, detect_events

# 設定
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtSvfsvYpDjQutAO9L4AV1Rq8XzZAQEAZcLZxl9JsSvxCo7X2JsaFTVdTAQwGNQRC2ySe5OPJaTzp9/pub?gid=915078159&single=true&output=csv"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord_webhook(embeds):
    if not DISCORD_WEBHOOK_URL:
        print("❌ 未設定 DISCORD_WEBHOOK_URL，跳過發送。")
        return

    payload = {
        "username": "托蘭市場分析師 (Toram Bot)",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/4202/4202568.png",
        "embeds": embeds
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("✅ Discord 通知發送成功！")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

def main():
    print("📥 開始下載數據...")
    # 這裡 load_data 可能會因為 @st.cache_data 在無 streamlit 環境下產生警告，通常可忽略
    df, err = load_data(SHEET_URL)
    
    if df.empty:
        print(f"❌ 數據為空: {err}")
        return

    # 1. 定義時間範圍：過去 24 小時
    now = datetime.datetime.now()
    yesterday = now - pd.Timedelta(hours=24)
    
    # 找出這 24 小時內有更新數據的物品 (活躍物品)
    recent_df = df[df['時間'] >= yesterday]
    active_items = recent_df['物品'].unique().tolist()
    
    print(f"🔍 過去 24 小時共有 {len(active_items)} 個活躍物品。")
    
    highlights = []

    # 2. 逐一分析活躍物品
    for item in active_items:
        # 取出該物品的"完整歷史"來做分析 (這樣趨勢和 MA 才會準)
        item_df = filter_and_prepare_data(df, item)
        
        if len(item_df) < 5: continue # 數據太少略過

        # --- 執行分析 ---
        r_squared, _ = calculate_r_squared(item_df)
        trend = analyze_trend(item_df)
        patterns = detect_patterns(item_df)
        events = detect_events(item_df) # 取得漲跌突變事件
        
        # 計算 24h 漲跌幅
        latest_price = item_df.iloc[-1]['單價']
        # 找 24 小時前的價格 (近似)
        try:
            prev_price_row = item_df[item_df['時間'] <= yesterday].iloc[-1]
            prev_price = prev_price_row['單價']
        except IndexError:
            prev_price = item_df.iloc[0]['單價'] # 如果 24 小時前沒資料，用最早的
            
        change_pct = ((latest_price - prev_price) / prev_price) * 100 if prev_price else 0
        
        # --- 3. 篩選報告條件 (Highlight Logic) ---
        reasons = []
        is_highlight = False

        # A. 價格劇烈波動 (>10%)
        if abs(change_pct) >= 10:
            emoji = "🚀" if change_pct > 0 else "🩸"
            reasons.append(f"{emoji} 24h漲跌: {change_pct:+.1f}%")
            is_highlight = True
            
        # B. 高 R² 且 強趨勢 (趨勢明確)
        if r_squared and r_squared >= 0.7 and trend['多空強度'] > 60:
            reasons.append(f"📈 強力趨勢 (R²: {r_squared:.2f})")
            is_highlight = True
            
        # C. 特殊型態偵測 (W底, M頭, 頭肩)
        important_patterns = ["頭肩", "雙重", "三角", "通道"]
        found_patterns = [p['type'] for p in patterns if any(k in p['type'] for k in important_patterns)]
        if found_patterns:
            reasons.append(f"👀 型態: {', '.join(found_patterns)}")
            is_highlight = True
            
        # D. 重大事件 (新高/新低)
        event_types = [e['type'] for e in events if "新高" in e['type'] or "新低" in e['type']]
        if event_types:
            reasons.append(f"🏆 事件: {', '.join(event_types)}")
            is_highlight = True

        if is_highlight:
            highlights.append({
                "item": item,
                "price": latest_price,
                "reasons": reasons,
                "trend": trend['趨勢方向']
            })

    # --- 4. 製作 Discord 報告 ---
    embeds = []
    
    # 標題卡片
    summary_text = f"監測 {len(active_items)} 個物品 | 發現 {len(highlights)} 個重點關注"
    if not highlights:
        summary_text += "\n😴 市場平靜，無重大波動。"
        
    embeds.append({
        "title": f"📅 托蘭交易所日報 ({now.strftime('%Y-%m-%d')})",
        "description": summary_text,
        "color": 3447003, # 藍色
        "footer": {"text": "由 Streamlit Python Bot 自動生成"}
    })

    # 重點物品列表 (分批處理，以免超過 Discord 限制)
    if highlights:
        # 依照 "關注度" 排序? 這裡簡單依價格排序
        highlights.sort(key=lambda x: x['price'], reverse=True)
        
        fields = []
        for h in highlights[:12]: # 最多顯示 12 個，避免版面太長
            reason_str = "\n".join(h['reasons'])
            fields.append({
                "name": f"💎 {h['item']}",
                "value": f"💰 ${h['price']:,}\n{reason_str}",
                "inline": True
            })
            
        embeds.append({
            "title": "🚨 市場焦點掃描",
            "color": 15158332, # 紅色
            "fields": fields
        })

    send_discord_webhook(embeds)

if __name__ == "__main__":
    main()