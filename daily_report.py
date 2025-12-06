# daily_report.py
import os
import requests
import pandas as pd
import datetime
import google.generativeai as genai

# 引用模組 (確保你的專案結構中有這些檔案)
from utils.preprocess import load_data, filter_and_prepare_data
from utils.regression import calculate_r_squared
from analysis.trend import analyze_trend
from analysis.patterns import detect_patterns, detect_events

# ==========================================
# 🔑 設定區 (讀取環境變數)
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtSvfsvYpDjQutAO9L4AV1Rq8XzZAQEAZcLZxl9JsSvxCo7X2JsaFTVdTAQwGNQRC2ySe5OPJaTzp9/pub?gid=915078159&single=true&output=csv"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# ==========================================
# 🤖 AI 寫手核心 (Gemini)
# ==========================================
def generate_ai_script(market_stats, highlights):
    """
    將市場數據打包傳給 Gemini，讓它生成真人分析文案
    """
    # 1. 檢查 API Key
    if not GEMINI_API_KEY:
        print("⚠️ 警告：未設定 GEMINI_API_KEY，將跳過 AI 分析。")
        return "⚠️ (系統訊息) 管理員尚未設定 AI 金鑰，無法生成分析報告，請參閱下方數據表格。", 0

    try:
        # 2. 設定 AI 模型
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')

        # 3. 準備數據摘要
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d %A") # 例如: 2025-12-07 Sunday
        
        # 整理前 3 名重點個股給 AI 看 (避免資訊過載)
        top_movers_str = ""
        for h in highlights[:3]: 
            # 處理標籤文字
            tags_str = ", ".join(h['tags']) if h['tags'] else "無特殊型態"
            top_movers_str += f"- {h['item']}: 漲跌 {h['change_pct']:.1f}%, 現價 ${h['price']:,.0f}, 特徵: {tags_str}\n"
            
        if not top_movers_str:
            top_movers_str = "今日無顯著波動物品。"

        # 4. 撰寫 Prompt (提示詞 - 這是 AI 的靈魂)
        prompt = f"""
        【角色設定】
        你是一位名叫「托蘭小姊姊」的虛擬寶物市場交易分析師。
        你的個性：溫暖、專業、像一位鄰家大姊姊，說話帶有台灣財經 YouTuber 的口語風格（例如：各位朋友、這點我們要留意、不要自己嚇自己）。
        你會適時加入一點「心靈雞湯」或「交易心理學」的建議。

        【今日任務】
        請根據以下市場數據，寫一篇約 200-300 字的 Discord 日報。

        【市場數據】
        - 日期：{date_str}
        - 上漲家數：{market_stats['up']}
        - 下跌家數：{market_stats['down']}
        - 總觀測數：{market_stats['total']}
        - 重點關注物品 (Top Movers)：
        {top_movers_str}

        【寫作結構要求】
        1. **開場**：根據今天是星期幾，給予不同的溫暖問候（例如週五就說週末愉快，週一就說加油收心）。
        2. **盤勢解讀**：根據漲跌家數判斷今天氣氛（多頭/空頭/盤整），並給予操作建議（順勢/觀望/保守）。
        3. **焦點分析**：挑選 1-2 個重點物品進行點評。若是大漲請用興奮語氣；若是大跌請溫柔提醒風險。
        4. **結尾**：一句簡短的祝福或交易心法。
        5. **格式**：請使用 Markdown 語法，適量使用 Emoji 🚀📉，段落分明，適合手機閱讀。不要列點式報告，要像寫文章一樣流暢。
        """

        # 5. 呼叫 Gemini 生成
        response = model.generate_content(prompt)
        text = response.text

        # 簡單根據漲跌判斷顏色 (綠色代表多頭，紅色代表空頭)
        color = 5763719 if market_stats['up'] >= market_stats['down'] else 15548997
        
        return text, color

    except Exception as e:
        print(f"❌ Gemini 生成失敗: {e}")
        return "🤖 機器人腦袋打結了，暫時無法生成分析報告... (請檢查 API Quota 或網路狀態)", 0

