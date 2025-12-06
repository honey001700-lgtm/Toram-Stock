# analysis/patterns.py
import pandas as pd
import numpy as np

# 3️⃣ AI 型態偵測
def detect_patterns(df):
    """
    簡單規則型態偵測 (非嚴格)
    """
    patterns = []
    price = df['單價'].values
    N = len(df)
    
    if N < 50: return patterns

    # --- 1. 區間盤整 (高點低點變化極小) ---
    max_price = price.max()
    min_price = price.min()
    volatility = (max_price - min_price) / min_price
    
    if volatility < 0.05: # 5% 以內波動
        patterns.append({
            'type': '區間盤整',
            'start_idx': 0,
            'end_idx': N - 1,
            'lines': [[min_price, min_price], [max_price, max_price]]
        })
        return patterns # 區間盤整優先度高，偵測到就返回

    # --- 2. 雙頂/雙底 (W/M 型態) ---
    window = int(N * 0.2) # 20% 區間
    
    # 簡化雙頂 (M) 偵測
    max_idx = np.argmax(price)
    if max_idx > window and max_idx < N - window:
        peak1_idx = np.argmax(price[:max_idx - 5])
        peak2_idx = np.argmax(price[max_idx + 5:]) + max_idx + 5
        
        if peak1_idx < max_idx < peak2_idx and \
           abs(price[peak1_idx] - price[peak2_idx]) / price[peak1_idx] < 0.02 and \
           price[peak1_idx] > df['單價'].mean():
            
            patterns.append({
                'type': '雙頂',
                'start_idx': peak1_idx,
                'end_idx': peak2_idx,
                'lines': [[price[peak1_idx], price[peak2_idx]]]
            })

    # 簡化雙底 (W) 偵測
    min_idx = np.argmin(price)
    if min_idx > window and min_idx < N - window:
        trough1_idx = np.argmin(price[:min_idx - 5])
        trough2_idx = np.argmin(price[min_idx + 5:]) + min_idx + 5
        
        if trough1_idx < min_idx < trough2_idx and \
           abs(price[trough1_idx] - price[trough2_idx]) / price[trough1_idx] < 0.02 and \
           price[trough1_idx] < df['單價'].mean():
            
            patterns.append({
                'type': '雙底',
                'start_idx': trough1_idx,
                'end_idx': trough2_idx,
                'lines': [[price[trough1_idx], price[trough2_idx]]]
            })

    # (頭肩/反頭肩、通道、三角收斂等複雜型態省略，以保持程式碼可讀性與執行速度)

    return patterns

# 9️⃣ 影響事件標註
def detect_events(df):
    """偵測價格突變、新高新低、連續漲跌等事件。"""
    events = []
    
    df['Price_Change'] = df['單價'].diff()
    df['Pct_Change'] = df['單價'].pct_change()
    
    # 1. 新高/新低
    df['Cumulative_Max'] = df['單價'].cummax()
    df['Cumulative_Min'] = df['單價'].cummin()
    
    new_highs = df[df['單價'] == df['Cumulative_Max']].index
    new_lows = df[df['單價'] == df['Cumulative_Min']].index
    
    for idx in new_highs:
        if idx > 0 and df.iloc[idx]['單價'] > df.iloc[idx-1]['單價']:
            events.append({'index': idx, 'type': '新高'})

    for idx in new_lows:
        if idx > 0 and df.iloc[idx]['單價'] < df.iloc[idx-1]['單價']:
            events.append({'index': idx, 'type': '新低'})

    # 2. 價格突變 (幅度超過平均波動 3 倍)
    std_change = df['Price_Change'].std()
    threshold = 3 * std_change
    
    abnormal_jumps = df[(df['Price_Change'].abs() > threshold) & (df['Price_Change'].abs() > df['單價'].mean() * 0.01)].index
    
    for idx in abnormal_jumps:
        change_type = "暴漲" if df.loc[idx, 'Price_Change'] > 0 else "暴跌"
        events.append({'index': idx, 'type': f'{change_type}突變'})
        
    return events