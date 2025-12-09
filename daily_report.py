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
# 🧠 AI 模型 (早晚報智能切換版)
# ==========================================
def generate_ai_script(market_stats, ai_focus_items, report_type):
    
    # 1. 時間設定
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    date_str = tw_now.strftime("%Y-%m-%d %A")

    # --- 設定早晚報的情境與結尾 ---
    if report_type == "早報":
        # 早報情境
        greeting = "早安"
        time_context = "昨晚到今早"
        # 結尾：鼓勵一天開始 + 預告晚上見
        ending_instruction = "結尾請維持熱情專業，鼓勵玩家把握今天的好時機，最後強制要說『我們今晚見！』"
    else:
        # 晚報情境
        greeting = "晚安"
        time_context = "今天白天"
        # 結尾：總結一天 + 提醒休息/掛機 + 預告明早見
        ending_instruction = "結尾請維持溫馨提醒（如風險管理或早點休息），最後強制要說『我們明早見！』"

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
    風格：喜歡在結尾說一些金句（例如：機會總是在變化中產生、風險管理永遠是第一要務）。
    
    【時間情境】
    - 日期：{date_str}
    - 時段：**{report_type}**
    - 開場問候：請說「{greeting}」，並說明這是「{time_context}」的市場變化。
    
    【市場數據】
    - 上漲 {market_stats['up']} 家 / 下跌 {market_stats['down']} 家
    - 平均漲跌幅：{market_stats['avg_change']:+.1f}%

    【本時段 6 大焦點物品】
    {items_str}

    【寫作要求】

    1. **自然流暢**：順暢介紹這 6 個物品，不要用生硬的標題。
    2. **情緒起伏**：
       - 大漲/新高：開心、恭喜玩家。
       - 大跌/頭肩頂：關心、提醒風險。
    3. **強制格式**：
       - 價格：**$10,000,000** (粗體+錢字號+千分位)，前後留空白。。
       - 漲跌：**+237.2%** (粗體+正負號+百分比)，前後留空白。。
    4. **特徵解讀**：如果物品有「頭肩頂」或「三角收斂」，請順口提到這代表什麼（例如：要注意回檔喔）。
    5. **結尾設定 (重要)**：
       - 請保留原本的風格（有漲有跌、投資需謹慎、賺得盆滿缽滿之類的專業結尾）。
       - {ending_instruction}
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
# 🎵 使用 Edge-TTS 生成加速語音
# ==========================================

def num_to_chinese(num_str):
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

async def generate_voice_async(text, output_file):
    communicate = edge_tts.Communicate(text, "zh-TW-HsiaoChenNeural", rate="+30%")
    await communicate.save(output_file)

def create_audio_file(text, report_type):
    print("🎙️ 正在生成語音報導 (Edge-TTS 加速版)...")
    try:
        # (1) 產生動態檔名
        utc_now = datetime.datetime.utcnow()
        tw_now = utc_now + datetime.timedelta(hours=8)
        month_day = tw_now.strftime('%m-%d')
        # 檔名加入早晚報標識
        filename = f"托蘭市場{report_type} ({month_day}).mp3"

        # (2) 清理文字
        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
        clean_text = clean_text.replace("###", "").replace("##", "")
        clean_text = re.sub(
            r'\$([0-9,]+)', 
            lambda m: f"{num_to_chinese(m.group(1))}眾神幣", 
            clean_text
        )
        clean_text = clean_text.replace(",", "")
        clean_text = re.sub(r'[\U00010000-\U0010ffff]', '', clean_text) 
        clean_text = re.sub(r'[\u2600-\u27bf]', '', clean_text)
        
        # (3) 執行非同步生成
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

    # 2. 時間與時段