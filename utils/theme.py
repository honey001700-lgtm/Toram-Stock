# utils/theme.py

# TradingView 暗黑風格顏色配置
TV_THEME = {
    # 背景與邊界
    "BG_PAPER": "#131722",  # 主背景
    "BG_PLOT": "#131722",   # 圖表區域背景
    "GRID": "#363c4e",      # 網格線
    "LINE_AXIS": "#363c4e", # 座標軸線
    # K線顏色
    "COLOR_UP": "#089981",  # 亮綠色 (漲)
    "COLOR_DOWN": "#F23645", # 亮紅色 (跌)
    "COLOR_TREND": "#2962FF", # 藍色 (趨勢線)
    # 技術指標顏色
    "COLOR_MA5": "#e6a23c", # 橙色
    "COLOR_MA20": "#2962FF", # 藍色
    "COLOR_MA60": "#FF00FF", # 紫色
    "COLOR_EMA": "#00FFFF",  # 青色
    "COLOR_BB_UP": "#FFA500", # 布林上軌
    "COLOR_BB_DOWN": "#9400D3", # 布林下軌
    # 文字
    "COLOR_TEXT": "#d1d4dc",
}

# Plotly Layout 基礎設定
PLOTLY_LAYOUT = {
    "template": "plotly_dark",
    "height": 650,
    "paper_bgcolor": TV_THEME['BG_PAPER'],
    "plot_bgcolor": TV_THEME['BG_PLOT'],
    "font": {"color": TV_THEME['COLOR_TEXT']},
    "margin": dict(l=20, r=80, t=60, b=40) # 讓右側Y軸有空間
}