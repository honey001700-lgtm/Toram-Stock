# daily_report.py
import os
import requests
import pandas as pd
import datetime
import json

# 引用模組
from utils.preprocess import load_data, filter_and_prepare_data
from utils.regression import calculate_r_squared
from analysis.trend import analyze_trend
from analysis.patterns import detect_patterns, detect_events

# 設定
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtSvfsvYpDjQutAO9L4AV1Rq8XzZAQEAZcLZxl9JsSvxCo7X2JsaFTVdTAQwGNQRC2ySe5OPJaTzp9/pub?gid=915078159&single=true&output=csv"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord_webhook(embeds):
    if not DISCORD_WEBHOOK_URL:
        print("❌ 未設定 DISCORD_WEBHOOK_URL")
        return

    payload = {
        "username": "托蘭市場分析師",
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
    print("🚀 SYSTEM CHECK: 腳本開始執行...")
    print("📥 開始下載數據...")
    df, err = load_data(SHEET_URL)
    
    if df.empty:
        print(f"❌ 數據為空: {err}")
        return

    # 1. 時間範圍
    now = datetime.datetime.now()
    yesterday = now - pd.Timedelta(hours=24)
    
    # 活躍物品
    recent_df = df[df['時間'] >= yesterday]
    active_items = recent_df['物品'].unique().tolist()
    
    print(f"🔍 過去 24 小時共有 {len(active_items)} 個活躍物品。")
    
    highlights = []

    # 2. 分析
    for item in active_items:
        item_df = filter_and_prepare_data(df, item)
        if len(item_df) < 5: continue 

        # 跑分析
        r_squared, _ = calculate_r_squared(item_df)
        trend = analyze_trend(item_df)
        patterns = detect_patterns(item_df)
        events = detect_events(item_df)
        
        # 計算漲跌
        latest_price = item_df.iloc[-1]['單價']
        try:
            prev_price_row = item_df[item_df['時間'] <= yesterday].iloc[-1]
            prev_price = prev_price_row['單價']
        except IndexError:
            prev_price = item_df.iloc[0]['單價']
            
        change_pct = ((latest_price - prev_price) / prev_price) * 100 if prev_price else 0
        
        # --- 3. 篩選邏輯 ---
        tags = [] 
        is_highlight = False

        # A. 價格劇烈波動
        if abs(change_pct) >= 10:
            is_highlight = True
            
        # B. 強趨勢
        if r_squared and r_squared >= 0.75 and trend['多空強度'] > 70:
            is_highlight = True
            
        # C. 型態 (存入 tags)
        target_patterns = ["頭肩", "雙重", "三角", "通道"]
        found_p = [p['type'] for p in patterns if any(k in p['type'] for k in target_patterns)]
        if found_p:
            for p in found_p:
                tags.append(f"型態: {p}")
            is_highlight = True
            
        # D. 事件 (存入 tags)
        event_types = [e['type'] for e in events if "新高" in e['type'] or "新低" in e['type']]
        if event_types:
            for e in event_types:
                tags.append(f"事件: {e}")
            is_highlight = True

        if is_highlight:
            highlights.append({
                "item": item,
                "price": latest_price,
                "change_pct": change_pct,
                "tags": tags,
                "trend": trend['趨勢方向']
            })

    # --- 4. 製作 Discord 報告 (清單樣式) ---
    embeds = []
    
    # 標題區
    summary_text = f"監測 {len(active_items)} 個物品 | 發現 {len(highlights)} 個重點關注"
    if not highlights:
        summary_text += "\n😴 市場平靜，無重大波動。"

    embeds.append({
        "title": f"📅 托蘭交易所日報 ({now.strftime('%Y-%m-%d')})",
        "description": summary_text,
        "color": 3447003, 
        "footer": {"text": "由 Streamlit Python Bot 自動生成"}
    })

    # 內容區
    if highlights:
        # 依波動幅度排序
        highlights.sort(key=lambda x: abs(x['change_pct']), reverse=True)
        
        fields = []
        # 限制顯示數量 (例如最多 15 個)，避免超過 Discord 限制
        for h in highlights[:15]: 
            
            lines = []
            
            # 第一行：價格
            lines.append(f"- 💰 ${h['price']:,.0f}")
            
            # 第二行：漲跌幅
            if h['change_pct'] > 0:
                lines.append(f"- 🚀 24h漲跌: +{h['change_pct']:.1f}%")
            elif h['change_pct'] < 0:
                lines.append(f"- 🩸 24h漲跌: {h['change_pct']:.1f}%")
            else:
                lines.append(f"- ➖ 24h平盤")
            
            # 第三行以後：事件或型態 (如果有的話)
            for tag in h['tags']:
                lines.append(f"- {tag}")

            # 組合字串
            value_text = "\n".join(lines)

            fields.append({
                "name": f"💎 {h['item']}",
                "value": value_text,
                "inline": True # ✅ 設為 True 開啟並排
            })
            
        embeds.append({
            "title": "🚨 市場焦點掃描",
            "color": 15158332, 
            "fields": fields
        })

    print("📤 準備發送 Discord...")
    send_discord_webhook(embeds)

if __name__ == "__main__":
    main()