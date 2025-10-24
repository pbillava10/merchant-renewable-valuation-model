import os
import numpy as np

def ensure_dirs(*paths):
    for p in paths:
        os.makedirs(p, exist_ok=True)

def month_hours_map():
    return {1:744,2:672,3:744,4:720,5:744,6:720,7:744,8:744,9:720,10:744,11:720,12:744}

def monthly_discount_rate(wacc_annual: float) -> float:
    return (1 + wacc_annual) ** (1/12) - 1

def percentile_from_p_level(p_level: int) -> float:
    return 100 - p_level  # P75 -> 25th percentile

def safe_div(a, b):
    return a / b if b else 0.0
