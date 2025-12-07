import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np # 用於計算趨勢線
import datetime

# 🔴 你的 Google Sheet CSV 連結
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtSvfsvYpDjQutAO9L4AV1Rq8XzZAQEAZcLZxl9JsSvxCo7X2JsaFTVdTAQwGNQRC2ySe5OPJaTzp9/pub?gid=915078159&single=true&output=csv"

st.set_page_config(
    page_title="托蘭交易所行情", 
    layout="wide", 
    page_icon="📈"
)

# --- 1. 資料讀取與清洗 ---
@st.cache_data(ttl=60)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
        if len(df.columns) >= 4:
            df = df.iloc[:, :4] 
            df.columns = ["時間", "物品", "屬性", "單價"]
            df = df.dropna(subset=["物品", "單價"])

            def parse_google_time(t_str):
                try:
                    t_str = str(t_str).strip()
                    if "下午" in t_str or "上午" in t_str:
                        is_pm = "下午" in t_str
                        clean_str = t_str.replace("下午", "").replace("上午", "").strip()
                        dt = pd.to_datetime(clean_str)
                        if is_pm and dt.hour != 12: dt += pd.Timedelta(hours=12)
                        elif not is_pm and dt.hour == 12: dt -= pd.Timedelta(hours=12)
                        return dt
                    else:
                        t_str = t_str.replace("/", "-")
                        return pd.to_datetime(t_str)
                except:
                    return pd.NaT

            df['時間'] = df['時間'].apply(parse_google_time)
            df = df.dropna(subset=["時間"])
            df['單價'] = pd.to_numeric(df['單價'], errors='coerce')
            df = df.dropna(subset=["單價"])
            
            # 自動分類
            def get_category(row):
                name = str(row['物品']).strip()
                attr = str(row['屬性']).strip() if pd.notna(row['屬性']) else ""
                check_str = name + attr
                if "武器" in check_str: return "⚔️ 武器王石"
                if "防具" in check_str: return "🛡️ 防具王石"
                if "追加" in check_str: return "🎩 追加王石"
                if "特殊" in check_str: return "💍 特殊王石"
                if "通用" in check_str: return "*️⃣ 通用王石"
                if "外觀" in check_str: return "👗 外觀"
                if "雙洞" in check_str or "單洞" in check_str or "不限洞" in check_str: return "⚔️ 裝備"
                return "📦 其他雜項"

            df['分類'] = df.apply(get_category, axis=1)
            df = df.sort_values("時間")
            return df, None
        else:
            return pd.DataFrame(), "欄位不足"
    except Exception as e:
        return pd.DataFrame(), str(e)

# --- 2. 網頁介面 ---
st.title("📈 Toram Online 市場價格追蹤 (TradingView 風格版)")

df, err = load_data()

