# save as: get_pos.py
import pyautogui
import time
import pygetwindow as gw
import os

# ⚠️ 請確認你的遊戲視窗標題名稱正確
GAME_TITLE = "ToramOnline" 

def main():
    print(f"🔍 正在搜尋視窗: {GAME_TITLE}...")
    try:
        window = gw.getWindowsWithTitle(GAME_TITLE)[0]
        print(f"✅ 鎖定視窗！左上角位於: ({window.left}, {window.top})")
        print("------------------------------------------------")
        print("現在顯示的是 [遊戲內相對座標] (X=-0~1280, Y=-0~720)")
        print("請將這些數字填入 Bot 的 COORDS 中")
        print("------------------------------------------------")
        
        while True:
            abs_x, abs_y = pyautogui.position()
            # 計算相對位置
            rel_x = abs_x - window.left
            rel_y = abs_y - window.top
            
            # 格式化輸出
            print(f"\r📍 相對座標: ({rel_x}, {rel_y}) | 絕對座標: ({abs_x}, {abs_y})    ", end="")
            time.sleep(0.1)
            
    except IndexError:
        print(f"❌ 找不到 '{GAME_TITLE}'，請確認遊戲已開啟。")
    except KeyboardInterrupt:
        print("\n結束。")

if __name__ == "__main__":
    main()