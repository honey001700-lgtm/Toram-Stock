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
# 🧠 AI 模型挑選與執行 (修正時間 + 強制粗體格式)
# ==========================================
def generate_ai_script(market_stats, highlights):
    
    # 1. 設定時間 (強制使用台灣時間 UTC+8)
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    date_str = tw_now.strftime("%Y-%m-%d %A") # 例如: 2025-12-07 Sunday

    # --- 備用文案 (Plan B) ---
    def get_backup_script():
        print("🛡️ 啟用備用文案模式...")
        mood = "📈 市場熱度上升中！" if market_stats['up'] > market_stats['down'] else "📉 市場稍顯冷清..."
        top_item = highlights[0] if highlights else None
        highlight_text = ""
        if top_item:
            # 備用文案也要符合你的格式要求
            highlight_text = f"今日焦點是 {top_item['item']}，幅度達 {top_item['change_pct']:.1f}%，現價 **${top_item['price']:,.0f}** ！"
        return f"""(系統自動生成) 各位冒險者好！🤖\n{mood}\n本日上漲 {market_stats['up']} 家，下跌 {market_stats['down']} 家。\n{highlight_text}\n(AI 分析師連線休息中，以上為自動播報)\n祝大家打寶順利！""", 0

    if not GEMINI_API_KEY:
        print("⚠️ 未設定 API Key")
        return get_backup_script()

    # --- 2. 篩選出所有「Flash」模型 ---
    target_models = []
    try:
        print("🔍 正在查詢 Google 可用模型清單...")
        genai.configure(api_key=GEMINI_API_KEY)
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        priority_list = ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-flash-002", "gemini-1.5-flash-001", "flash"]
        seen = set()
        for p in priority_list:
            for m in all_models:
                if p in m and m not in seen:
                    target_models.append(m)
                    seen.add(m)
        
        if not target_models: target_models = all_models
    except:
        target_models = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-001"]

    # --- 3. 準備提示詞 (加入強制格式指令) ---
    top_movers_str = ""
    for h in highlights[:3]: 
        tags_str = ", ".join(h['tags']) if h['tags'] else "無"
        top_movers_str += f"- {h['item']}: 漲跌 {h['change_pct']:+.1f}%, 價格 {h['price']:,.0f}, 特徵: [{tags_str}]\n"

    prompt = f"""
    【角色設定】
    你是一位名叫「托蘭分析師」的托蘭市場走向分析師。
    語氣：活潑、熱情、專業，就像台灣的財經 YouTuber。
    
    【市場數據】
    - 日期：{date_str} (請以此日期為準，不要說錯)
    - 市場氣氛：上漲 {market_stats['up']} 家 / 下跌 {market_stats['down']} 家
    - 重點關注物品：\n{top_movers_str}

    【寫作要求】
    1. 結構：開場問候 -> 整體盤勢 -> 重點物品點評(漲則興奮恭喜, 跌則謹慎提醒) -> 結尾祝福。
    2. ⚠️ **強制格式要求** (非常重要)：
       - **價格**：必須寫成 **$10,000,000** (粗體 + 錢字號 + 千分位)，前後留空白。
       - **漲跌幅**：必須寫成 **+200.5%** (粗體 + 正負號 + 百分比)，前後留空白。
    3. 如果物品有「頭肩頂」或「創歷史新高」等特徵，請務必在點評時提到並解讀其意義。
    4. ⚠️ **結尾強制指令**：
       - 這是「日報」，結尾請說「明天見」。
    5. 字數約 250 字，多用 Emoji 讓版面生動。
    """

    # --- 4. 輪詢呼叫 ---
    for model_name in target_models:
        try:
            print(f"🧠 嘗試呼叫: {model_name} ...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.7))
            
            if response.text:
                print("✅ AI 寫作成功！")
                color = 5763719 if market_stats['up'] >= market_stats['down'] else 15548997
                return response.text, color
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                print(f"⏳ {model_name} 配額不足...")
            else:
                print(f"❌ {model_name} 錯誤: {e}")
            time.sleep(1)

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
# 🧠 AI 模型 (6人版 - 自然聊天風格)
# ==========================================
def generate_ai_script(market_stats, ai_focus_items):
    
    # 1. 時間設定 (台灣時間)
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    date_str = tw_now.strftime("%Y-%m-%d %A")

    # 備用文案
    def get_backup_script():
        return "(AI 分析師連線忙碌中，請直接查看下方數據看板)", 0
    
    if not GEMINI_API_KEY: return get_backup_script()

    # --- 準備提示詞 ---
    
    # 簡單的物品清單字串
    items_str = ""
    for h in ai_focus_items:
        role = h.get('role', '重點關注') # 例如：漲幅冠軍、跌幅最重
        tags_str = ", ".join(h['tags']) if h['tags'] else "無"
        items_str += f"- {h['item']} ({role}): 漲跌 {h['change_pct']:+.1f}%, 價格 {h['price']:,.0f}, 特徵: {tags_str}\n"

    prompt = f"""
    【角色設定】
    你是一位名叫「托蘭小姊姊」的虛擬寶物市場分析師。
    語氣：活潑、熱情、專業，就像台灣的財經 YouTuber 在跟觀眾直播聊天。
    
    【市場數據】
    - 日期：{date_str} (請以此日期為準)
    - 上漲 {market_stats['up']} 家 / 下跌 {market_stats['down']} 家
    - 平均漲跌幅：{market_stats['avg_change']:+.1f}%

    【今日 6 大焦點物品】
    {items_str}

    【寫作要求】
    1. **自然流暢**：請像原本那樣，順暢地介紹這 6 個物品，**不要**使用「紅榜區」、「警示區」這種生硬的分類標題。就像你在跟朋友講今天發生了什麼大新聞一樣。
    2. **情緒起伏**：
       - 講到大漲、創新高的物品時要興奮、恭喜玩家。
       - 講到大跌、或有「頭肩頂」的物品時，語氣轉為關心、提醒風險。
    3. **強制格式 (非常重要)**：
       - 價格： **$10,000,000** (粗體+錢號+千分位)。
       - 漲跌： **+237.2%** (粗體+正負號+百分比)。
    4. **特徵解讀**：如果物品有「頭肩頂」或「三角收斂」，請順口提到這代表什麼（例如：要注意回檔喔）。
    5. **結尾**：強制說「我們明天見」。
    6. 字數約 350 字，多用 Emoji。
    """

    # --- 呼叫模型 ---
    target_models = []
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_list = ["gemini-2.0-flash-exp", "gemini-1.5-flash", "gemini-1.5-flash-001", "flash"]
        seen = set()
        for p in priority_list:
            for m in all_models:
                if p in m and m not in seen:
                    target_models.append(m)
                    seen.add(m)
        if not target_models: target_models = all_models
    except:
        target_models = ["models/gemini-1.5-flash"]

    for model_name in target_models:
        try:
            print(f"🧠 嘗試呼叫: {model_name} ...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.7))
            if response.text:
                color = 5763719 if market_stats['up'] >= market_stats['down'] else 15548997
                return response.text, color
        except Exception as e:
            if "429" not in str(e): print(f"❌ {model_name} error: {e}")
            time.sleep(1)

    return get_backup_script()

# ==========================================
# 🚀 主程式 (選出 6 強 + 傳給 AI)
# ==========================================
def main():
    print("🚀 SYSTEM CHECK: 腳本開始執行...")
    
    # 1. 讀取數據
    df, err = load_data(SHEET_URL)
    if df.empty: return

    # 強制台灣時間 UTC+8
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    yesterday = tw_now - pd.Timedelta(hours=24)
    
    if not pd.api.types.is_datetime64_any_dtype(df['時間']):
        df['時間'] = pd.to_datetime(df['時間'])

    recent_df = df[df['時間'] >= yesterday]
    active_items = recent_df['物品'].unique().tolist()
    
    # --- 數據收集 ---
    all_changes = [] 
    highlights = []
    
    for item in active_items:
        item_df = filter_and_prepare_data(df, item)
        if len(item_df) < 5: continue 

        latest = item_df.iloc[-1]['單價']
        try:
            prev = item_df[item_df['時間'] <= yesterday].iloc[-1]['單價']
        except:
            prev = item_df.iloc[0]['單價']
            
        change = ((latest - prev) / prev) * 100 if prev else 0
        all_changes.append(change)

        patterns = detect_patterns(item_df)
        events = detect_events(item_df)
        tags = [p['type'] for p in patterns if any(k in p['type'] for k in ["頭肩", "雙重", "三角"])]
        tags += [e['type'] for e in events if "新高" in e['type'] or "新低" in e['type']]

        if abs(change) >= 10 or tags:
            highlights.append({
                "item": item,
                "price": latest,
                "change_pct": change,
                "tags": tags
            })

    market_stats = {
        'up': sum(1 for x in all_changes if x > 0),
        'down': sum(1 for x in all_changes if x < 0),
        'avg_change': sum(all_changes) / len(all_changes) if all_changes else 0
    }

    # --- 🌟 挑選 6 位主角 (AI Focus) ---
    ai_focus_items = []
    selected_names = set()

    def add_item(item_obj, role_name):
        if item_obj['item'] not in selected_names:
            item_obj['role'] = role_name
            ai_focus_items.append(item_obj)
            selected_names.add(item_obj['item'])

    # 1. 👑 漲幅冠軍
    highlights.sort(key=lambda x: x['change_pct'], reverse=True)
    if highlights and highlights[0]['change_pct'] > 0:
        add_item(highlights[0], "漲幅冠軍")

    # 2. 🥈 漲幅亞軍
    if len(highlights) > 1 and highlights[1]['change_pct'] > 0:
        add_item(highlights[1], "強勢副手")

    # 3. 🩸 跌幅最重
    highlights.sort(key=lambda x: x['change_pct']) # 由小到大
    if highlights and highlights[0]['change_pct'] < 0:
        add_item(highlights[0], "跌幅最重")

    # 4. 🔥 創新高代表
    high_breakers = [h for h in highlights if any("新高" in t for t in h['tags'])]
    if high_breakers:
        high_breakers.sort(key=lambda x: x['change_pct'], reverse=True)
        add_item(high_breakers[0], "創歷史新高")

    # 5. 🔭 技術型態
    pattern_items = [h for h in highlights if any(k in "".join(h['tags']) for k in ["頭肩", "雙重", "三角"])]
    if pattern_items:
        pattern_items.sort(key=lambda x: len(x['tags']), reverse=True)
        add_item(pattern_items[0], "技術型態")

    # 6. 👀 熱門補位 (補滿 6 個)
    highlights.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    for h in highlights:
        if len(ai_focus_items) >= 6: break
        add_item(h, "重點關注")

    # 生成 AI 報告
    ai_script, color = generate_ai_script(market_stats, ai_focus_items)

    # --- 製作 Embeds ---
    embeds = []
    embeds.append({
        "title": f"🎙️ 托蘭市場日報 ({tw_now.strftime('%m/%d')})",
        "description": ai_script,
        "color": color,
        "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png"}
    })

    if highlights:
        # 看板部分：列出前 15 名
        highlights.sort(key=lambda x: abs(x['change_pct']), reverse=True)
        fields = []
        for h in highlights[:15]: 
            emoji = "🚀" if h['change_pct'] > 0 else ("🩸" if h['change_pct'] < 0 else "➖")
            
            pretty_tags = []
            for tag in h.get('tags', []):
                if "新高" in tag: pretty_tags.append("🔥 創歷史新高")
                elif "新低" in tag: pretty_tags.append("🧊 創歷史新低")
                elif "頭肩頂" in tag: pretty_tags.append("👤 頭肩頂(看跌)")
                elif "頭肩底" in tag: pretty_tags.append("🧘 頭肩底(看漲)")
                elif "雙重頂" in tag: pretty_tags.append("⛰️ M頭(看跌)")
                elif "雙重底" in tag: pretty_tags.append("🇼 W底(看漲)")
                elif "三角" in tag: pretty_tags.append("📐 三角收斂")
                else: pretty_tags.append(tag) 

            tag_display = f"\n" + "\n".join([f"└ {t}" for t in pretty_tags]) if pretty_tags else ""
            
            fields.append({
                "name": f"{h['item']}", 
                "value": f"{emoji} `{h['change_pct']:+.1f}%` | ${h['price']:,.0f}{tag_display}",
                "inline": True
            })
            
        embeds.append({
            "title": "📋 精選數據看板",
            "color": 3447003,
            "fields": fields,
            "footer": {"text": f"統計時間: {tw_now.strftime('%Y-%m-%d %H:%M')} (GMT+8)"}
        })

    send_discord_webhook(embeds)
    
if __name__ == "__main__":
    main()