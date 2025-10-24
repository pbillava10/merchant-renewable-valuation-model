import pandas as pd
from .config import CFG
from .utils import month_hours_map

def forecast_generation(hdf: pd.DataFrame):
    """Monthly expected gen and peak/off shares from history."""
    hdf = hdf.copy()
    hdf["month"] = hdf.index.month
    hours_map = month_hours_map()

    hourly_mean = hdf.groupby("month")["Gen"].mean()
    hourly_std  = hdf.groupby("month")["Gen"].std().fillna(0)

    ptab = hdf.groupby(["month","period"])["Gen"].sum().unstack(fill_value=0)
    ptab["total"] = ptab.sum(axis=1)
    ptab["peak_pct"] = ptab.get("Peak",0) / ptab["total"].replace(0,1)
    ptab["off_pct"]  = ptab.get("Off-Peak",0) / ptab["total"].replace(0,1)

    rows = []
    for y in range(CFG.FORECAST_START_YEAR, CFG.FORECAST_START_YEAR+CFG.FORECAST_YEARS):
        for m in range(1,13):
            hm = hours_map[m]
            exp_mwh = float(hourly_mean.get(m,0.0) * hm)
            std_mwh = float(hourly_std.get(m,0.0) * (hm**0.5))
            peak_pct = float(ptab.loc[m,"peak_pct"]) if m in ptab.index else 0.5
            off_pct  = float(ptab.loc[m,"off_pct"])  if m in ptab.index else 0.5
            rows.append({
                "year":y,"month":m,
                "expected_mwh":max(exp_mwh,0.0),
                "std_mwh":max(std_mwh,0.0),
                "peak_mwh":max(exp_mwh*peak_pct,0.0),
                "off_mwh":max(exp_mwh*off_pct,0.0),
                "peak_pct":peak_pct,"off_pct":off_pct
            })
    return pd.DataFrame(rows)

def forecast_hub_forwards(fw_df: pd.DataFrame, market: str):
    """Return monthly hub forward peak/off for forecast window."""
    df = fw_df[fw_df["Market"].str.upper()==market.upper()].copy()
    df["date"] = pd.to_datetime(df["Month"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df = df[(df["year"]>=CFG.FORECAST_START_YEAR)&(df["year"]<CFG.FORECAST_START_YEAR+CFG.FORECAST_YEARS)]
    return df[["year","month","Peak","Off_Peak"]].rename(columns={"Peak":"fw_peak","Off_Peak":"fw_off"})
