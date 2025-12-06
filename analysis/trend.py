# analysis/trend.py
import pandas as pd
import numpy as np
from scipy.stats import linregress

# 1️⃣ AI 趨勢分析
def analyze_trend(df):
    """
    根據最近的價格變化進行趨勢分析。
    使用最近 N 筆資料 (N=30)
    """
    N = min(30, len(df))
    if N < 5:
        return {"趨勢方向": "數據不足", "多空強度": 0, "AI統計信心值": 0, "支撐/阻力附近距離": "N/A", "未來短期預測價格": "N/A", "反轉風險提示": "數據不足"}

    recent_df = df.tail(N)
    
    # 1. 線性回歸趨勢 (主要方向)
    x = np.arange(N)
    y = recent_df['單價'].values
    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    
    # 2. 趨勢方向判斷
    if slope > 0.05 * recent_df['單價'].mean() / N:
        trend_dir = "🚀 上升趨勢"
    elif slope < -0.05 * recent_df['單價'].mean() / N:
        trend_dir = "📉 下跌趨勢"
    else:
        trend_dir = "↔️ 震盪盤整"

    # 3. 多空強度 (0-100)
    # 使用斜率的絕對值和 R-squared 結合
    strength_raw = abs(slope) * (r_value ** 2)
    max_strength = recent_df['單價'].std() # 假設最大強度與波動度相關
    strength = min(100, int((strength_raw / max_strength) * 100 * 2)) if max_strength > 0 else 50
    
    # 4. AI 統計信心值 (基於 R-squared)
    confidence = int((r_value ** 2) * 100)
    
    # 5. 未來短期預測 (7點後，簡單線性外推)
    future_x = N + 7
    forecast_price = p_value * future_x + intercept if confidence > 50 else recent_df['單價'].iloc[-1]
    
    # 6. 反轉風險提示 (基於 RSI 概念 - 簡單用價格與 MA20 距離)
    MA20 = recent_df['單價'].rolling(window=20).mean().iloc[-1] if N >= 20 else recent_df['單價'].mean()
    last_price = recent_df['單價'].iloc[-1]
    risk = "低"
    if last_price > MA20 * 1.05 and trend_dir == "🚀 上升趨勢":
        risk = "⚠️ 高 (超買可能)"
    elif last_price < MA20 * 0.95 and trend_dir == "📉 下跌趨勢":
        risk = "⚠️ 高 (超賣可能)"
    
    # 7. 支撐/阻力附近距離 (由 `support_resistance.py` 處理，此處留空)
    
    return {
        "趨勢方向": trend_dir,
        "多空強度": strength,
        "AI統計信心值": confidence,
        "支撐/阻力附近距離": "待計算", # Placeholder
        "未來短期預測價格": f"${forecast_price:,.0f}",
        "反轉風險提示": risk,
        "R_squared": None, # 🔴 新增預設值
    }