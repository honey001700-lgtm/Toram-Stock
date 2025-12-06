# test_api.py
import os
import requests

# 請確認這裡能讀到你的 KEY
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

def test_gemini():
    if not API_KEY:
        print("❌ 錯誤：找不到 GEMINI_API_KEY 環境變數")
        return

    print(f"🔑 使用 Key (前四碼): {API_KEY[:4]}****")
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{"parts": [{"text": "哈囉，請回覆 'OK' 兩個字就好。"}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"📡 HTTP 狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 測試成功！回應內容：")
            print(response.json())
        else:
            print("❌ 測試失敗。Google 回傳的錯誤訊息如下：")
            print(response.text) # 這是關鍵！請把這行顯示的內容貼給我看
            
    except Exception as e:
        print(f"💥 程式崩潰: {e}")

if __name__ == "__main__":
    test_gemini()