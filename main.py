import streamlit as st
import pandas as pd
import numpy as np
import datetime
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from scipy.stats import linregress

# 導入模組
from utils.preprocess import load_data, filter_and_prepare_data
from utils.theme import TV_THEME
from charts.base_chart import create_flagship_chart
from analysis.trend import analyze_trend
from analysis.support_resistance import find_support_resistance
from analysis.patterns import detect_patterns, detect_events
from utils.regression import calculate_r_squared # 🔴 新增導入

# 🔴 你的 Google Sheet CSV 連結
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQtSvfsvYpDjQutAO9L4AV1Rq8XzZAQEAZcLZxl9JsSvxCo7X2JsaFTVdTAQwGNQRC2ySe5OPJaTzp9/pub?gid=915078159&single=true&output=csv"

st.set_page_config(
    page_title="📈 托蘭交易所旗艦版", 
    layout="wide", 
    page_icon="💎"
)

# --- 1. 資料讀取 ---
df_full, err = load_data(SHEET_URL)

st.title("💎 Toram Online 市場價格追蹤 (TradingView + AI 旗艦版)")
st.caption(f"數據更新時間: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (每 5 分鐘自動更新)")


if df_full.empty:
    if err:
        st.error(f"❌ 資料讀取錯誤：{err}")
    else:
        st.info("📭 資料庫目前是空的。")
    st.stop()


# --- 2. 側邊欄設定 (主控制台) ---
st.sidebar.header("🔍 交易控制台")

# 物品選擇
custom_order = ["⚔️ 武器王石", "🛡️ 防具王石", "🎩 追加王石", "💍 特殊王石", "*️⃣ 通用王石", "⚔️ 裝備", "👗 外觀", "📦 其他雜項"]
existing_cats = df_full['分類'].unique().tolist()
sorted_cats = [c for c in custom_order if c in existing_cats] + [c for c in existing_cats if c not in custom_order]
selected_cat = st.sidebar.radio("1️⃣ 選擇種類", sorted_cats, index=0 if sorted_cats else None)

filtered_by_cat = df_full[df_full['分類'] == selected_cat]
items = sorted(filtered_by_cat['物品'].unique().tolist())
selected_item = st.sidebar.selectbox("2️⃣ 選擇物品", items)

# 1️⃣1️⃣ 日期範圍選擇 (快速切換模式)
st.sidebar.subheader("📅 數據範圍選擇")
date_mode = st.sidebar.radio(
    "快速範圍", 
    ["全部", "90 日圖", "30 日圖", "7 日圖"],
    index=1,
    horizontal=True
)

end_date = df_full['時間'].max()
start_date = df_full['時間'].min()

if date_mode == "90 日圖":
    start_date = end_date - pd.Timedelta(days=90)
elif date_mode == "30 日圖":
    start_date = end_date - pd.Timedelta(days=30)
elif date_mode == "7 日圖":
    start_date = end_date - pd.Timedelta(days=7)

# --- 3. 指標與 AI 開關 (4️⃣, 5️⃣, 6️⃣, 7️⃣, 2️⃣, 3️⃣, 9️⃣) ---
st.sidebar.subheader("⚙️ 指標與 AI 設定")
indicator_config = {
    'AI_Overlay': st.sidebar.checkbox("AI 覆蓋層 (S/R, 型態, 事件)", value=True),
    'MA5': st.sidebar.checkbox("MA5 (5日均線)", value=False),
    'MA20': st.sidebar.checkbox("MA20 (20日均線)", value=True),
    'MA60': st.sidebar.checkbox("MA60 (60日均線)", value=False),
    'EMA': st.sidebar.checkbox("EMA (指數均線)", value=False),
    'BB': st.sidebar.checkbox("布林通道 (Bollinger Bands)", value=True),
    'VWAP': st.sidebar.checkbox("VWAP (加權均價)", value=False),
    'Regression': st.sidebar.checkbox("線性趨勢回歸線", value=True),
}


