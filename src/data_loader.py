import os
import pandas as pd
from .config import CFG

def _augment(df):
    df["RT_Basis"] = df["RT_Busbar"] - df["RT_Hub"]
    df["DA_Basis"] = df["DA_Busbar"] - df["DA_Hub"]
    df["hour"] = df.index.hour
    df["dow"] = df.index.dayofweek
    df["is_peak"] = df["dow"].isin(CFG.PEAK_DAYS) & df["hour"].isin(CFG.PEAK_HOURS)
    df["period"] = df["is_peak"].map({True:"Peak", False:"Off-Peak"})
    return df

def _read_asset_csv(path):
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"])
    df["datetime"] = df.apply(lambda r: r["Date"] + pd.to_timedelta(int(r["HE"])-1, unit="h"), axis=1)
    df = df.set_index("datetime").sort_index()
    df = df.rename(columns={"RT Busbar":"RT_Busbar","RT Hub":"RT_Hub","DA Busbar":"DA_Busbar","DA Hub":"DA_Hub"})
    _augment(df)
    return df

def load_assets():
    assets = {}
    for name, meta in CFG.ASSETS.items():
        market = meta["market"]
        csv = os.path.join(CFG.RAW_DIR, f"{market.lower()}_{name.lower()}.csv")
        if not os.path.exists(csv):
            raise FileNotFoundError(f"Missing {csv}. Run convert_to_csv.py first.")
        assets[name] = _read_asset_csv(csv)
    return assets

def load_forwards():
    fcsv = os.path.join(CFG.RAW_DIR, "forward_curves.csv")
    if not os.path.exists(fcsv):
        raise FileNotFoundError("Missing forward_curves.csv. Run convert_to_csv.py first.")
    fw = pd.read_csv(fcsv)
    fw["date"] = pd.to_datetime(fw["Month"])
    fw["year"] = fw["date"].dt.year
    fw["month"] = fw["date"].dt.month
    return fw
