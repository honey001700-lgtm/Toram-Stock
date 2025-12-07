# analysis/support_resistance.py
import pandas as pd
import numpy as np
from scipy.signal import find_peaks

# 2️⃣ AI 自動偵測支撐/阻力
def find_support_resistance(df):
    """
    使用 Peak Finding 算法偵測主要 S/R 點。
    """
    if len(df) < 50:
        return {'support': [df['單價'].min()], 'resistance': [df['單價'].max()]}

    price = df['單價'].values
    # 🔴 修正：使用價格的 1% 作為 Prominence，更具價格意義
    prominence_threshold = df['單價'].mean() * 0.01 
    # 距離至少間隔 5 筆資料或總長度的 5%
    distance_threshold = int(len(df) * 0.05) or 5 
    
    # 1. 偵測局部波峰 (Peaks - 潛在阻力)
    peaks, _ = find_peaks(price, prominence=prominence_threshold, distance=distance_threshold) 
    resistance_levels = price[peaks].tolist()
    
    # 2. 偵測局部波谷 (Troughs - 潛在支撐)
    troughs, _ = find_peaks(-price, prominence=prominence_threshold, distance=distance_threshold)
    support_levels = price[troughs].tolist()

    # 3. 聚類分析 (將相似價格歸為同一 S/R 線)
    def cluster_levels(levels, tolerance_percent=0.03): # 使用 3% 寬容度
        if not levels: return []
        levels = sorted(levels)
        final_levels = []
        current_cluster = [levels[0]]
        
        for i in range(1, len(levels)):
            # 判斷是否在容忍度內
            if (levels[i] - current_cluster[0]) / current_cluster[0] <= tolerance_percent:
                current_cluster.append(levels[i])
            else:
                final_levels.append(np.mean(current_cluster))
                current_cluster = [levels[i]]
        final_levels.append(np.mean(current_cluster))
        # 🔴 移除強制取整到千位數
        return final_levels 

    # 4. 取得主要 S/R
    major_resistance = cluster_levels(resistance_levels)
    major_support = cluster_levels(support_levels)
    
    # 🔴 移除過於嚴格的過濾邏輯
    # major_support = [s for s in major_support if s < df['單價'].mean() * 1.05]
    # major_resistance = [r for r in major_resistance if r > df['單價'].mean() * 0.95]

    return {
        'support': [round(s) for s in major_support[-2:]], # 只取最近的兩個並取整
        'resistance': [round(r) for r in major_resistance[:2]] # 只取最近的兩個並取整
    }