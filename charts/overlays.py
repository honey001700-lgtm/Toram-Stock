import plotly.graph_objects as go
import pandas as pd
import numpy as np

# 嘗試導入主題配置，若無則使用預設值
try:
    from utils.theme import TV_THEME
except ImportError:
    TV_THEME = {'COLOR_UP': '#00FF00', 'COLOR_DOWN': '#FF0000'}

# ==========================================
# 2️⃣ AI 自動偵測支撐/阻力 (Support & Resistance)
# ==========================================
def add_support_resistance_lines(fig, df, sr_data):
    """
    在圖表上繪製支撐和阻力線及區域。
    """
    if not sr_data: 
        return
    
    # 繪製主要支撐線 (S)
    for level in sr_data.get('support', []):
        fig.add_hline(
            y=level, 
            line_dash="dash", 
            line_color="#00CED1", 
            line_width=1, 
            opacity=0.7,
            annotation_text=f"S: {level:,.0f}", 
            annotation_position="bottom right",
            annotation_font=dict(color="#00CED1", size=10)
        )

    # 繪製主要阻力線 (R)
    for level in sr_data.get('resistance', []):
        fig.add_hline(
            y=level, 
            line_dash="dash", 
            line_color="#FF4500", 
            line_width=1, 
            opacity=0.7,
            annotation_text=f"R: {level:,.0f}", 
            annotation_position="top right",
            annotation_font=dict(color="#FF4500", size=10)
        )

    # 繪製 S/R 區域
    if sr_data.get('support') and sr_data.get('resistance'):
        min_s = min(sr_data['support'])
        max_r = max(sr_data['resistance'])
        
        # 支撐區域
        fig.add_shape(type="rect", xref="x", yref="y",
            x0=df['時間'].min(), y0=min_s * 0.99,
            x1=df['時間'].max(), y1=min_s * 1.01,
            line=dict(width=0), fillcolor="rgba(0, 205, 205, 0.15)", layer="below")
        
        # 阻力區域
        fig.add_shape(type="rect", xref="x", yref="y",
            x0=df['時間'].min(), y0=max_r * 0.99,
            x1=df['時間'].max(), y1=max_r * 1.01,
            line=dict(width=0), fillcolor="rgba(255, 69, 0, 0.15)", layer="below")

