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
    
    # 1. 偵測局部波峰 (Peaks - 潛在阻力)
    # prominence: 峰頂相對兩側谷底的高度差
    peaks, _ = find_peaks(price, prominence=price.std() * 0.3, distance=int(len(df) * 0.05) or 5) 
    resistance_levels = price[peaks].tolist()
    
    # 2. 偵測局部波谷 (Troughs - 潛在支撐)
    troughs, _ = find_peaks(-price, prominence=price.std() * 0.3, distance=int(len(df) * 0.05) or 5)
    support_levels = price[troughs].tolist()

    # 3. 聚類分析 (將相似價格歸為同一 S/R 線)
    def cluster_levels(levels, tolerance_percent=0.015):
        if not levels: return []
        levels = sorted(levels)
        final_levels = []
        current_cluster = [levels[0]]
        
        for i in range(1, len(levels)):
            if (levels[i] - current_cluster[0]) / current_cluster[0] <= tolerance_percent:
                current_cluster.append(levels[i])
            else:
                final_levels.append(np.mean(current_cluster))
                current_cluster = [levels[i]]
        final_levels.append(np.mean(current_cluster))
        return [int(round(l, -3)) for l in final_levels] # 取整到千位，更像實際交易的整數價位

    # 4. 取得主要 S/R
    major_resistance = cluster_levels(resistance_levels, tolerance_percent=0.03)
    major_support = cluster_levels(support_levels, tolerance_percent=0.03)
    
    # 剔除 S/R 靠得太近的 (如 S > R)
    major_support = [s for s in major_support if s < df['單價'].mean() * 1.05]
    major_resistance = [r for r in major_resistance if r > df['單價'].mean() * 0.95]

    return {
        'support': major_support[-2:], # 只取最近的兩個
        'resistance': major_resistance[:2] # 只取最近的兩個
    }