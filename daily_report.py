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

# ==========================================
# 🔑 設定區
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtSvfsvYpDjQutAO9L4AV1Rq8XzZAQEAZcLZxl9JsSvxCo7X2JsaFTVdTAQwGNQRC2ySe5OPJaTzp9/pub?gid=915078159&single=true&output=csv"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
# 使用 strip() 去除可能不小心複製到的空白鍵
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# ==========================================
# 🤖 AI 寫手核心 (針對 Gemini 2.0 Flash 優化)
# ==========================================
def generate_ai_script(market_stats, highlights):
    """
    使用 REST API 強制呼叫 Gemini 2.0 Flash
    """
    if not GEMINI_API_KEY:
        print("⚠️ 警告：未設定 GEMINI_API_KEY")
        return "⚠️ (系統訊息) 管理員尚未設定 AI 金鑰，無法生成分析報告。", 0

    # 1. 準備提示詞 (Prompt)
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %A")
    
    top_movers_str = ""
    for h in highlights[:3]: 
        tags_str = ", ".join(h['tags']) if h['tags'] else "無特殊型態"
        top_movers_str += f"- {h['item']}: 漲跌 {h['change_pct']:.1f}%, 現價 ${h['price']:,.0f}, 特徵: {tags_str}\n"

    prompt = f"""
    【角色設定】
    你是一位名叫「托蘭小姊姊」的虛擬寶物市場交易分析師。
    你的個性：溫暖、專業、像一位鄰家大姊姊，說話帶有台灣財經 YouTuber 的口語風格。
    【今日任務】
    請根據以下市場數據，寫一篇約 200 字的 Discord 日報。
    【市場數據】
    - 日期：{date_str}
    - 上漲家數：{market_stats['up']} | 下跌家數：{market_stats['down']}
    - 重點關注：\n{top_movers_str}
    【寫作要求】
    1. 開場問候 (根據星期幾變化)。
    2. 盤勢多空判斷與操作建議。
    3. 重點物品點評 (漲則興奮、跌則提醒)。
    4. 結尾簡短祝福。
    5. 使用 Markdown 與 Emoji，語氣流暢自然。
    """

    # 2. 設定 API 網址 (Gemini 2.0 Flash)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        print(f"🧠 正在呼叫 Gemini 2.0 Flash ...")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            color = 5763719 if market_stats['up'] >= market_stats['down'] else 15548997
            return text, color
        else:
            print(f"❌ Gemini API Error: {response.status_code}")
            # 如果 2.0 失敗 (例如地區限制)，自動降級回 1.5 Flash
            if response.status_code == 404:
                print("🔄 2.0 模型連線失敗，嘗試切換回 1.5-flash...")
                url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
                response_fb = requests.post(url_fallback, headers=headers, json=data)
                if response_fb.status_code == 200:
                    result = response_fb.json()
                    text = result['candidates'][0]['content']['parts'][0]['text']
                    return text, 5763719
            
            return f"機器人連線失敗 (HTTP {response.status_code})", 0

    except Exception as e:
        print(f"❌ Request Failed: {e}")
        return "機器人腦袋打結了 (網路錯誤)...", 0

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
        # 顯示前 8 名，避免版面太長
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