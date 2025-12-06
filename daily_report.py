# daily_report.py
import os
import requests
import pandas as pd
import datetime
import time
import google.generativeai as genai 

# 為了避免 Streamlit 的警告洗版，我們把它靜音
import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

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
# 🧠 AI 模型挑選與執行 (Flash 優先版)
# ==========================================
def generate_ai_script(market_stats, highlights):
    
    # --- 備用文案 (Plan B) ---
    def get_backup_script():
        print("🛡️ 啟用備用文案模式...")
        mood = "📈 市場熱度上升中！" if market_stats['up'] > market_stats['down'] else "📉 市場稍顯冷清..."
        top_item = highlights[0] if highlights else None
        highlight_text = ""
        if top_item:
            highlight_text = f"今日焦點是 {top_item['item']}，幅度達 {top_item['change_pct']:.1f}%！"
        return f"""(系統自動生成) 各位冒險者好！🤖\n{mood}\n本日上漲 {market_stats['up']} 家，下跌 {market_stats['down']} 家。\n{highlight_text}\n(AI 分析師連線休息中，以上為自動播報)\n祝大家打寶順利！""", 0

    if not GEMINI_API_KEY:
        print("⚠️ 未設定 API Key")
        return get_backup_script()

    # --- 1. 篩選出所有「Flash」模型 ---
    target_models = []
    try:
        print("🔍 正在查詢 Google 可用模型清單...")
        genai.configure(api_key=GEMINI_API_KEY)
        
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # 我們只想要 Flash (速度快、額度高)
        # 優先順序：2.0 Flash Exp -> 1.5 Flash -> 任何 Flash
        priority_list = [
            "gemini-2.0-flash-exp", 
            "gemini-1.5-flash", 
            "gemini-1.5-flash-002",
            "gemini-1.5-flash-001",
            "flash" # 只要名字裡有 flash 都抓進來
        ]

        # 依照優先順序建立候選名單
        seen = set()
        for p in priority_list:
            for m in all_models:
                if p in m and m not in seen:
                    target_models.append(m)
                    seen.add(m)
        
        print(f"📋 篩選後的 Flash 模型候選: {target_models}")

        if not target_models:
            print("⚠️ 沒找到任何 Flash 模型，將嘗試所有可用模型...")
            target_models = all_models

    except Exception as e:
        print(f"⚠️ 查詢模型失敗: {e}")
        # 如果查詢失敗，就盲猜這幾個最穩的
        target_models = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-001"]

    # --- 2. 準備提示詞 ---
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %A")
    top_movers_str = ""
    for h in highlights[:3]: 
        tags_str = ", ".join(h['tags']) if h['tags'] else "無"
        top_movers_str += f"- {h['item']}: {h['change_pct']:+.1f}% (${h['price']:,.0f}) [{tags_str}]\n"

    prompt = f"""
    角色：托蘭市場交易分析師(托蘭小姊姊)。語氣：客觀、冷靜、專業，像台灣 YouTuber。
    數據：{date_str}，上漲{market_stats['up']}家 / 下跌{market_stats['down']}家。
    焦點物品：\n{top_movers_str}
    任務：寫一篇約 200 字的 Discord 日報。
    結構：1.開場問候 2.盤勢多空判斷 3.重點物品點評(漲則興奮,跌則提醒) 4.結尾祝福。
    要求：重點在於數據分析，但情緒用語也不要太少。使用 Emoji，不要太生硬。
    """

    # --- 3. 輪詢呼叫 (失敗就換下一個) ---
    for model_name in target_models:
        try:
            print(f"🧠 嘗試呼叫: {model_name} ...")
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(temperature=0.7)
            )
            
            if response.text:
                print("✅ AI 寫作成功！")
                color = 5763719 if market_stats['up'] >= market_stats['down'] else 15548997
                return response.text, color

        except Exception as e:
            # 判斷是否為配額不足 (429)
            if "429" in str(e) or "quota" in str(e).lower():
                print(f"⏳ {model_name} 配額不足，切換下一個模型...")
            else:
                print(f"❌ {model_name} 執行失敗: {e}")
            
            time.sleep(1) # 稍微休息一下

    print("❌ 所有模型嘗試皆失敗。")
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
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print("✅ Discord 通知發送成功！")
    except Exception as e:
        print(f"❌ 發送失敗: {e}")