if not df.empty:
    st.sidebar.header("🔍 搜尋設定")
    
    custom_order = ["⚔️ 武器王石", "🛡️ 防具王石", "🎩 追加王石", "💍 特殊王石", "*️⃣ 通用王石", "⚔️ 裝備", "👗 外觀", "📦 其他雜項"]
    existing_cats = df['分類'].unique().tolist()
    sorted_cats = [c for c in custom_order if c in existing_cats] + [c for c in existing_cats if c not in custom_order]
    
    cat_options = ["全部顯示"] + sorted_cats
    selected_cat = st.sidebar.radio("1️⃣ 選擇種類", cat_options)

    if selected_cat != "全部顯示":
        filtered_df = df[df['分類'] == selected_cat]
    else:
        filtered_df = df

    items = sorted(filtered_df['物品'].unique().tolist())
    
    if items:
        selected_item = st.sidebar.selectbox("2️⃣ 選擇物品", items)
        target_df = df[df['物品'] == selected_item].copy()

        if not target_df.empty:
            # 計算最新數據
            latest = target_df.iloc[-1]
            latest_price = latest['單價']
            
            delta_val = None
            if len(target_df) >= 2:
                prev_price = target_df.iloc[-2]['單價']
                diff = latest_price - prev_price
                if diff != 0: delta_val = f"{diff:,.0f}"

            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric(label=f"💰 {selected_item} 最新價格", value=f"${latest_price:,.0f}", delta=delta_val)

            # ==========================================
            # 🔥🔥🔥 TradingView 風格圖表繪製區 🔥🔥🔥
            # ==========================================
            fig = go.Figure()

            # 1. 主價格線 (亮綠色，帶漸層填充)
            fig.add_trace(go.Scatter(
                x=target_df['時間'], 
                y=target_df['單價'],
                mode='lines+markers',
                name='成交價',
                line=dict(color='#089981', width=2), # TradingView 漲勢綠
                marker=dict(size=6, color='#089981', line=dict(width=1, color='white')),
                fill='tozeroy',
                fillcolor='rgba(8, 153, 129, 0.1)', # 淡淡的綠色背景
                hovertemplate='<b>%{x|%Y-%m-%d %H:%M}</b><br>價格: $%{y:,.0f}<extra></extra>'
            ))

            # 2. 移動平均線 (MA3) - 黃色虛線
            if len(target_df) >= 3:
                target_df['MA_3'] = target_df['單價'].rolling(window=3).mean()
                fig.add_trace(go.Scatter(
                    x=target_df['時間'],
                    y=target_df['MA_3'],
                    mode='lines',
                    name='MA(3) 平均線',
                    line=dict(color='#F23645', width=1.5), # TradingView 跌勢紅
                    opacity=0.8,
                    hoverinfo='skip'
                ))

            # 3. 趨勢預測線 (線性回歸) - 藍色點線
            if len(target_df) >= 2:
                x_nums = pd.to_numeric(target_df['時間'])
                z = np.polyfit(x_nums, target_df['單價'], 1)
                p = np.poly1d(z)
                fig.add_trace(go.Scatter(
                    x=target_df['時間'],
                    y=p(x_nums),
                    mode='lines',
                    name='趨勢預測',
                    line=dict(color='#2962FF', width=1, dash='dot'), # TradingView 藍
                    opacity=0.7,
                    hoverinfo='skip'
                ))

            # 4. 平均價格基準線 (水平線)
            avg_price = target_df['單價'].mean()
            fig.add_hline(
                y=avg_price, 
                line_dash="dash", 
                line_color="gray", 
                opacity=0.5,
                annotation_text=f"均價: ${avg_price:,.0f}", 
                annotation_position="bottom left",
                annotation_font=dict(color="gray")
            )

            # 5. 最高/最低點標註
            if len(target_df) > 1:
                max_pt = target_df.loc[target_df['單價'].idxmax()]
                min_pt = target_df.loc[target_df['單價'].idxmin()]
                
                # 最高點
                fig.add_annotation(
                    x=max_pt['時間'], y=max_pt['單價'],
                    text=f"High: ${max_pt['單價']:,.0f}",
                    showarrow=True, arrowhead=1, yshift=10,
                    font=dict(color="#089981", size=10), arrowcolor="#089981"
                )
                # 最低點
                fig.add_annotation(
                    x=min_pt['時間'], y=min_pt['單價'],
                    text=f"Low: ${min_pt['單價']:,.0f}",
                    showarrow=True, arrowhead=1, ay=25,
                    font=dict(color="#F23645", size=10), arrowcolor="#F23645"
                )

            # --- Layout 設定 (TradingView 風格核心) ---
            fig.update_layout(
                title=dict(text=f"{selected_item} 市場走勢圖", font=dict(size=20, color="#d1d4dc")),
                height=550,
                template="plotly_dark",
                # 背景顏色設定
                paper_bgcolor="#131722", # TradingView 主背景色
                plot_bgcolor="#131722",
                
                # X軸設定 (時間)
                xaxis=dict(
                    type="date",
                    gridcolor="#363c4e", # 深灰網格
                    linecolor="#363c4e",
                    rangeslider=dict(visible=True, bgcolor="#131722"), # 下方滑動條
                    rangeselector=dict(
                        buttons=list([
                            dict(count=7, label="1W", step="day", stepmode="backward"),
                            dict(count=1, label="1M", step="month", stepmode="backward"),
                            dict(step="all", label="All")
                        ]),
                        bgcolor="#2a2e39", # 按鈕背景
                        font=dict(color="white")
                    )
                ),
                
                # Y軸設定 (將價格放在右側，符合看盤習慣)
                yaxis=dict(
                    title="單價 (Spina)",
                    tickformat=",",
                    side="right", # 🔥 關鍵：Y軸移到右邊
                    gridcolor="#363c4e",
                    zerolinecolor="#363c4e"
                ),
                
                # 滑鼠懸停模式 (十字準線)
                hovermode="x unified",
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", y=1.02, 
                    xanchor="right", x=1
                ),
                margin=dict(l=20, r=60, t=60, b=40)
            )

            st.plotly_chart(fig, use_container_width=True)

            # --- 詳細資料表格 ---
            with st.expander("📝 查看詳細交易紀錄", expanded=True):
                display_df = target_df.sort_values("時間", ascending=False).copy()
                display_df['時間'] = display_df['時間'].dt.strftime('%Y-%m-%d %H:%M')
                display_df['單價'] = display_df['單價'].apply(lambda x: f"${x:,.0f}")
                
                # 簡單計算漲跌幅 (與均價比)
                display_df['與均價差'] = target_df.sort_values("時間", ascending=False)['單價'] - avg_price
                display_df['狀態'] = display_df['與均價差'].apply(
                    lambda x: "🔴 高於均價" if x > 0 else "🟢 低於均價"
                )
                
                st.dataframe(
                    display_df[['時間', '物品', '屬性', '單價', '狀態']],
                    use_container_width=True,
                    hide_index=True
                )
        else:
            st.warning("此物品目前沒有數據。")
    else:
        st.info("此分類下暫無物品。")

else:
    if err:
        st.error(f"❌ 資料讀取錯誤：{err}")
    else:
        st.info("📭 資料庫目前是空的。")