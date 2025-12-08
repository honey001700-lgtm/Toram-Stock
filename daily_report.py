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
# 🎵 使用 Edge-TTS 生成 (系統命令強制執行版)
# ==========================================
import subprocess
import sys

def create_audio_file(text):
    print("🎙️ 啟動語音生成 (System CLI Mode)...")
    
    # 1. 檢查文字
    if not text or not text.strip():
        print("❌ 錯誤：文字為空")
        return None

    # 2. 清理文字 (極簡化，只移除會導致命令列崩潰的符號)
    clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', text) 
    clean_text = clean_text.replace("###", "").replace("##", "").replace("`", "")
    clean_text = re.sub(r'\$([0-9,]+)', lambda m: f"{num_to_chinese(m.group(1))}眾神幣", clean_text)
    clean_text = clean_text.replace(",", "")
    # 移除 Emoji (這很重要，Emoji 會導致命令列編碼錯誤)
    clean_text = re.sub(r'[^\w\s\u4e00-\u9fa5,.:;!?，。：；！？\(\)（）]', '', clean_text)
    
    if not clean_text.strip(): return None

    # 3. 準備檔案路徑
    utc_now = datetime.datetime.utcnow()
    tw_now = utc_now + datetime.timedelta(hours=8)
    filename = f"托蘭市場日報 ({tw_now.strftime('%m-%d %H')}).mp3"
    
    # 為了避免命令列長度限制，我們先將文字寫入暫存檔
    temp_txt_path = "temp_tts_input.txt"
    with open(temp_txt_path, "w", encoding="utf-8") as f:
        f.write(clean_text)

    # 4. 執行命令列 (使用 sys.executable 確保用的是同一個 Python 環境)
    # 指令等同於: edge-tts --voice zh-TW-HsiaoYuNeural --file temp_tts_input.txt --write-media output.mp3
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--voice", "zh-TW-HsiaoYuNeural",
        "--file", temp_txt_path,
        "--write-media", filename
    ]

    print(f"🔥 [強制模式] 執行系統命令，鎖定曉雨...")
    
    try:
        # 執行外部命令，並捕獲輸出
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            check=True, # 如果失敗會噴出 CalledProcessError
            timeout=60  # 設定 60 秒超時
        )
        
        # 檢查檔案是否生成
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            print(f"✅ 系統命令執行成功！音檔已生成。")
            # 清理暫存文字檔
            if os.path.exists(temp_txt_path): os.remove(temp_txt_path)
            return filename
        else:
            print("❌ 命令執行完成但沒有產生檔案。")
            return None

    except subprocess.CalledProcessError as e:
        print("\n" + "="*40)
        print("🛑 系統命令被「卡」住了！回傳錯誤如下：")
        print(f"錯誤代碼 (Return Code): {e.returncode}")
        print(f"標準錯誤 (Stderr): {e.stderr}")
        print("="*40)
        
        if "401" in e.stderr:
            print("👉 還是 401？請確認 requirements.txt 有用 git 安裝最新版 edge-tts。")
        elif "No audio" in e.stderr:
            print("💀 絕望結論：微軟已將 GitHub Actions 的 IP 完全封鎖，無法使用曉雨。")
        
        return None
        
    except Exception as e:
        print(f"❌ 發生未預期的系統錯誤: {e}")
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