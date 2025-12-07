# daily_report.py
import os
import requests
import pandas as pd
import datetime
import time
import json
import re
import asyncio 
import edge_tts 
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
# 🧠 AI 模型 (6人焦點版 - 自然聊天風格)
# ==========================================
def generate_ai_script(market_stats, ai_focus_items):
    
    # 1. 時間設定 (強制使用台灣時間 UTC+8)
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    date_str = tw_now.strftime("%Y-%m-%d %A")

    # 備用文案
    def get_backup_script():
        return "(AI 分析師連線忙碌中，請直接查看下方數據看板)", 0
    
    if not GEMINI_API_KEY: return get_backup_script()

    # --- 準備 Prompt ---
    items_str = ""
    for h in ai_focus_items:
        role = h.get('role', '重點關注')
        tags_str = ", ".join(h['tags']) if h['tags'] else "無"
        items_str += f"- {h['item']} ({role}): 漲跌 {h['change_pct']:+.1f}%, 價格 {h['price']:,.0f}, 特徵: {tags_str}\n"

    prompt = f"""
    【角色設定】
    你是一位名叫「托蘭分析師」的托蘭市場分析師。
    語氣：冷靜、熱情、專業，就像台灣的財經達人 YouTuber。
    
    【市場數據】
    - 日期：{date_str}
    - 上漲 {market_stats['up']} 家 / 下跌 {market_stats['down']} 家
    - 平均漲跌幅：{market_stats['avg_change']:+.1f}%

    【今日 6 大焦點物品】
    {items_str}

    【寫作要求】
    1. **自然流暢**：順暢介紹這 6 個物品，不要用生硬標題。
    2. **情緒起伏**：大漲要開心恭喜，大跌或頭肩頂要語氣轉為關心提醒。
    3. **強制格式**：
       - 價格：**$10,000,000** (粗體+錢字號+千分位)。
       - 漲跌：**+237.2%** (粗體+正負號+百分比)。
    4. **特徵解讀**：順口提到技術型態代表的意義。
    5. **結尾**：請說「我們明天見」。
    6. 字數約 350 字，多用Emoji。
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
# 🎵 NEW: 使用 Edge-TTS 生成加速語音
# ==========================================
async def generate_voice_async(text, output_file):
    # rate='+30%' 代表加速 30%
    communicate = edge_tts.Communicate(text, "zh-TW-HsiaoChenNeural", rate="+30%")
    await communicate.save(output_file)

def create_audio_file(text):
    print("🎙️ 正在生成語音報導 (Edge-TTS 加速版)...")
    try:
        # 1. 產生動態檔名
        utc_now = datetime.datetime.utcnow()
        tw_now = utc_now + datetime.timedelta(hours=8)
        
        # 格式: [ 托蘭市場日報 (12-08 14點) ].mp3
        # 注意：使用 - 分隔日期，避免路徑錯誤
        month_day = tw_now.strftime('%m-%d')
        hour = tw_now.strftime('%H')
        filename = f"托蘭市場日報 ({month_day} {hour}點).mp3"

        # 2. 清理文字 (移除 Emoji 與特殊符號)
        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
        clean_text = clean_text.replace("###", "").replace("##", "")
        # 移除 Emoji
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text) 
        clean_text = re.sub(r'[\u2600-\u27bf]', '', clean_text)
        
        # 3. 執行非同步生成
        asyncio.run(generate_voice_async(clean_text, filename))
        return filename
    except Exception as e:
        print(f"❌ 語音生成失敗: {e}")
        return None

# ==========================================
# 🛠️ Discord 發送功能
# ==========================================
def send_discord_webhook(embeds, file_path=None):
    if not DISCORD_WEBHOOK_URL:
        print("❌ 未設定 DISCORD_WEBHOOK_URL")
        return

    payload = {
        "username": "托蘭 AI 分析師",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png",
        "embeds": embeds
    }

    try:
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                # 使用 multipart/form-data，Discord 會自動處理顯示位置
                files = {'file': (file_path, f, 'audio/mpeg')}
                response = requests.post(
                    DISCORD_WEBHOOK_URL, 
                    data={'payload_json': json.dumps(payload)}, 
                    files=files
                )
        else:
            response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
            
        if response.status_code in [200, 204]:
            print("✅ Discord 通知發送成功！")
        else:
            print(f"❌ Discord 回傳錯誤: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"❌ 發送失敗: {e}")

# ==========================================
# 🚀 主程式
# ==========================================
def main():
    print("🚀 SYSTEM CHECK: 腳本開始執行...")
    
    # 1. 讀取數據
    df, err = load_data(SHEET_URL)
    if df.empty: return

    # 2. 時間設定
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    yesterday = tw_now - pd.Timedelta(hours=25)
    
    if not pd.api.types.is_datetime64_any_dtype(df['時間']):
        df['時間'] = pd.to_datetime(df['時間'])

    recent_df = df[df['時間'] >= yesterday]
    active_items = recent_df['物品'].unique().tolist()
    
    # --- 3. 數據收集與分析 ---
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

    # --- 4. 挑選焦點物品 ---
    ai_focus_items = []
    selected_names = set()
    def add_item(item_obj, role_name):
        if item_obj['item'] not in selected_names:
            item_obj['role'] = role_name
            ai_focus_items.append(item_obj)
            selected_names.add(item_obj['item'])

    highlights.sort(key=lambda x: x['change_pct'], reverse=True)
    if highlights and highlights[0]['change_pct'] > 0: add_item(highlights[0], "漲幅冠軍")
    if len(highlights) > 1 and highlights[1]['change_pct'] > 0: add_item(highlights[1], "強勢副手")
    highlights.sort(key=lambda x: x['change_pct']) 
    if highlights and highlights[0]['change_pct'] < 0: add_item(highlights[0], "跌幅最重")
    high_breakers = [h for h in highlights if any("新高" in t for t in h['tags'])]
    if high_breakers:
        high_breakers.sort(key=lambda x: x['change_pct'], reverse=True)
        add_item(high_breakers[0], "創歷史新高")
    pattern_items = [h for h in highlights if any(k in "".join(h['tags']) for k in ["頭肩", "雙重", "三角"])]
    if pattern_items:
        pattern_items.sort(key=lambda x: len(x['tags']), reverse=True)
        add_item(pattern_items[0], "技術型態")
    highlights.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    for h in highlights:
        if len(ai_focus_items) >= 6: break
        add_item(h, "重點關注")

    # 5. 生成 AI 報告
    ai_script, color = generate_ai_script(market_stats, ai_focus_items)

    # 6. 生成音檔 (只針對 AI 腳本)
    audio_file_path = None
    if ai_script and "AI 分析師連線忙碌中" not in ai_script:
        audio_file_path = create_audio_file(ai_script)

    # --- 7. 製作 Embeds ---
    embeds = []
    
    # [Embed 1] AI 日報
    embeds.append({
        "title": f"🎙️ 托蘭市場日報 ({tw_now.strftime('%m/%d')})",
        "description": ai_script,
        "color": color,
        "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png"}
    })

    # [Embed 2] 數據看板
    if highlights:
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
                elif "雙重頂" in tag: pretty_tags.append("Ⓜ️ M頭(看跌)")
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
            "description": "*(此區域數據不包含在語音播報中)*",
            "color": 3447003,
            "fields": fields,
            "footer": {"text": f"統計時間: {tw_now.strftime('%Y-%m-%d %H:%M')} (GMT+8)"}
        })

    # 8. 發送 (Discord 處理順序)
    send_discord_webhook(embeds, file_path=audio_file_path)

    # 9. 清理暫存
    if audio_file_path and os.path.exists(audio_file_path):
        os.remove(audio_file_path)
        print("🧹 暫存音檔已清理")

if __name__ == "__main__":
    main()