# daily_report.py
import os
import requests
import pandas as pd
import datetime
import time
# 👇 改用 Google 官方 SDK，更穩定
import google.generativeai as genai 

from utils.preprocess import load_data, filter_and_prepare_data
from analysis.trend import analyze_trend
from analysis.patterns import detect_patterns, detect_events

# ==========================================
# 🔑 設定區
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtSvfsvYpDjQutAO9L4AV1Rq8XzZAQEAZcLZxl9JsSvxCo7X2JsaFTVdTAQwGNQRC2ySe5OPJaTzp9/pub?gid=915078159&single=true&output=csv"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# ==========================================
# 🤖 AI 寫手核心 (官方 SDK 版)
# ==========================================
def generate_ai_script(market_stats, highlights):
    
    # --- 1. 定義備用文案 (如果 AI 還是掛掉，至少有東西看) ---
    def get_backup_script():
        print("🛡️ 啟用備用文案模式...")
        mood = "📈 市場熱度上升中！" if market_stats['up'] > market_stats['down'] else "📉 市場稍顯冷清..."
        
        top_item = highlights[0] if highlights else None
        highlight_text = ""
        if top_item:
            highlight_text = f"今日焦點是 {top_item['item']}，幅度達 {top_item['change_pct']:.1f}%！"

        return f"""(系統自動生成) 各位冒險者好！🤖\n{mood}\n本日上漲 {market_stats['up']} 家，下跌 {market_stats['down']} 家。\n{highlight_text}\n(AI 分析師目前連線忙碌中，以上為自動播報)\n祝大家打寶順利！""", 0

    if not GEMINI_API_KEY:
        print("⚠️ 未設定 API Key")
        return get_backup_script()

    # --- 2. 設定 Google SDK ---
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"❌ SDK 設定失敗: {e}")
        return get_backup_script()

    # --- 3. 準備提示詞 ---
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %A")
    
    top_movers_str = ""
    for h in highlights[:3]: 
        tags_str = ", ".join(h['tags']) if h['tags'] else "無"
        top_movers_str += f"- {h['item']}: {h['change_pct']:+.1f}% (${h['price']:,.0f}) [{tags_str}]\n"

    prompt = f"""
    角色：托蘭虛寶交易分析師(托蘭小姊姊)。語氣：活潑、溫暖、專業，像台灣 YouTuber。
    數據：{date_str}，上漲{market_stats['up']}家 / 下跌{market_stats['down']}家。
    焦點物品：\n{top_movers_str}
    任務：寫一篇約 200 字的 Discord 日報。
    結構：1.開場問候 2.盤勢多空判斷 3.重點物品點評(漲則興奮,跌則提醒) 4.結尾祝福。
    要求：使用 Emoji，不要太生硬。
    """

    # --- 4. 嘗試多個模型名稱 (SDK 會自動處理網址) ---
    # 這裡列出最穩定的幾個名稱
    model_candidates = [
        "gemini-2.0-flash-exp", # 最新實驗版
        "gemini-1.5-flash",     # 通用別名
        "gemini-1.5-flash-001", # 指定版本
        "gemini-1.5-flash-latest" 
    ]

    for model_name in model_candidates:
        try:
            print(f"🧠 正在呼叫模型: {model_name} ...")
            model = genai.GenerativeModel(model_name)
            
            # 設定生成參數 (降低隨機性，避免亂講話)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7
                )
            )
            
            if response.text:
                print(f"✅ {model_name} 生成成功！")
                color = 5763719 if market_stats['up'] >= market_stats['down'] else 15548997
                return response.text, color
                
        except Exception as e:
            # 這裡會印出具體錯誤，例如 "404 Not Found" 或 "429 Resource Exhausted"
            print(f"⚠️ {model_name} 失敗: {e}")
            time.sleep(1) # 稍微休息一下再試下一個
            continue

    print("❌ 所有 AI 模型嘗試皆失敗。")
    return get_backup_script()

# ==========================================
# 🛠️ Discord 發送功能
# ==========================================
def send_discord_webhook(embeds):
    if not DISCORD_WEBHOOK_URL:
        print("❌ 未設定 DISCORD_WEBHOOK_URL")
        return

    payload = {
        "username": "托蘭 AI 分析師",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png",
        "embeds": embeds
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("✅ Discord 通知發送成功！")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

# ==========================================
# 🚀 主程式
# ==========================================
def main():
    print("🚀 SYSTEM CHECK: 腳本開始執行...")
    
    # 1. 讀取數據
    print("📥 開始下載數據...")
    df, err = load_data(SHEET_URL)
    
    if df.empty:
        print(f"❌ 數據為空: {err}")
        return

    # 2. 時間範圍 (24h)
    now = datetime.datetime.now()
    yesterday = now - pd.Timedelta(hours=24)
    if not pd.api.types.is_datetime64_any_dtype(df['時間']):
        df['時間'] = pd.to_datetime(df['時間'])

    recent_df = df[df['時間'] >= yesterday]
    active_items = recent_df['物品'].unique().tolist()
    
    print(f"🔍 過去 24 小時共有 {len(active_items)} 個活躍物品。")
    
    highlights = []
    market_stats = {'up': 0, 'down': 0, 'total': 0}

    # 3. 分析物品
    for item in active_items:
        item_df = filter_and_prepare_data(df, item)
        if len(item_df) < 5: continue 

        latest_price = item_df.iloc[-1]['單價']
        try:
            prev_price = item_df[item_df['時間'] <= yesterday].iloc[-1]['單價']
        except IndexError:
            prev_price = item_df.iloc[0]['單價']
            
        change_pct = ((latest_price - prev_price) / prev_price) * 100 if prev_price else 0
        
        market_stats['total'] += 1
        if change_pct > 0: market_stats['up'] += 1
        elif change_pct < 0: market_stats['down'] += 1

        # 篩選 Highlight
        trend = analyze_trend(item_df)
        patterns = detect_patterns(item_df)
        events = detect_events(item_df)
        
        tags = []
        is_high = False
        if abs(change_pct) >= 10: is_high = True
        
        for p in patterns:
            if any(k in p['type'] for k in ["頭肩", "雙重", "三角", "通道"]):
                tags.append(p['type'])
        
        for e in events:
            if "新高" in e['type'] or "新低" in e['type']:
                tags.append(e['type'])

        if is_high or tags:
            highlights.append({
                "item": item,
                "price": latest_price,
                "change_pct": change_pct,
                "tags": tags
            })

    # 4. 生成 AI 報告
    if highlights:
        highlights.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    
    ai_script, color = generate_ai_script(market_stats, highlights)

    # 5. 製作 Embeds
    embeds = []
    
    embeds.append({
        "title": f"🎙️ 托蘭市場日報 ({now.strftime('%m/%d')})",
        "description": ai_script,
        "color": color,
        "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png"}
    })

    if highlights:
        fields = []
        for h in highlights[:8]: 
            emoji = "🚀" if h['change_pct'] > 0 else ("🩸" if h['change_pct'] < 0 else "➖")
            tag_display = f"\n└ {', '.join(h['tags'])}" if h['tags'] else ""

            fields.append({
                "name": f"{h['item']}",
                "value": f"{emoji} {h['change_pct']:+.1f}% | ${h['price']:,.0f}{tag_display}",
                "inline": True
            })
            
        embeds.append({
            "title": "📋 精選數據看板",
            "color": 3447003,
            "fields": fields
        })

    # 6. 發送
    print("📤 準備發送 Discord...")
    send_discord_webhook(embeds)

if __name__ == "__main__":
    main()