# ==========================================
# 3️⃣ AI 型態偵測 (Patterns)
# ==========================================
def add_pattern_traces(fig, df, patterns_data):
    """
    在圖表上繪製偵測到的型態。
    - 區間盤整也使用箭頭，指向起始點價格。
    - 無明顯型態被忽略。
    """
    if df.empty or not patterns_data: 
        return

    colors = {
        "👤 頭肩頂 (看跌)": "#FF5252", "🧘 頭肩底 (看漲)": "#00E676",
        "Ⓜ️ 雙重頂 (M頭)": "#FF9100", "🇼 雙重底 (W底)": "#00B0FF",
        "📐 三角收斂": "#E040FB", "🛤️ 上升通道": "#2979FF",
        "📉 下降通道": "#FF1744", "🚀 急速拉升": "#F50057",
        "🩸 恐慌拋售": "#9E9E9E", "🦀 區間盤整": "#607D8B",
        "區間盤整": "#607D8B", "無明顯型態": "#B0BEC5"
    }
    
    # 🔴 最終 ARROW_PATTERNS：包含所有需繪製的型態
    ARROW_PATTERNS = {"👤 頭肩頂 (看跌)", "🧘 頭肩底 (看漲)", 
                      "Ⓜ️ 雙重頂 (M頭)", "🇼 雙重底 (W底)",
                      "📐 三角收斂", "🛤️ 上升通道", "📉 下降通道", 
                      "🚀 急速拉升", "🩸 恐慌拋售", 
                      "🦀 區間盤整", "區間盤整"}


    for i, pattern in enumerate(patterns_data):
        p_type = pattern['type']
        
        if p_type == "無明顯型態":
            continue
        
        # 區間盤整現在也會被包含在 ARROW_PATTERNS 中
        if p_type not in ARROW_PATTERNS:
            continue

        p_start_idx = pattern.get('start_idx')
        p_end_idx = pattern.get('end_idx')
        
        if p_start_idx is None or p_end_idx is None: continue
        
        p_start_idx = max(0, min(int(p_start_idx), len(df)-1))
        p_end_idx = max(0, min(int(p_end_idx), len(df)-1))
        
        start_time = df.iloc[p_start_idx]['時間']
        end_time = df.iloc[p_end_idx]['時間']
        start_price = df.iloc[p_start_idx]['單價']
        end_price = df.iloc[p_end_idx]['單價']
        
        p_color = colors.get(p_type, "#FFFFFF")

        # 決定標註的 X/Y 軸位置 (最終標註時間與價格)
        final_time = start_time
        y_pos = df.iloc[p_start_idx]['單價'] # 預設為起始點價格
        
        
        if p_type in {"🚀 急速拉升", "🩸 恐慌拋售"}:
            # 🔴 急速拉升/恐慌拋售：動態計算「加速/減速開始點」
            pattern_slice = df.iloc[p_start_idx : p_end_idx + 1].copy()
            
            if len(pattern_slice) >= 2:
                pattern_slice['Change'] = pattern_slice['單價'].diff()
                std_change = pattern_slice['Change'].std()
                threshold = 3 * std_change 

                start_point = None
                if p_type == "🚀 急速拉升":
                    start_point = pattern_slice[pattern_slice['Change'] > threshold]
                elif p_type == "🩸 恐慌拋售":
                    start_point = pattern_slice[pattern_slice['Change'] < -threshold]
                
                if start_point is not None and not start_point.empty:
                    final_time = start_point.iloc[0]['時間']
                    y_pos = start_point.iloc[0]['單價']
            
        elif p_type in ARROW_PATTERNS and p_type not in {"🚀 急速拉升", "🩸 恐慌拋售", "🦀 區間盤整", "區間盤整"}:
            # 複雜型態 (A, B, C): 使用中點
            mid_idx = int((p_start_idx + p_end_idx) / 2)
            final_time = df.iloc[mid_idx]['時間']
            y_pos = df.iloc[mid_idx]['單價']
            
        else:
            # 區間盤整 (🦀): 🔴 使用起始點 (final_time=start_time, y_pos=start_price)
            # 這兩個變數在函數開始時已被初始化，無需額外計算
            pass 


        # 1. 繪製輔助線 (lines)
        if 'lines' in pattern:
            for line_params in pattern['lines']:
                ys = line_params if isinstance(line_params, list) else [start_price, end_price]
                if len(ys) == 2:
                    fig.add_trace(go.Scatter(
                        x=[start_time, end_time], y=ys, mode='lines', 
                        line=dict(color=p_color, width=2, dash='dot'),
                        showlegend=False, hoverinfo='skip'
                    ))
        
        # 2. 繪製區間背景色塊
        fig.add_shape(type="rect", x0=start_time, x1=end_time,
            y0=df['單價'].min() * 0.98, y1=df['單價'].min() * 1.01,
            line=dict(width=0), fillcolor=p_color, opacity=0.1, layer="below")


        # 3. 繪製標註 (所有 ARROW_PATTERNS 都有箭頭)
        stagger_level = i % 4
        arrow_len = 40 + (stagger_level * 25)
        
        fig.add_annotation(
            x=final_time, y=y_pos, 
            text=f"<b>{p_type}</b>",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5, arrowcolor=p_color,
            ay=-arrow_len, ax=0,
            bgcolor="rgba(30, 30, 30, 0.85)", bordercolor=p_color,
            font=dict(color=p_color, size=11, weight='bold'), borderpad=3
        )


# 9️⃣ 影響事件標註 (Events)
def add_event_markers(fig, df, events_data):
    """
    在圖表上標註價格突變、新高新低等事件。
    """
    if not events_data: 
        return

    for i, event in enumerate(events_data):
        idx = event['index']
        e_type = event['type']
        
        if idx >= len(df): continue
        
        cur_time = df.iloc[idx]['時間']
        cur_price = df.iloc[idx]['單價']
        
        e_color = "#FFFF00"
        e_symbol = "star"
        
        if '新高' in e_type:
            e_color = "#FF3D00"
            e_symbol = "triangle-up"
        elif '新低' in e_type:
            e_color = "#00B0FF"
            e_symbol = "triangle-down"
        elif '突變' in e_type:
            e_color = "#EA80FC"
            e_symbol = "diamond"

        fig.add_trace(go.Scatter(
            x=[cur_time], y=[cur_price],
            mode='markers',
            name=e_type,
            showlegend=False,
            marker=dict(color=e_color, size=8, symbol=e_symbol, line=dict(width=1, color='black')),
            hovertemplate=f'<b>{e_type}</b><br>價格: %{{y:,.0f}}<extra></extra>' 
        ))

        stagger_level = i % 3
        arrow_len = 30 + (stagger_level * 25)

        fig.add_annotation(
            x=cur_time, y=cur_price,
            text=e_type,
            showarrow=True, arrowhead=1, arrowcolor=e_color,
            ay=arrow_len, ax=0,
            font=dict(color="#FFFFFF", size=10),
            bgcolor="rgba(50, 50, 50, 0.7)", bordercolor=e_color, borderpad=2
        )