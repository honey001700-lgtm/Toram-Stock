import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
from scipy.stats import linregress

# 3️⃣ AI 型態偵測
def detect_patterns(df, window=3):
    """
    進階型態偵測：頭肩型態、三角收斂、通道、雙重頂/底
    保證所有回傳型態都包含 'start_idx' 與 'end_idx'
    """
    patterns = []
    
    # 若資料過少，回傳空的但不報錯
    if len(df) < 15:
        return patterns

    prices = df['單價'].values
    
    # 1. 取得局部高點 (Peaks) 與 低點 (Troughs)
    peak_idxs = argrelextrema(prices, np.greater, order=window)[0]
    trough_idxs = argrelextrema(prices, np.less, order=window)[0]
    
    # 轉換為 (Index, Price) 列表
    peaks = [(i, prices[i]) for i in peak_idxs]
    troughs = [(i, prices[i]) for i in trough_idxs]

    # --- A. 頭肩型態 (Head and Shoulders) ---
    if len(peaks) >= 3:
        p1, p2, p3 = peaks[-3], peaks[-2], peaks[-1]
        if p2[1] > p1[1] and p2[1] > p3[1]:
            shoulder_avg = (p1[1] + p3[1]) / 2
            if abs(p1[1] - p3[1]) / shoulder_avg < 0.15: 
                patterns.append({
                    'type': "👤 頭肩頂 (看跌)",
                    'start_idx': int(p1[0]),
                    'end_idx': int(p3[0]),
                    'lines': [[p1[1], p3[1]]]
                })

    if len(troughs) >= 3:
        t1, t2, t3 = troughs[-3], troughs[-2], troughs[-1]
        if t2[1] < t1[1] and t2[1] < t3[1]:
            shoulder_avg = (t1[1] + t3[1]) / 2
            if abs(t1[1] - t3[1]) / shoulder_avg < 0.15:
                patterns.append({
                    'type': "🧘 頭肩底 (看漲)",
                    'start_idx': int(t1[0]),
                    'end_idx': int(t3[0]),
                    'lines': [[t1[1], t3[1]]]
                })

    # --- B. 雙重頂/底 (Double Top/Bottom) ---
    if len(peaks) >= 2:
        p_last, p_prev = peaks[-1], peaks[-2]
        if abs(p_last[1] - p_prev[1]) / p_last[1] < 0.03:
            patterns.append({
                'type': "Ⓜ️ 雙重頂 (M頭)",
                'start_idx': int(p_prev[0]),
                'end_idx': int(p_last[0])
            })

    if len(troughs) >= 2:
        t_last, t_prev = troughs[-1], troughs[-2]
        if abs(t_last[1] - t_prev[1]) / t_last[1] < 0.03:
             patterns.append({
                'type': "🇼 雙重底 (W底)",
                'start_idx': int(t_prev[0]),
                'end_idx': int(t_last[0])
            })

    # --- C. 趨勢線分析 (三角收斂 與 通道) ---
    if len(peaks) >= 3 and len(troughs) >= 3:
        recent_peak_idxs = peak_idxs[-5:]
        recent_trough_idxs = trough_idxs[-5:]
        
        # 找出這段分析的起點與終點 (轉為 int)
        pattern_start = int(min(recent_peak_idxs[0], recent_trough_idxs[0]))
        pattern_end = int(max(recent_peak_idxs[-1], recent_trough_idxs[-1]))
        
        slope_res, _, _, _, _ = linregress(recent_peak_idxs, prices[recent_peak_idxs])
        slope_sup, _, _, _, _ = linregress(recent_trough_idxs, prices[recent_trough_idxs])
        
        if slope_res < -0.05 and slope_sup > 0.05:
            patterns.append({
                'type': "📐 三角收斂",
                'start_idx': pattern_start,
                'end_idx': pattern_end
            })
        elif slope_res > 0.1 and slope_sup > 0.1:
            if abs(slope_res - slope_sup) < 0.5:
                patterns.append({
                    'type': "🛤️ 上升通道",
                    'start_idx': pattern_start,
                    'end_idx': pattern_end
                })
        elif slope_res < -0.1 and slope_sup < -0.1:
            if abs(slope_res - slope_sup) < 0.5:
                patterns.append({
                    'type': "📉 下降通道",
                    'start_idx': pattern_start,
                    'end_idx': pattern_end
                })

    # --- D. 簡單暴漲暴跌 (安全網) ---
    if not patterns:
        total_change = (prices[-1] - prices[0]) / prices[0]
        max_price = prices.max()
        min_price = prices.min()
        volatility = (max_price - min_price) / min_price if min_price > 0 else 0
        
        default_start = 0
        default_end = len(df) - 1
        
        if total_change > 0.3:
            patterns.append({'type': "🚀 急速拉升", 'start_idx': default_start, 'end_idx': default_end})
        elif total_change < -0.3:
            patterns.append({'type': "🩸 恐慌拋售", 'start_idx': default_start, 'end_idx': default_end})
        elif volatility < 0.05:
            patterns.append({'type': "🦀 區間盤整", 'start_idx': default_start, 'end_idx': default_end})
        else:
            patterns.append({'type': "無明顯型態", 'start_idx': default_start, 'end_idx': default_end})

    return patterns

# 9️⃣ 影響事件標註 (修正版：確保縮排正確)
def detect_events(df):
    """偵測價格突變、新高新低等事件。"""
    events = [] # 1. 初始化列表
    
    if df.empty: 
        return events # 2. 若空則回傳空列表

    try:
        # 避免 SettingWithCopyWarning
        df = df.copy()
        
        df['Price_Change'] = df['單價'].diff()
        
        # 1. 新高/新低
        current_price = df.iloc[-1]['單價']
        cumulative_max = df['單價'].cummax().iloc[-1]
        cumulative_min = df['單價'].cummin().iloc[-1]
        
        if current_price >= cumulative_max:
            events.append({'index': df.index[-1], 'type': '🔥 創歷史新高'})
        elif current_price <= cumulative_min:
            events.append({'index': df.index[-1], 'type': '🧊 創歷史新低'})

        # 2. 價格突變
        std_change = df['Price_Change'].std()
        mean_price = df['單價'].mean()
        last_change = df.iloc[-1]['Price_Change']
        
        # 防止 std_change 為 NaN (例如只有一筆資料)
        if pd.isna(std_change):
            std_change = 0
            
        threshold = 3 * std_change
        
        # 確保波動有一定規模 (至少 1%)
        if abs(last_change) > threshold and abs(last_change)     > mean_price * 0.01:
            change_type = "⚡ 暴漲突變" if last_change > 0 else "⚡ 暴跌突變"
            events.append({'index': df.index[-1], 'type': change_type})
            
    except Exception as e:
        # 發生任何錯誤也回傳空列表，避免 NoneType error
        print(f"Event detection error: {e}")
        return []

    return events # 3. 🔴 關鍵：確保這行縮排在最外層，一定會被執行