if selected_item:
    target_df = filter_and_prepare_data(df_full, selected_item, start_date, end_date)
    
    if not target_df.empty:
        # --- 4. 數據總覽 (Metric) ---
        col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
        latest_price = target_df.iloc[-1]['單價']
        prev_price = target_df.iloc[-2]['單價'] if len(target_df) >= 2 else latest_price
        
        with col_m1: st.metric(label=f"💰 最新價格", value=f"${latest_price:,.0f}", delta=f"{latest_price - prev_price:,.0f}")
        with col_m2: st.metric(label="⬆️ 最高價", value=f"${target_df['單價'].max():,.0f}")
        with col_m3: st.metric(label="⬇️ 最低價", value=f"${target_df['單價'].min():,.0f}")
        with col_m4: st.metric(label="⚖️ 平均價", value=f"${target_df['單價'].mean():,.0f}")
        with col_m5: st.metric(label="📊 數據筆數", value=f"{len(target_df):,}")

        # --- 5. AI 分析計算 (1️⃣, 2️⃣, 3️⃣) ---
        # 🔴 在 AI 報告前先計算 R²
        from utils.regression import calculate_r_squared 
        r_squared_global, _ = calculate_r_squared(target_df)
        
        # 1️⃣ AI 趨勢分析
        trend_report = analyze_trend(target_df)
        trend_report['R_squared'] = r_squared_global # 🔴 將計算結果賦值給 AI 報告

        # 2️⃣ AI S/R 偵測
        sr_report = find_support_resistance(target_df)
        
        # 3️⃣ AI 型態偵測
        pattern_report = detect_patterns(target_df)
        
        # 9️⃣ AI 事件偵測
        event_report = detect_events(target_df)
        
        # 組合分析數據
        analysis_data = {
            'trend_analysis': trend_report,
            'sr_analysis': sr_report,
            'pattern_analysis': pattern_report,
            'event_analysis': event_report
        }

        st.subheader("🤖 AI 智能分析報告")
        
        # 提取 R_squared，並進行安全格式化
        r_squared_value = trend_report['R_squared'] 
        r_squared_display = f"{r_squared_value:.2f}" if isinstance(r_squared_value, (float, int)) else 'N/A'
        
        # --- 6. AI 分析面板顯示 (使用 st.metric 和 st.expander) ---
        
        # 🔴 AI 摘要 Metric
        col_a1, col_a2, col_a3, col_a4 = st.columns(4)
        
        with col_a1: 
            st.metric(
                label="趨勢方向", 
                value=trend_report['趨勢方向'], 
                delta=f"強度: {trend_report['多空強度']}/100"
            )
        with col_a2: 
            st.metric(
                label="反轉風險", 
                value=trend_report['反轉風險提示'], 
                delta=f"信心值: {trend_report['AI統計信心值']}/100"
            )
        with col_a3: 
            st.metric(
                label="短期預測價", 
                value=trend_report['未來短期預測價格']
            )
        with col_a4:
            patterns = ", ".join([p['type'] for p in pattern_report]) if pattern_report else "無型態"
            resistance = ', '.join([f'${r:,}' for r in sr_report['resistance']])
            st.metric(
                label="偵測型態 / R²", 
                value=patterns, 
                delta=f"R²: {r_squared_display}"
            )

        # 🔴 詳細 AI 參數與建議
        with st.expander("🛠️ 詳細 AI 參數與建議", expanded=False):
            st.markdown(f"""
            - **當前趨勢方向**: **{trend_report['趨勢方向']}**
            - **多空強度 (0-100)**: **{trend_report['多空強度']}**
            - **AI 統計信心值 (0-100)**: **{trend_report['AI統計信心值']}**
            - **回歸線 R² (趨勢可信度)**: **{r_squared_display}**
            ---
            - **主要阻力線 (R)**: `{resistance}`
            - **主要支撐線 (S)**: `{', '.join([f'${s:,}' for s in sr_report['support']])}`
            - **預測價格 (短期 7 點)**: **{trend_report['未來短期預測價格']}**
            - **反轉風險提示**: **{trend_report['反轉風險提示']}**
            - **偵測型態**: **{patterns}**
            """)

        # --- 7. 圖表繪製 (8️⃣) ---
        st.subheader(f"📈 {selected_item} 旗艦圖表")
        fig = create_flagship_chart(target_df, selected_item, indicator_config, analysis_data) 
        st.plotly_chart(fig, use_container_width=True)
        
        # --- 8. 區間選取分析器 (1️⃣0️⃣) ---
        st.markdown("---")
        st.subheader("🎯 互動區間分析器")
        st.info("拖曳上方的 Plotly 圖表中的 **Range Slider** 選擇範圍，查看該區間的統計數據。")
        
        # 獲取 Range Slider 選擇的範圍
        # 由於 Streamlit 的 st.plotly_chart 不直接支持 Range Slider 的事件回傳，
        # 我們使用一個簡易的時間範圍選擇來模擬互動分析。
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            analysis_start = st.date_input("分析起始日期", value=start_date.date(), min_value=start_date.date(), max_value=end_date.date())
        with col_r2:
            analysis_end = st.date_input("分析結束日期", value=end_date.date(), min_value=analysis_start, max_value=end_date.date())
            
        analysis_df = filter_and_prepare_data(df_full, selected_item, pd.to_datetime(analysis_start), pd.to_datetime(analysis_end) + pd.Timedelta(days=1))
        
        if not analysis_df.empty:
            
            # 計算區間統計
            range_max = analysis_df['單價'].max()
            range_min = analysis_df['單價'].min()
            range_avg = analysis_df['單價'].mean()
            range_start_price = analysis_df.iloc[0]['單價']
            range_end_price = analysis_df.iloc[-1]['單價']
            range_change = range_end_price - range_start_price
            range_change_pct = (range_change / range_start_price) * 100
            
            # 波動率 (標準差/平均價)
            volatility = (analysis_df['單價'].std() / range_avg) * 100 if range_avg != 0 else 0
            
            col_rs1, col_rs2, col_rs3, col_rs4, col_rs5 = st.columns(5)
            with col_rs1: st.metric("區間最高價", f"${range_max:,.0f}")
            with col_rs2: st.metric("區間最低價", f"${range_min:,.0f}")
            with col_rs3: st.metric("區間平均價", f"${range_avg:,.0f}")
            with col_rs4: st.metric("升跌幅", f"${range_change:,.0f}", delta=f"{range_change_pct:.2f}%")
            with col_rs5: st.metric("波動率 (%)", f"{volatility:.2f}%")
            
        else:
            st.warning("所選範圍內無數據。")
            
    else:
        st.info("此物品在所選時間範圍內沒有數據。")
