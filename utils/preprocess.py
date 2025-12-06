# utils/preprocess.py
import pandas as pd
import numpy as np
import streamlit as st # <-- 🔴 新增這行

@st.cache_data(ttl=60 * 5) # 緩存 5 分鐘
def load_data(SHEET_URL):
    """讀取資料並進行基礎清洗與分類。"""
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
            
            # 自動分類 (與原版相同)
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
                if any(x in check_str for x in ["雙洞", "單洞", "不限洞", "空洞"]): return "⚔️ 裝備"
                return "📦 其他雜項"

            df['分類'] = df.apply(get_category, axis=1)
            df = df.sort_values("時間")

            # 6️⃣ VWAP (成交量加權平均) 的體積估計 (每筆交易量為 1)
            df['Volume'] = 1 
            
            return df, None
        else:
            return pd.DataFrame(), "欄位不足"
    except Exception as e:
        return pd.DataFrame(), str(e)
        
def filter_and_prepare_data(df, item_name, start_date=None, end_date=None):
    """依物品名稱和日期過濾資料。"""
    target_df = df[df['物品'] == item_name].copy()
    if start_date and end_date:
        target_df = target_df[(target_df['時間'] >= start_date) & (target_df['時間'] <= end_date)]
    return target_df.reset_index(drop=True)