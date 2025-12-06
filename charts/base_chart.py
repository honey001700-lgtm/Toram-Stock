# charts/base_chart.py
import plotly.graph_objects as go
import pandas as pd
from utils.theme import TV_THEME, PLOTLY_LAYOUT
from charts.indicators import *
from charts.overlays import *

# 8️⃣ 基礎圖表繪製 (帶高級視覺效果)
def create_flagship_chart(df, item_name, indicator_config, analysis_data):
    """
    創建 TradingView 風格的價格追蹤圖表。
    :param df: 經過過濾和處理的 DataFrame
    :param item_name: 物品名稱
    :param indicator_config: 指標顯示配置
    :param analysis_data: AI 分析結果
    :return: Plotly Figure
    """
    if df.empty:
        return go.Figure()

    fig = go.Figure()
    
    # --- 1. 主價格線 (亮綠色，帶漸層填充, 8️⃣ 柔光效果) ---
    # 使用線條陰影/邊框模擬發光效果 (Plotly 無法直接做 CSS text-shadow，只能靠顏色與線寬)
    fig.add_trace(go.Scatter(
        x=df['時間'], 
        y=df['單價'],
        mode='lines+markers',
        name='成交價',
        line=dict(color=TV_THEME['COLOR_UP'], width=3), # 較寬線條
        marker=dict(size=6, color=TV_THEME['COLOR_UP'], line=dict(width=1, color='white')),
        fill='tozeroy',
        fillcolor='rgba(8, 153, 129, 0.15)', # 20% 透明度的綠色漸層
        hovertemplate='<b>%{x|%Y-%m-%d %H:%M}</b><br>價格: $%{y:,.0f}<extra></extra>'
    ))

    # --- 2. 應用技術指標 (4️⃣, 5️⃣, 6️⃣, 7️⃣) ---
    df_with_indicators = df.copy()
    df_with_indicators = add_ma_ema_traces(fig, df_with_indicators, indicator_config)
    df_with_indicators = add_bollinger_bands(fig, df_with_indicators, indicator_config)
    add_vwap_trace(fig, df_with_indicators, indicator_config)
    add_regression_trace(fig, df_with_indicators, indicator_config) # 🔴 不再接收 r_squared 返回值

    # --- 3. 應用 AI 覆蓋層 (2️⃣, 3️⃣, 9️⃣) ---
    if indicator_config['AI_Overlay']:
        add_support_resistance_lines(fig, df, analysis_data['sr_analysis'])
        add_pattern_traces(fig, df, analysis_data['pattern_analysis'])
        add_event_markers(fig, df, analysis_data['event_analysis'])

    # --- 4. 基礎佈局設定 (TradingView 風格核心) ---
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=f"💎 {item_name}", font=dict(size=24, color=TV_THEME['COLOR_TEXT'])),
        
        # X軸設定 (日期範圍選擇器, 1️⃣1️⃣)
        xaxis=dict(
            type="date",
            gridcolor=TV_THEME['GRID'],
            linecolor=TV_THEME['LINE_AXIS'],
            rangeslider=dict(visible=True, bgcolor="#2a2e39"),
            rangeselector=dict(
                buttons=list([
                    dict(count=7, label="1W", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(step="all", label="All")
                ]),
                bgcolor="#2a2e39",
                font=dict(color=TV_THEME['COLOR_TEXT'])
            )
        ),
        
        # Y軸設定 (價格右側顯示)
        yaxis=dict(
            title="單價 (Spina)",
            tickformat=",",
            side="right",
            gridcolor=TV_THEME['GRID'],
            zerolinecolor=TV_THEME['GRID'],
            autorange=True # 自動調整Y軸範圍
        ),
        
        # 懸停模式 (十字準線)
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, 
            xanchor="right", x=1, bgcolor=TV_THEME['BG_PAPER']
        ),
        # 啟用區間選取分析器 (1️⃣0️⃣) - 透過 Streamlit 的點擊/選取事件處理
        dragmode='select'
    )

    return fig