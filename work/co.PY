import cv2
import numpy as np
import mss
import pygetwindow as gw
import time

# ==========================================
# 1. 這裡填入你想檢查的座標
# ==========================================
GAME_TITLE = "ToramOnline"

# 你剛剛提供的座標
CHECK_REGIONS = {
    "AMOUNT_REGION": {"top": 200, "left": 477, "width": 28, "height": 45},
    "PRICE_REGION":  {"top": 200, "left": 980, "width": 220, "height": 45}
}

# ==========================================
# 2. 執行檢查
# ==========================================
def draw_debug_boxes():
    print("⏳ 尋找遊戲視窗中...")
    try:
        # 取得遊戲視窗
        windows = gw.getWindowsWithTitle(GAME_TITLE)
        if not windows:
            print(f"❌ 找不到 '{GAME_TITLE}'，請先開啟遊戲。")
            return
        
        window = windows[0]
        if not window.isActive:
            window.activate()
            time.sleep(1) # 等待視窗彈出

        print(f"✅ 鎖定視窗: {window.title} ({window.width}x{window.height})")
        
        with mss.mss() as sct:
            # 截取整個遊戲視窗
            monitor = {
                "top": window.top, 
                "left": window.left, 
                "width": window.width, 
                "height": window.height
            }
            img = np.array(sct.grab(monitor))
            
            # 轉換顏色 (MSS 是 BGRA，OpenCV 需要 BGR)
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # 開始畫框框
            for name, r in CHECK_REGIONS.items():
                x = r["left"]
                y = r["top"]
                w = r["width"]
                h = r["height"]
                
                # 設定顏色
                if "PRICE" in name:
                    color = (0, 0, 255) # 紅色 (價格)
                else:
                    color = (255, 0, 0) # 藍色 (數量)

                # 畫矩形
                cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
                
                # 寫上標籤文字
                cv2.putText(img, name, (x, y - 5), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # 存檔
            filename = "check_range.png"
            cv2.imwrite(filename, img)
            print(f"📸 截圖已儲存為: {filename}")
            print("請打開這張圖片，確認框框是否剛好包住數字！")
            
            # 直接彈出視窗顯示 (按任意鍵關閉)
            cv2.imshow("Debug View", img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")

if __name__ == "__main__":
    draw_debug_boxes()