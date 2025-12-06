# debug_sdk.py
import os
import requests
import google.generativeai as genai
import datetime

# 1. 取得設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord(title, desc, color, detail=""):
    if not DISCORD_WEBHOOK_URL: return
    payload = {
        "username": "SDK 診斷醫生",
        "embeds": [{
            "title": title,
            "description": desc,
            "color": color,
            "fields": [{"name": "錯誤詳細內容", "value": f"```\n{detail[:900]}\n```"}] if detail else [],
            "footer": {"text": f"測試時間: {datetime.datetime.now()}"}
        }]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

print("🚀 開始 SDK 診斷...")

# 檢查 Key 格式
if not GEMINI_API_KEY:
    send_discord("❌ 錯誤", "找不到 API Key", 15548997)
    exit()

if not GEMINI_API_KEY.startswith("AIza"):
    msg = f"你的 Key 開頭是 '{GEMINI_API_KEY[:4]}...'，這看起來不像 Google AI Studio 的 Key (通常是 AIza 開頭)。"
    send_discord("⚠️ Key 格式可疑", msg, 16776960)

# 設定 SDK
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    send_discord("❌ SDK 設定失敗", "configure 階段就掛了", 15548997, str(e))
    exit()

# 測試 1: 列出可用模型 (確認權限)
try:
    print("📋 正在查詢可用模型...")
    models = []
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            models.append(m.name)
    
    if not models:
        send_discord("❌ 找不到任何模型", "連線成功但沒有可用模型，可能是 API Key 權限不足或未啟用 API。", 15548997)
    else:
        print(f"✅ 找到 {len(models)} 個模型")
        # 測試 2: 嘗試生成
        target_model = "gemini-1.5-flash"
        try:
            model = genai.GenerativeModel(target_model)
            response = model.generate_content("Hi, reply OK.")
            send_discord("✅ 診斷成功", f"成功呼叫 {target_model}！\n回應: {response.text}", 5763719, f"可用模型清單:\n{models[:5]}...")
        except Exception as e:
            send_discord("⚠️ 列出模型成功但生成失敗", f"無法呼叫 {target_model}", 15548997, str(e))

except Exception as e:
    # 這是最關鍵的地方，告訴我們為什麼 SDK 連不到
    send_discord("❌ 連線致命錯誤", "無法列出模型 (list_models 失敗)", 15548997, str(e))