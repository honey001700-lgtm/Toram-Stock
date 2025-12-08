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
    - 日期：{date_str} (請以此日期為準)
    - 上漲 {market_stats['up']} 家 / 下跌 {market_stats['down']} 家
    - 平均漲跌幅：{market_stats['avg_change']:+.1f}%

    【今日 6 大焦點物品】
    {items_str}

    【寫作要求】
    1. **自然流暢**：請順暢地介紹這 6 個物品，**不要**使用「紅榜區」、「警示區」這種生硬的分類標題。
    2. **情緒起伏**：
       - 講到大漲、創新高的物品時要開心、恭喜玩家。
       - 講到大跌、或有「頭肩頂」的物品時，語氣轉為關心、提醒風險。
    3. **強制格式 (非常重要)**：
       - 價格：必須寫成 **$10,000,000** (粗體 + 錢字號 + 千分位)，前後留空白。
       - 漲跌：必須寫成 **+237.2%** (粗體 + 正負號 + 百分比)，前後留空白。
    4. **特徵解讀**：如果物品有「頭肩頂」或「三角收斂」，請順口提到這代表什麼（例如：要注意回檔喔）。
    5. **結尾強制指令**：
       - 即使今天是週日，因為這是「日報」，結尾請說「我們明天見」，**絕對不要說**「下週見」。
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
# 🎵 使用 Edge-TTS 生成加速語音 (完整修正版)
# ==========================================

# 1. 數字轉中文輔助函式 (解決 TTS 亂念數字問題)
def num_to_chinese(num_str):
    """
    將 "25,555,555" 這樣的字串轉換為 "二千五百五十五萬五千五百五十五"
    """
    try:
        n = int(num_str.replace(",", ""))
    except:
        return num_str
        
    if n == 0: return "零"

    units = ['', '萬', '億']
    nums = '零一二三四五六七八九'
    
    def _block_to_chinese(num):
        s = ""
        if num >= 1000:
            s += nums[num // 1000] + "千"
            num %= 1000
            if num < 100: s += "零"
        if num >= 100:
            s += nums[num // 100] + "百"
            num %= 100
            if num < 10 and num > 0: s += "零"
        if num >= 10:
            s += nums[num // 10] + "十"
            num %= 10
        if num > 0:
            s += nums[num]
        return s.strip("零")

    result = ""
    unit_idx = 0
    while n > 0:
        block = n % 10000
        if block > 0:
            block_str = _block_to_chinese(block)
            result = block_str + units[unit_idx] + result
        n //= 10000
        unit_idx += 1
    
    if result.startswith("一十"):
        result = result[1:]
        
    return result

# 2. 非同步語音生成函式 (這是您報錯說缺少的部分)
# ==========================================
# 🎵 使用 Edge-TTS 生成 (單一人聲 + 深度診斷版)
# ==========================================

async def generate_voice_diagnostic(text, output_file):
    # 【設定】只使用這一個聲音，絕不切換
    TARGET_VOICE = "zh-TW-HsiaoYuNeural" 
    
    print(f"🔍 [診斷模式] 準備使用語音: {TARGET_VOICE}")
    print(f"📊 [診斷模式] 文字長度: {len(text)} 字")

    try:
        # 建立連線物件
        communicate = edge_tts.Communicate(text, TARGET_VOICE, rate="+30%")
        
        # 嘗試生成
        await communicate.save(output_file)
        
        # 檢查結果
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"✅ 語音生成成功！檔案大小: {os.path.getsize(output_file)} bytes")
            return True
        else:
            print("❌ 生成失敗：檔案雖然沒有報錯，但產出的檔案是空的 (0 bytes)。")
            print("👉 可能原因：傳入的文字含有微軟無法處理的字元，或被伺服器靜默拒絕。")
            return False

    except Exception as e:
        error_msg = str(e)
        print("\n" + "="*40)
        print("🛑 語音生成被「卡住」了！詳細原因分析：")
        print("="*40)
        
        # --- 針對不同錯誤代碼進行分析 ---
        
        if "401" in error_msg or "Unauthorized" in error_msg:
            print("💀 錯誤類型：【401 驗證失敗 (Unauthorized)】")
            print("👉 原因：您的 edge-tts 套件版本過舊，微軟的金鑰已更換。")
            print("🔧 解法：必須在 requirements 或 actions 裡使用 'git+https://github.com/rany2/edge-tts.git@master'")
            
        elif "No audio was received" in error_msg:
            print("🔇 錯誤類型：【無音訊回傳 (No Audio Received)】")
            print("👉 原因：")
            print("   1. 微軟伺服器主動切斷連線 (可能是 IP 頻率過高)。")
            print("   2. 該語音模型暫時維修中。")
            print("   3. 文字格式有問題 (例如全都是符號)。")
            
        elif "400" in error_msg or "BadRequest" in error_msg:
            print("⚠️ 錯誤類型：【400 請求錯誤 (Bad Request)】")
            print("👉 原因：傳送的文字格式錯誤，SSML 標籤不對，或者含有非法字元。")
            
        elif "Connection" in error_msg or "socket" in error_msg:
            print("🔌 錯誤類型：【連線失敗 (Connection Error)】")
            print("👉 原因：網路不穩，無法連上微軟 Edge 伺服器 (wss://speech.platform.bing.com)。")
            
        else:
            print(f"❓ 未知錯誤類型：{error_msg}")
            
        print("="*40 + "\n")
        return False

def create_audio_file(text):
    print("🎙️ 正在生成語音報導 (嚴格模式)...")
    
    # 1. 檢查文字內容
    if not text or not text.strip():
        print("❌ 卡住原因：輸入的文字是空的 (Empty String)。")
        return None

    # 2. 清理文字
    # 這裡只做最基本的清理，保留大部分內容以便測試
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    clean_text = clean_text.replace("###", "").replace("##", "").replace("`", "")
    clean_text = re.sub(r'\$([0-9,]+)', lambda m: f"{num_to_chinese(m.group(1))}眾神幣", clean_text)
    clean_text = clean_text.replace(",", "")
    # 移除 Emoji (這通常是卡住的主因之一)
    clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text) 
    clean_text = re.sub(r'[\u2600-\u27bf]', '', clean_text)

    if not clean_text.strip():
        print("❌ 卡住原因：文字清理後變成了空白 (可能是原文全都是 Emoji 或特殊符號)。")
        return None

    # 3. 執行生成 (包含詳細診斷)
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    filename = f"托蘭市場日報 ({tw_now.strftime('%m-%d %H')}).mp3"

    success = asyncio.run(generate_voice_diagnostic(clean_text, filename))
    
    if success:
        return filename
    else:
        # 失敗時直接回傳 None，不使用任何備用方案
        print("❌ 因語音生成失敗，本次日報將不包含音檔。")
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
                # 使用 multipart/form-data
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