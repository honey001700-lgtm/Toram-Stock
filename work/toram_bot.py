import re
import time
import cv2
import numpy as np
import mss
import pydirectinput
import easyocr
import pyperclip
import pygetwindow as gw
import requests

# ==========================================
# 0. 全域加速設定
# ==========================================
pydirectinput.PAUSE = 0.01 

# ==========================================
# 1. 核心設定區
# ==========================================
GAME_TITLE = "ToramOnline"

GOOGLE_FORM_CONFIG = {
    "URL": "https://docs.google.com/forms/d/e/1FAIpQLSfiHCTUAwRjmdvTbPQaJQ7lttdrwDEclr_pAn--9PtIZ89KxQ/formResponse", 
    "ENTRY_NAME": "entry.1808413303",
    "ENTRY_ATTR": "entry.274589927",
    "ENTRY_PRICE": "entry.747077800"
}

TARGET_ITEMS = [
    {"search_text": "東・普羅芬多", "save_as": "東．普羅芬多", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "魔晶獸", "save_as": "魔晶獸", "attr": "武器王石", "slot": "-", "mode": "normal", "search_pos": (385, 400)},
    {"search_text": "香菇咪", "save_as": "香菇咪", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "移儡原生素體", "save_as": "移儡原生素體", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "巴圖德", "save_as": "巴圖德", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "蔓迪", "save_as": "蔓迪", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "爆山", "save_as": "爆山", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "斯圖姆恩", "save_as": "斯圖姆恩", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "惡龍法奇諾", "save_as": "惡龍法奇諾", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "隆迪奈", "save_as": "隆迪奈", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "真・", "save_as": "真·魔晶獸", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "寄生甲獸", "save_as": "寄生甲獸", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "迪亞克", "save_as": "迪亞克", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "功夫龍波姆", "save_as": "功夫龍波姆", "attr": "武器王石", "slot": "-", "mode": "normal", "search_pos": (385, 400)},
    {"search_text": "功夫龍波姆 Ⅱ", "save_as": "功夫龍波姆II", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "功夫龍波姆 Ⅲ", "save_as": "功夫龍波姆III", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "魔糰子", "save_as": "魔糰子", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "不比兔", "save_as": "不比兔", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "黑衣聖誕公主", "save_as": "黑衣聖誕公主", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "轟龍波比納利", "save_as": "轟龍波比納利", "attr": "武器王石", "slot": "-", "mode": "normal"},
    {"search_text": "豪德威斯", "save_as": "豪德威斯", "attr": "武器王石", "slot": "-", "mode": "normal"},

    {"search_text": "魅露瑟哈爾", "save_as": "魅露瑟哈爾", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "晶瑪體", "save_as": "晶瑪體", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "似曜隕石", "save_as": "似曜隕石", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "穆爾貢之手", "save_as": "穆爾貢之手", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "鼯忍", "save_as": "鼯忍", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "黑桃忍者", "save_as": "黑桃忍者", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "兔美", "save_as": "兔美", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "兔麻糬", "save_as": "兔麻糬", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "諾耶莉爾", "save_as": "諾耶莉爾", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "諾耶莉爾冰雕", "save_as": "諾耶莉爾冰雕", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "約爾拉茲", "save_as": "約爾拉茲", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "蓋格納", "save_as": "蓋格納", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "黑暗貝莉", "save_as": "黑暗貝莉", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "巧酥獅", "save_as": "巧酥獅", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "DX法伊特", "save_as": "DX法伊特", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "DX法伊特 Ⅱ", "save_as": "DX法伊特II", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "阿魯塔達爾", "save_as": "阿魯塔達爾", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "席比拉雷斯", "save_as": "席比拉雷斯", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "斃魔斯", "save_as": "斃魔斯", "attr": "防具王石", "slot": "-", "mode": "normal"},
    {"search_text": "獅哥東", "save_as": "獅哥東", "attr": "防具王石", "slot": "-", "mode": "normal"},

    {"search_text": "草龍耶弗", "save_as": "草龍耶弗", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "戈爾多", "save_as": "戈爾多", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "薄暮巨龍", "save_as": "薄暮巨龍", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "巴瘋魔", "save_as": "巴瘋魔", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "深謀的青影", "save_as": "深謀的青影", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "禁忌舞者", "save_as": "禁忌舞者", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "古拉", "save_as": "古拉", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "擔輪普原生素幼體", "save_as": "擔輪普原生素幼體", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "巧克流漿", "save_as": "巧克流漿", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "凝膠糖精", "save_as": "凝膠糖精", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "凝膠糖精Ⅱ", "save_as": "凝膠糖精II", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "阿瑪爾貢", "save_as": "阿瑪爾貢", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "甜納許", "save_as": "甜納許", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "愛亞克", "save_as": "愛亞克", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "祖庫托", "save_as": "哥布林·祖庫托", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "王之鬥牛王Ⅱ", "save_as": "王之鬥牛王II", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "魔力費雷西亞", "save_as": "魔力費雷西亞", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "吉普莉爾 Ⅲ", "save_as": "吉普莉爾III", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "卡斯蒂莉亞", "save_as": "卡斯蒂莉亞", "attr": "追加王石", "slot": "-", "mode": "normal"},
    {"search_text": "鯊魚波多姆", "save_as": "鯊魚波多姆", "attr": "追加王石", "slot": "-", "mode": "normal"},

    {"search_text": "甜點精", "save_as": "甜點精", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "席卡諾加米", "save_as": "席卡諾加米", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "黑利古希", "save_as": "黑利古希", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "修米達", "save_as": "修米達", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "寄生樹", "save_as": "寄生樹", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "布利塔", "save_as": "布利塔", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "伏爾加", "save_as": "龍．伏爾加", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "星之魔導士", "save_as": "星之魔導士", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "茄龍歐瓦比昂", "save_as": "茄龍歐瓦比昂", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "叫聲的禍影", "save_as": "叫聲的禍影", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    {"search_text": "機械神梅普露", "save_as": "機械神梅普露", "attr": "特殊王石", "slot": "-", "mode": "normal"},
    
    {"search_text": "休斯古巨獸", "save_as": "休斯古巨獸", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "奴雷德斯", "save_as": "奴雷德斯", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "毗奴古爾迦", "save_as": "毗奴古爾迦", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "大果怪", "save_as": "大果怪", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "麗瑪希娜", "save_as": "麗瑪希娜", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "金屬刺蠍", "save_as": "金屬刺蠍", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "變異幽靈牛", "save_as": "變異幽靈牛", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "枯飛葉", "save_as": "枯飛葉", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "奧狄隆馬其納", "save_as": "奧狄隆馬其納", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "壓釘機", "save_as": "壓釘機", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "百合冠", "save_as": "百合冠", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "雷諾萊犀", "save_as": "雷諾萊犀", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "暴獸利古希", "save_as": "暴獸利古希", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "彼方殘影", "save_as": "彼方殘影", "attr": "通用王石", "slot": "-", "mode": "normal"},
    {"search_text": "科隆教父", "save_as": "科隆教父", "attr": "通用王石", "slot": "-", "mode": "normal"},
    
    {"search_text": "魔法戰士之書", "save_as": "魔法戰士之書", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "暗黑之書", "save_as": "暗黑之書", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "吟遊詩人之書", "save_as": "吟遊詩人之書", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "舞者之書", "save_as": "舞者之書", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "忍之書", "save_as": "忍之書", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "徒手戰鬥之書", "save_as": "徒手戰鬥之書", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "死靈術師之書", "save_as": "死靈法師之書", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "有裂痕的黑結晶", "save_as": "有裂痕的黑結晶", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "水底的遺失物", "save_as": "水底的遺失物", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "水底的鏽塊", "save_as": "水底的鏽塊", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "水底的木箱", "save_as": "水底的木箱", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "水底的寂靜", "save_as": "水底的寂靜", "attr": "其他雜項", "slot": "-", "mode": "normal"},
    {"search_text": "10周年歡慶箱", "save_as": "10周年歡慶箱", "attr": "其他雜項", "slot": "-", "mode": "normal"},

    {"search_text": "霞的武士刀", "save_as": "霞的武士刀", "attr": "不限洞", "slot": "-", "mode": "normal"},
    {"search_text": "佩司博拉多", "save_as": "佩司博拉多", "attr": "不限洞", "slot": "-", "mode": "normal"},
    {"search_text": "梅普露的盾", "save_as": "梅普露的盾", "attr": "不限洞", "slot": "-", "mode": "normal"},

    {"search_text": "米特髮箍", "save_as": "米特髮箍", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "薔薇眼罩", "save_as": "薔薇眼罩", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "側馬尾", "save_as": "側馬尾", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "疼痛的右臂", "save_as": "疼痛的右臂", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "薑餅人眨眼", "save_as": "薑餅人眨眼", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "怪物墨水", "save_as": "怪物墨水", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "野漠頭巾", "save_as": "野漠頭巾", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "休美蝶髮夾", "save_as": "休美蝶髮夾", "attr": "雙洞", "slot": 2, "mode": "normal"},

    {"search_text": "海馬手環", "save_as": "海馬手環", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "鱷魚皮吊飾", "save_as": "鱷魚皮吊飾", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "樹樁戰鼓", "save_as": "樹樁戰鼓", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "波花護符", "save_as": "波花護符", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "海星手裏劍", "save_as": "海星手裏劍", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "龍環", "save_as": "龍環", "attr": "雙洞", "slot": 2, "mode": "normal"},
    {"search_text": "穿越時空的懷錶", "save_as": "穿越時空的懷錶", "attr": "雙洞", "slot": 2, "mode": "normal"},

    {"search_text": "巴拉迪奧之槍", "save_as": "巴拉迪奧之槍", "attr": "外觀", "slot": "-", "mode": "app"},
    {"search_text": "巴拉迪奧魔杖", "save_as": "巴拉迪奧魔杖", "attr": "外觀", "slot": "-", "mode": "app"},
    {"search_text": "櫻嵐", "save_as": "櫻嵐・仿製品", "attr": "外觀", "slot": "-", "mode": "app"},
    {"search_text": "八咫烏", "save_as": "八咫烏", "attr": "外觀", "slot": "-", "mode": "app"},
    {"search_text": "虹霓", "save_as": "虹霓", "attr": "外觀", "slot": "-", "mode": "app"},
    {"search_text": "虹鏡", "save_as": "虹鏡", "attr": "外觀", "slot": "-", "mode": "app"},
    {"search_text": "鯊魚泳裝", "save_as": "鯊魚泳裝", "attr": "外觀", "slot": "-", "mode": "app"},
    {"search_text": "SPA套裝", "save_as": "SPA套裝", "attr": "外觀", "slot": "-", "mode": "app"},
]

# ==========================================
# 2. 座標設定 (預設值)
# ==========================================
COORDS = {
    # 介面操作
    "BTN_USE_MARKET": (660, 400),
    "BTN_BUY_ITEM": (660, 500),
    "BTN_SORT_PRICE": (660, 480),
    "BTN_WORLD_MARKET": (935, 315),
    "SCROLL_AREA": (875, 314),
    "BTN_SLOT_CLICK": (660, 410),
    "BTN_TYPE_APP": (660, 625),
    "MOUSE_RESET": (660, 400),

    # 搜尋流程
    "BTN_OPEN_INPUT": (660, 275),
    "INPUT_BOX": (660, 240),
    "BTN_SEARCH_TARGET": (390, 340), # 預設搜尋按鈕位置
    "BTN_CONFIRM_SEARCH": (1025, 200),  
    
    # 截圖區域
    "AMOUNT_REGION": {"top": 200, "left": 477, "width": 28, "height": 45},
    "PRICE_REGION":  {"top": 200, "left": 980, "width": 220, "height": 45}
}

# ==========================================
# 3. 數據上傳模組
# ==========================================
class DataManager:
    def __init__(self):
        self.config = GOOGLE_FORM_CONFIG
        self.session = requests.Session()
        
    def save(self, name, attr, price):
        form_data = {
            self.config["ENTRY_NAME"]: name,
            self.config["ENTRY_ATTR"]: attr,
            self.config["ENTRY_PRICE"]: str(price)
        }
        try:
            response = self.session.post(self.config["URL"], data=form_data, timeout=3)
            if response.status_code == 200:
                print(f"✅ 上傳成功: {name} | ${price:,.0f}")
            else:
                print(f"⚠️ 上傳失敗 (Code: {response.status_code})")
        except Exception as e:
            print(f"❌ 網路錯誤: {e}")

# ==========================================
# 4. 機器人主程式
# ==========================================
class ToramBot:
    def __init__(self):
        print("🚀 初始化中... (支援自定義座標版)")
        self.reader = easyocr.Reader(['en'], gpu=True) 
        self.db = DataManager()
        self.sct = mss.mss()
        
        try:
            self.window = gw.getWindowsWithTitle(GAME_TITLE)[0]
            if not self.window.isActive: 
                self.window.activate()
                time.sleep(0.5)
        except IndexError:
            print(f"❌ 找不到 '{GAME_TITLE}'")
            exit()

    # 🛠️ 修改點 1: 讓 click 支援字串(查表) 或 元組(直接座標)
    def click(self, target, delay=0.2): 
        if isinstance(target, str):
            # 如果是字串，去 COORDS 查表
            rx, ry = COORDS[target]
        elif isinstance(target, tuple):
            # 如果是元組，直接使用該座標
            rx, ry = target
        else:
            print(f"❌ 座標格式錯誤: {target}")
            return

        # 加上視窗偏移量
        x = self.window.left + rx
        y = self.window.top + ry
        
        pydirectinput.moveTo(x, y)
        time.sleep(0.1) 
        pydirectinput.click()
        if delay > 0: time.sleep(delay)

    def scroll_ui(self):
        # 這裡也要用 self.window.left/top 因為沒有用 click 函式
        scroll_def = COORDS["SCROLL_AREA"]
        bx = self.window.left + scroll_def[0]
        by = self.window.top + scroll_def[1]

        pydirectinput.moveTo(bx, by + 200)
        pydirectinput.mouseDown()
        for _ in range(5):
            pydirectinput.moveRel(0, int(-400/5))
            time.sleep(0.02)
        pydirectinput.mouseUp()
        time.sleep(0.5) 

    # 🛠️ 修改點 2: 增加 custom_pos 參數
    def input_search(self, text, custom_pos=None):
        self.click("BTN_OPEN_INPUT", 0.3)
        self.click("INPUT_BOX", 0.3)
        pyperclip.copy(text)
        pydirectinput.keyDown('ctrl'); time.sleep(0.1)
        pydirectinput.press('v'); time.sleep(0.1)
        pydirectinput.keyUp('ctrl'); time.sleep(0.1)
        pydirectinput.press('enter')
        time.sleep(0.8) 
        
        # 判斷是否使用特例座標
        if custom_pos:
            print(f"👉 使用特例座標點擊搜尋: {custom_pos}")
            self.click(custom_pos, 0.1)
        else:
            self.click("BTN_SEARCH_TARGET", 0.3) 
        
        # 確認搜尋按鈕 (右上角那個)
        self.click("BTN_CONFIRM_SEARCH", 0.3)
        
        # 移開滑鼠
        self.click("MOUSE_RESET", 1.0)

    # 🛠️ 新增修改點：接收 item 參數，判斷是否為單一數量
    def get_number_from_screen(self, region_key, is_price=False):
        r = COORDS[region_key]
        monitor = {
            "top": self.window.top + r["top"], 
            "left": self.window.left + r["left"], 
            "width": r["width"], 
            "height": r["height"]
        }
        try:
            img = np.array(self.sct.grab(monitor))
            img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
            _, bn = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
            bn = cv2.copyMakeBorder(bn, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=[255, 255, 255])

            # 允許的字符集：數字、括號、逗號、's' (OCR有時會將數字識別成s)
            res = self.reader.readtext(bn, detail=0, allowlist='0123456789(),s')
            if not res: return None
            
            full_text = "".join(res)
            # 清理所有非數字字符
            clean_text = re.sub(r'[^\d]', '', full_text)
            
            if not clean_text: return None
            return int(clean_text)

        except Exception as e:
            print(f"⚠️ 截圖錯誤: {e}")
            return None

    # 🛠️ 新增修改點：根據 item 判斷是否強制數量為 1
    def get_unit_price(self, item): 
        total_price = self.get_number_from_screen("PRICE_REGION", is_price=True)
        if total_price is None: return None
        
        # 判斷是否為單一數量物品（有洞數限制或外觀）
        is_single_item = (item.get("slot", "-") != "-") or (item.get("mode") == "app")

        if is_single_item:
            # 強制設定數量為 1
            amount = 1
            print(f"🔎 (單一數量, Slot/外觀) 價格: ${total_price}")
        else:
            # 嘗試 OCR 讀取數量
            amount = self.get_number_from_screen("AMOUNT_REGION")
            if amount is None or amount == 0: amount = 1 
            print(f"🔎 價格: ${total_price} / 數量: {amount}")
            
        return int(total_price / amount)

    def run_cycle(self, item):
        print(f"📍 查詢: {item['save_as']}")
        
        for _ in range(3):
            pydirectinput.press('f'); time.sleep(0.2)
        time.sleep(0.2) 
        
        self.click("BTN_USE_MARKET", 0.6)
        self.click("BTN_BUY_ITEM", 0.1)
        self.click("BTN_SORT_PRICE", 0.5)
        self.click("BTN_WORLD_MARKET", 0.5)
        self.scroll_ui()

        slot = item.get("slot")
        clicks = 0
        if slot == 2: clicks = 3
        elif slot == 1: clicks = 2
        elif slot == 0: clicks = 1
        if clicks > 0:
            for _ in range(clicks): self.click("BTN_SLOT_CLICK", 0.3)

        if item.get("mode") == "app": self.click("BTN_TYPE_APP", 0.4)

        # 🛠️ 修改點 3: 讀取 item 設定中的 search_pos 並傳遞
        custom_pos = item.get("search_pos") # 如果沒有設定，會拿到 None
        self.input_search(item["search_text"], custom_pos)
        
        # 🛠️ 修改點 4: 傳入 item 字典給 get_unit_price
        price = self.get_unit_price(item) 

        if price: self.db.save(item["save_as"], item.get("attr", "Auto"), price)
        else: print(f"⚠️ 讀取失敗")
            
        print("🔄 退出")
        pydirectinput.press('esc') 
        time.sleep(1.0)

if __name__ == "__main__":
    print("=== 托蘭機器人 (自定義搜尋按鈕版) ===")
    print("3秒後開始...")
    time.sleep(3)
    bot = ToramBot()
    for item in TARGET_ITEMS:
        try:
            bot.run_cycle(item)
            time.sleep(0.5) 
        except Exception as e:
            print(f"❌ 錯誤: {e}")
            pydirectinput.press('esc')
            time.sleep(1)