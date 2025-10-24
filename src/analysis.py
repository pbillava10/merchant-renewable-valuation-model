import numpy as np
import pandas as pd
from .config import CFG

def build_hist_buckets(df: pd.DataFrame):
    """
    Bucket history by (month, period). Tag regimes (HIGH/LOW) using RT hub rolling std.
    Returns (buckets, p_high)
    """
    df = df.copy()
    df["month"] = df.index.month
    df["rt_hub_rollstd"] = df["RT_Hub"].rolling(CFG.ROLLING_STD_HOURS, min_periods=24).std()
    thr = df["rt_hub_rollstd"].median(skipna=True)
    df["regime"] = np.where(df["rt_hub_rollstd"] > thr, "HIGH", "LOW")

    buckets = {}
    for m in range(1,13):
        for per in ["Peak","Off-Peak"]:
            b = df[(df["month"]==m)&(df["period"]==per)]
            if b.empty: continue
            buckets[(m, per)] = {
                "gen": b["Gen"].dropna(),
                "rt_hub": b["RT_Hub"].dropna(),
                "da_hub": b["DA_Hub"].dropna(),
                "rt_basis": b["RT_Basis"].dropna(),
                "da_basis": b["DA_Basis"].dropna(),
                "rt_hub_high": b[b["regime"]=="HIGH"]["RT_Hub"].dropna(),
                "rt_hub_low":  b[b["regime"]=="LOW"]["RT_Hub"].dropna(),
            }
    p_high = float((df["regime"]=="HIGH").mean())
    return buckets, p_high
