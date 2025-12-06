# analysis/forecast.py
import pandas as pd
from analysis.trend import analyze_trend

# AI 預測（此處功能已在 trend.py 中簡化完成，但保留檔案結構）
def get_ai_forecast(df):
    """調用趨勢分析結果並返回。"""
    return analyze_trend(df)