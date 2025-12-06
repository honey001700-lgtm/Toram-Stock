# daily_report.py
import os
import requests
import pandas as pd
import datetime
import json
import time

# 引用模組
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
# 🤖 AI 寫手核心 (修復版：多模型輪詢)
# ==========================================
def generate_ai_script(market_stats, highlights):
    
    # --- 1. 定義備案 (Plan B) ---
    def get_backup_script():
        print("🛡️ 啟用備用文案模式...")
        mood = "📈 市場熱度上升中！" if market_stats['up'] > market_stats['down'] else "📉 市場稍顯冷清..."
        top_item = highlights[0] if highlights else None
        highlight_text = ""
        if top_item:
            highlight_text = f"今日焦點是 {top_item['item']}，幅度達 {top_item['change_pct']:.1f}%！"
        return f"""(系統自動生成) 各位冒險者好！🤖\n{mood}\n本日上漲 {market_stats['up']} 家，下跌 {market_stats['down']} 家。\n{highlight_text}\n祝大家打寶順利！""", 0

    if not GEMINI_API_KEY:
        return get_backup_script()

    # --- 2. 準備 Prompt ---
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %A")
    top_movers_str = ""
    for h in highlights[:3]: 
        tags_str = ", ".join(h['tags']) if h['tags'] else "無"
        top_movers_str += f"- {h['item']}: {h['change_pct']:+.1f}% (${h['price']:,.0f}) [{tags_str}]\n"

    prompt = f"""
    角色：托蘭虛寶交易分析師(托蘭小姊姊)。語氣：活潑專業台灣口語。
    數據：{date_str}，漲{market_stats['up']}/跌{market_stats['down']}。
    焦點：\n{top_movers_str}
    任務：寫200字日報。1.開場 2.行情點評 3.重點物品 4.結尾。
    """

    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}

    # --- 3. 定義模型清單 (解決 404 問題的核心) ---
    base_url = "https://generativelanguage.googleapis.com/v1beta/models"
    models = [
        # 優先嘗試 2.0 實驗版 (名稱要加 -exp)
        ("gemini-2.0-flash-exp", f"{base_url}/gemini-2.0-flash-exp:generateContent?key={GEMINI_API_KEY}"),
        # 嘗試 1.5 Flash 指定版本 (解決 alias 404 問題)
        ("gemini-1.5-flash-001", f"{base_url}/gemini-1.5-flash-001:generateContent?key={GEMINI_API_KEY}"),
        # 嘗試 1.5 Flash 通用名稱
        ("gemini-1.5-flash", f"{base_url}/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"),
        # 最後嘗試 1.5 Pro
        ("gemini-1.5-pro", f"{base_url}/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}"),
    ]

    # --- 4. 輪詢呼叫 ---
    for model_name, url in models:
        try:
            print(f"🧠 嘗試呼叫 {model_name}...")
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                text = result['candidates'][0]['content']['parts'][0]['text']
                color = 5763719 if market_stats['up'] >= market_stats['down'] else 15548997
                return text, color
            elif response.status_code == 429:
                print(f"⏳ {model_name} 忙碌中 (429)，休息 2 秒...")
                time.sleep(2)
            else:
                print(f"⚠️ {model_name} 失敗 ({response.status_code})，嘗試下一個...")
                
        except Exception as e:
            print(f"❌ {model_name} 發生錯誤: {e}")
            continue

    print("❌ 所有 AI 模型皆失敗，切換備案。")
    return get_backup_script()

# ==========================================
# 🛠️ Discord 發送
# ==========================================
def send_discord_webhook(embeds):
    if not DISCORD_WEBHOOK_URL: return
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={
            "username": "托蘭 AI 分析師",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png",
            "embeds": embeds
        })
        print("✅ Discord 通知發送成功！")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

# ==========================================
# 🚀 主程式
# ==========================================
def main():
    print("🚀 腳本開始...")
    df, err = load_data(SHEET_URL)
    if df.empty: return

    # 資料處理
    now = datetime.datetime.now()
    yesterday = now - pd.Timedelta(hours=24)
    if not pd.api.types.is_datetime64_any_dtype(df['時間']):
        df['時間'] = pd.to_datetime(df['時間'])

    active_items = df[df['時間'] >= yesterday]['物品'].unique().tolist()
    highlights = []
    market_stats = {'up': 0, 'down': 0, 'total': 0}

    for item in active_items:
        item_df = filter_and_prepare_data(df, item)
        if len(item_df) < 5: continue 

        latest = item_df.iloc[-1]['單價']
        try:
            prev = item_df[item_df['時間'] <= yesterday].iloc[-1]['單價']
        except:
            prev = item_df.iloc[0]['單價']
            
        change = ((latest - prev) / prev) * 100 if prev else 0
        
        market_stats['total'] += 1
        if change > 0: market_stats['up'] += 1
        elif change < 0: market_stats['down'] += 1

        patterns = detect_patterns(item_df)
        events = detect_events(item_df)
        tags = [p['type'] for p in patterns if any(x in p['type'] for x in ["頭肩", "雙重", "三角"])]
        tags += [e['type'] for e in events if "新高" in e['type'] or "新低" in e['type']]

        if abs(change) >= 10 or tags:
            highlights.append({"item": item, "price": latest, "change_pct": change, "tags": tags})

    highlights.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    
    # 生成內容
    ai_script, color = generate_ai_script(market_stats, highlights)

    embeds = [{
        "title": f"🎙️ 托蘭市場日報 ({now.strftime('%m/%d')})",
        "description": ai_script,
        "color": color,
        "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png"}
    }]

    if highlights:
        fields = []
        for h in highlights[:8]: 
            emoji = "🚀" if h['change_pct'] > 0 else ("🩸" if h['change_pct'] < 0 else "➖")
            tag_display = f"\n└ {', '.join(h['tags'])}" if h['tags'] else ""
            fields.append({
                "name": h['item'],
                "value": f"{emoji} {h['change_pct']:+.1f}% | ${h['price']:,.0f}{tag_display}",
                "inline": True
            })
        embeds.append({"title": "📋 精選數據", "color": 3447003, "fields": fields})

    send_discord_webhook(embeds)

if __name__ == "__main__":
    main()