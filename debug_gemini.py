# debug_gemini.py
import os
import requests
import json
import datetime

# 1. 取得設定
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL")

def send_discord_report(status, message, details, color):
    if not DISCORD_WEBHOOK_URL:
        print("❌ 無法發送 Discord (未設定 Webhook)")
        return

    embed = {
        "title": f"🛠️ API 診斷報告: {status}",
        "description": message,
        "color": color, # 綠色或紅色
        "fields": [
            {"name": "詳細回應", "value": f"```json\n{details[:1000]}\n```"} # 限制長度避免爆掉
        ],
        "footer": {"text": f"測試時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
    }
    
    payload = {
        "username": "托蘭維修工",
        "embeds": [embed]
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)

def test_connection():
    print("🚀 開始診斷 Gemini API...")
    
    # 檢查 Key 是否存在
    if not GEMINI_API_KEY:
        msg = "環境變數中找不到 GEMINI_API_KEY"
        print(msg)
        send_discord_report("設定錯誤", msg, "請檢查 GitHub Secrets 設定。", 15548997)
        return

    # 遮蔽 Key 顯示
    masked_key = f"{GEMINI_API_KEY[:5]}...{GEMINI_API_KEY[-3:]}"
    print(f"🔑 使用 Key: {masked_key}")

    # 測試連線 (使用 1.5 Flash，因為它最穩定)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": "哈囉，請回覆 'OK'。"}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        
        # 1. 成功 (HTTP 200)
        if response.status_code == 200:
            result = response.json()
            try:
                reply = result['candidates'][0]['content']['parts'][0]['text']
                msg = f"✅ 連線成功！機器人回應: {reply}"
                print(msg)
                send_discord_report("測試成功", msg, json.dumps(result, indent=2), 5763719) # 綠色
            except:
                msg = "⚠️ 連線成功但解析回應失敗 (格式改變?)"
                send_discord_report("解析異常", msg, response.text, 16776960) # 黃色

        # 2. 失敗 (HTTP 4xx/5xx)
        else:
            error_msg = f"❌ 連線失敗 (HTTP {response.status_code})"
            print(error_msg)
            print(response.text)
            # 這是重點！把 Google 回傳的錯誤訊息傳到 Discord
            send_discord_report("API 錯誤", error_msg, response.text, 15548997) # 紅色

    except Exception as e:
        msg = f"💥 程式執行錯誤: {e}"
        print(msg)
        send_discord_report("系統崩潰", msg, str(e), 0)

if __name__ == "__main__":
    test_connection()