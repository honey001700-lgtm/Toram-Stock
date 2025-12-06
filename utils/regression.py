# utils/regression.py
import pandas as pd
import numpy as np
from scipy.stats import linregress

def calculate_r_squared(df):
    """計算整個數據範圍的線性回歸 R²。"""
    if len(df) < 2:
        return None, None
        
    x_nums = np.arange(len(df))
    
    # 線性回歸
    z = np.polyfit(x_nums, df['單價'], 1)
    p = np.poly1d(z)
    
    # R-squared (決定係數)
    y_mean = np.mean(df['單價'])
    ss_tot = np.sum((df['單價'] - y_mean)**2)
    ss_res = np.sum((df['單價'] - p(x_nums))**2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    return r_squared, p(x_nums) # 返回 R² 和預測的 Y 值