# ==========================================
# 🚀 主程式 (垂直條列式標籤版)
# ==========================================
def main():
    print("🚀 SYSTEM CHECK: 腳本開始執行...")
    
    # 1. 讀取數據
    df, err = load_data(SHEET_URL)
    if df.empty: return

    # 2. 時間範圍 (24h)
    now = datetime.datetime.now()
    yesterday = now - pd.Timedelta(hours=24)
    if not pd.api.types.is_datetime64_any_dtype(df['時間']):
        df['時間'] = pd.to_datetime(df['時間'])

    recent_df = df[df['時間'] >= yesterday]
    active_items = recent_df['物品'].unique().tolist()
    
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

        patterns = detect_patterns(item_df)
        events = detect_events(item_df)
        tags = [p['type'] for p in patterns if any(k in p['type'] for k in ["頭肩", "雙重", "三角"])]
        tags += [e['type'] for e in events if "新高" in e['type'] or "新低" in e['type']]

        if abs(change_pct) >= 10 or tags:
            highlights.append({
                "item": item,
                "price": latest_price,
                "change_pct": change_pct,
                "tags": tags
            })

    # 4. 生成 AI 報告
    highlights.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    
    ai_script, color = generate_ai_script(market_stats, highlights)

    # ==========================================
    # 🎨 5. 製作 Embeds (垂直標籤排版)
    # ==========================================
    embeds = []
    
    embeds.append({
        "title": f"🎙️ 托蘭市場日報 ({now.strftime('%m/%d')})",
        "description": ai_script,
        "color": color,
        "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png"}
    })

    if highlights:
        fields = []
        # 顯示前 15 名
        for h in highlights[:15]: 
            emoji = "🚀" if h['change_pct'] > 0 else ("🩸" if h['change_pct'] < 0 else "➖")
            
            # --- 標籤轉譯與排版邏輯 ---
            pretty_tags = []
            raw_tags = h.get('tags', [])
            
            for tag in raw_tags:
                if "新高" in tag: pretty_tags.append("🔥 創歷史新高")
                elif "新低" in tag: pretty_tags.append("🧊 創歷史新低")
                elif "頭肩頂" in tag: pretty_tags.append("👤 頭肩頂(看跌)")
                elif "頭肩底" in tag: pretty_tags.append("🧘 頭肩底(看漲)")
                elif "雙重頂" in tag: pretty_tags.append("⛰️ M頭(看跌)")
                elif "雙重底" in tag: pretty_tags.append("🇼 W底(看漲)")
                elif "三角" in tag: pretty_tags.append("📐 三角收斂")
                else: pretty_tags.append(tag) 

            # ✨ 關鍵修改：每個標籤都換行，並加上 '└ ' 前綴
            if pretty_tags:
                # 這裡會變成：
                # └ 🔥 創歷史新高
                # └ 📐 三角收斂
                tag_lines = "\n".join([f"└ {t}" for t in pretty_tags])
                tag_display = f"\n{tag_lines}"
            else:
                tag_display = ""
            
            fields.append({
                "name": f"{h['item']}", 
                "value": f"{emoji} `{h['change_pct']:+.1f}%` | ${h['price']:,.0f}{tag_display}",
                "inline": True
            })
            
        embeds.append({
            "title": "📋 精選數據看板",
            "color": 3447003,
            "fields": fields,
            "footer": {"text": f"統計時間: {now.strftime('%Y-%m-%d %H:%M')}"}
        })

    # 6. 發送
    send_discord_webhook(embeds)

if __name__ == "__main__":
    main()