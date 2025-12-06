# charts/indicators.py
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from utils.theme import TV_THEME

# 4️⃣ 移動平均線 (MA) 和 EMA
def add_ma_ema_traces(fig, df, config):
    """添加 MA/EMA 指標線。"""
    for window, color in [
        (5, TV_THEME['COLOR_MA5']), 
        (20, TV_THEME['COLOR_MA20']), 
        (60, TV_THEME['COLOR_MA60'])
    ]:
        ma_col = f'MA{window}'
        if config.get(ma_col, False):
            df[ma_col] = df['單價'].rolling(window=window).mean()
            fig.add_trace(go.Scatter(
                x=df['時間'], y=df[ma_col], mode='lines', name=ma_col,
                line=dict(color=color, width=1.5), opacity=0.8, hoverinfo='skip'
            ))

    if config.get('EMA', False):
        df['EMA'] = df['單價'].ewm(span=20, adjust=False).mean()
        fig.add_trace(go.Scatter(
            x=df['時間'], y=df['EMA'], mode='lines', name='EMA(20)',
            line=dict(color=TV_THEME['COLOR_EMA'], width=1.5, dash='dot'), opacity=0.8, hoverinfo='skip'
        ))
    return df

# 5️⃣ 布林通道 (Bollinger Bands)
def add_bollinger_bands(fig, df, config):
    """添加布林通道 (MA20, STD 2)。"""
    if not config.get('BB', False):
        return df
        
    window = 20
    df['MA20'] = df['單價'].rolling(window=window).mean()
    df['STD'] = df['單價'].rolling(window=window).std()
    df['BB_UP'] = df['MA20'] + (df['STD'] * 2)
    df['BB_DOWN'] = df['MA20'] - (df['STD'] * 2)
    
    # 中軌 (MA20) - 沿用 MA20 的線
    if not config.get('MA20', False):
        fig.add_trace(go.Scatter(
            x=df['時間'], y=df['MA20'], mode='lines', name='BB 中軌(MA20)',
            line=dict(color=TV_THEME['COLOR_MA20'], width=1.5), opacity=0.8, hoverinfo='skip'
        ))

    # 上軌
    fig.add_trace(go.Scatter(
        x=df['時間'], y=df['BB_UP'], mode='lines', name='BB 上軌',
        line=dict(color=TV_THEME['COLOR_BB_UP'], width=1), opacity=0.7, hoverinfo='skip'
    ))
    # 下軌 (使用 fill 填充上下軌區域，更美觀)
    fig.add_trace(go.Scatter(
        x=df['時間'], y=df['BB_DOWN'], mode='lines', name='BB 下軌',
        line=dict(color=TV_THEME['COLOR_BB_DOWN'], width=1), opacity=0.7,
        fill='tonexty', fillcolor='rgba(255, 165, 0, 0.1)', # 20% 透明度
        hoverinfo='skip'
    ))
    return df

# 6️⃣ VWAP (成交量加權平均)
def add_vwap_trace(fig, df, config):
    """添加 VWAP (成交量加權平均) 線。"""
    if not config.get('VWAP', False):
        return
        
    # VWAP = 累積(單價 * Volume) / 累積(Volume)
    df['PriceVol'] = df['單價'] * df['Volume']
    df['CumPriceVol'] = df['PriceVol'].cumsum()
    df['CumVolume'] = df['Volume'].cumsum()
    df['VWAP'] = df['CumPriceVol'] / df['CumVolume']

    fig.add_trace(go.Scatter(
        x=df['時間'], y=df['VWAP'], mode='lines', name='VWAP (加權均價)',
        line=dict(color='#FFD700', width=2), opacity=0.9, hoverinfo='skip'
    ))

# 7️⃣ 回歸線 (線性回歸 + R²)
def add_regression_trace(fig, df, config):
    """添加線性回歸線和計算 R²。"""
    if not config.get('Regression', False) or len(df) < 2:
        return None
        
    # 🔴 這裡使用新的 utils 函數來計算
    from utils.regression import calculate_r_squared
    r_squared, y_pred = calculate_r_squared(df)
    
    if r_squared is None: return None
        
    fig.add_trace(go.Scatter(
        x=df['時間'],
        y=y_pred, # 使用計算好的 Y 值
        mode='lines',
        name=f'趨勢回歸線 (R²={r_squared:.2f})',
        line=dict(color=TV_THEME['COLOR_TREND'], width=1, dash='dash'), # 藍色虛線
        opacity=0.8,
        hoverinfo='skip'
    ))
    return r_squared # 返回 R²