import pandas as pd
from analysis.trend import analyze_trend

def get_ai_forecast(df):
    """調用趨勢分析結果並返回。"""
    return analyze_trend(df)