# ==========================================
# 🛠️ Discord 發送功能
# ==========================================
def send_discord_webhook(embeds):
    if not DISCORD_WEBHOOK_URL:
        print("❌ 未設定 DISCORD_WEBHOOK_URL，跳過發送。")
        return

    payload = {
        "username": "托蘭 AI 分析師",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png", # 女性分析師頭像
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
        print(f"❌ 數據為空或讀取失敗: {err}")
        return

    # 2. 設定時間範圍 (過去 24 小時)
    now = datetime.datetime.now()
    yesterday = now - pd.Timedelta(hours=24)
    
    # 篩選活躍物品
    recent_df = df[df['時間'] >= yesterday]
    active_items = recent_df['物品'].unique().tolist()
    
    print(f"🔍 過去 24 小時共有 {len(active_items)} 個活躍物品。")
    
    highlights = []
    # 統計數據 (給 AI 判斷多空用)
    market_stats = {'up': 0, 'down': 0, 'total': 0}

    # 3. 逐一分析物品
    for item in active_items:
        # 取得該物品的完整歷史數據
        item_df = filter_and_prepare_data(df, item)
        if len(item_df) < 5: continue 

        # 計算漲跌幅
        latest_price = item_df.iloc[-1]['單價']
        try:
            # 嘗試找 24 小時前的價格
            prev_price_row = item_df[item_df['時間'] <= yesterday].iloc[-1]
            prev_price = prev_price_row['單價']
        except IndexError:
            # 如果找不到，就用最早的一筆
            prev_price = item_df.iloc[0]['單價']
            
        change_pct = ((latest_price - prev_price) / prev_price) * 100 if prev_price else 0
        
        # 更新統計數據
        market_stats['total'] += 1
        if change_pct > 0: market_stats['up'] += 1
        elif change_pct < 0: market_stats['down'] += 1

        # 執行技術分析
        trend = analyze_trend(item_df)
        patterns = detect_patterns(item_df)
        events = detect_events(item_df)
        
        # --- 篩選亮點 (Highlights) ---
        tags = []
        is_high_volatility = False
        
        # 條件 A: 波動過大 (>10%)
        if abs(change_pct) >= 10: 
            is_high_volatility = True
        
        # 條件 B: 偵測到特殊型態
        target_keywords = ["頭肩", "雙重", "三角", "通道"]
        for p in patterns:
            for kw in target_keywords:
                if kw in p['type']:
                    tags.append(p['type'])
                    break # 避免重複添加同一種型態
        
        # 條件 C: 偵測到新高/新低事件
        for e in events:
            if "新高" in e['type'] or "新低" in e['type']:
                tags.append(e['type'])

        # 如果符合任一條件，加入 Highlights 列表
        if is_high_volatility or len(tags) > 0:
            highlights.append({
                "item": item,
                "price": latest_price,
                "change_pct": change_pct,
                "tags": tags
            })

    # 4. 生成報告內容
    print("🧠 正在呼叫 Gemini 進行分析...")
    
    # 將 Highlights 依照波動幅度排序 (讓 AI 先看到波動大的)
    if highlights:
        highlights.sort(key=lambda x: abs(x['change_pct']), reverse=True)
    
    # 呼叫 AI 生成文案
    ai_script, color = generate_ai_script(market_stats, highlights)

    # 5. 製作 Discord Embeds
    embeds = []
    
    # 卡片 1: AI 主播分析
    embeds.append({
        "title": f"🎙️ 托蘭市場日報 ({now.strftime('%m/%d')})",
        "description": ai_script,
        "color": color,
        "thumbnail": {"url": "https://cdn-icons-png.flaticon.com/512/6997/6997662.png"}
    })

    # 卡片 2: 精選數據看板 (Top 8)
    if highlights:
        fields = []
        # 只顯示前 8 名，避免版面過長
        for h in highlights[:9]: 
            emoji = "🚀" if h['change_pct'] > 0 else ("🩸" if h['change_pct'] < 0 else "➖")
            
            # 處理標籤顯示格式
            tag_display = ""
            if h['tags']:
                tag_display = f"\n└ {', '.join(h['tags'])}"

            fields.append({
                "name": f"{h['item']}",
                "value": f"{emoji} {h['change_pct']:+.1f}% | ${h['price']:,.0f}{tag_display}",
                "inline": True
            })
            
        embeds.append({
            "title": "📋 精選數據看板",
            "color": 3447003, # 深藍色
            "fields": fields
        })

    # 6. 發送
    print("📤 準備發送 Discord...")
    send_discord_webhook(embeds)

if __name__ == "__main__":
    main()