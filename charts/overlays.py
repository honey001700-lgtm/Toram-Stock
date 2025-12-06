import plotly.graph_objects as go

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
        
        fig.add_shape(type="rect", xref="x", yref="y",
            x0=df['時間'].min(), y0=min_s * 0.99,
            x1=df['時間'].max(), y1=min_s * 1.01,
            line=dict(width=0), fillcolor="rgba(0, 205, 205, 0.15)", layer="below")
        
        fig.add_shape(type="rect", xref="x", yref="y",
            x0=df['時間'].min(), y0=max_r * 0.99,
            x1=df['時間'].max(), y1=max_r * 1.01,
            line=dict(width=0), fillcolor="rgba(255, 69, 0, 0.15)", layer="below")

# ==========================================
# 3️⃣ AI 型態偵測 (Patterns)
# ==========================================
def add_pattern_traces(fig, df, patterns_data):
    """
    在圖表上繪製偵測到的型態，並自動解決標籤重疊問題。
    """
    if not patterns_data: 
        return

    colors = {
        "👤 頭肩頂 (看跌)": "#FF5252",
        "🧘 頭肩底 (看漲)": "#00E676",
        "Ⓜ️ 雙重頂 (M頭)": "#FF9100",
        "🇼 雙重底 (W底)": "#00B0FF",
        "📐 三角收斂": "#E040FB",
        "🛤️ 上升通道": "#2979FF",
        "📉 下降通道": "#FF1744",
        "🚀 急速拉升": "#F50057",
        "🩸 恐慌拋售": "#9E9E9E",
        "🦀 區間盤整": "#607D8B",
        "區間盤整": "#607D8B",
        "無明顯型態": "#B0BEC5"
    }

    for i, pattern in enumerate(patterns_data):
        p_type = pattern['type']
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

        if 'lines' in pattern:
            for line_params in pattern['lines']:
                ys = line_params if isinstance(line_params, list) else [start_price, end_price]
                if len(ys) == 2:
                    fig.add_trace(go.Scatter(
                        x=[start_time, end_time], y=ys, mode='lines', 
                        line=dict(color=p_color, width=2, dash='dot'),
                        showlegend=False, hoverinfo='skip'
                    ))
        else:
            fig.add_shape(type="rect", x0=start_time, x1=end_time,
                y0=min(start_price, end_price) * 0.995, y1=max(start_price, end_price) * 1.005,
                line=dict(width=0), fillcolor=p_color, opacity=0.1, layer="below")

        mid_idx = int((p_start_idx + p_end_idx) / 2)
        mid_time = df.iloc[mid_idx]['時間']
        mid_price = df.iloc[mid_idx]['單價']

        stagger_level = i % 4
        arrow_len = 40 + (stagger_level * 25)

        fig.add_annotation(
            x=mid_time, y=mid_price,
            text=f"<b>{p_type}</b>",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=1.5, arrowcolor=p_color,
            ay=-arrow_len, ax=0,
            bgcolor="rgba(30, 30, 30, 0.85)", bordercolor=p_color,
            font=dict(color=p_color, size=11, weight='bold'), borderpad=3
        )

# ==========================================
# 9️⃣ 影響事件標註 (Events) - 已修正 f-string
# ==========================================
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

        # 🔴 修正重點：使用 {{ }} 來跳過 f-string 對 y 的變數檢查
        fig.add_trace(go.Scatter(
            x=[cur_time], y=[cur_price],
            mode='markers',
            name=e_type,
            showlegend=False,
            marker=dict(color=e_color, size=8, symbol=e_symbol, line=dict(width=1, color='black')),
            # 這裡改成了 %{{y:,.0f}}，這樣 Python 會輸出 %{y:,.0f} 給 Plotly
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