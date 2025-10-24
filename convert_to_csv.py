

import os
import pandas as pd
from pathlib import Path

INPUT_XLSX = "data/raw/HackathonDataset.xlsx"
OUT_DIR = Path("data/raw")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SHEET_TO_ASSET_CSV = {
    "ERCOT": "ercot_valentino.csv",
    "MISO": "miso_mantero.csv",
    "CAISO": "caiso_howling_gale.csv",
}

def _money_to_float(x):
    if pd.isna(x): return pd.NA
    s = str(x).strip()
    if s == "": return pd.NA
    neg = s.startswith("(") and s.endswith(")")
    s = s.replace("(", "").replace(")", "").replace("$", "").replace(",", "")
    try:
        v = float(s)
        return -v if neg else v
    except Exception:
        return pd.NA

def extract_sheet(sheet_name: str):
    raw = pd.read_excel(INPUT_XLSX, sheet_name=sheet_name, header=None)

    # --- Historical: detect header row with "Date" and "HE"
    hist_header = None
    for r in range(min(60, len(raw))):
        vals = raw.iloc[r].astype(str).str.strip().tolist()
        if "Date" in vals and ("HE" in vals or "Hour Ending" in vals):
            hist_header = r
            break
    if hist_header is None:
        raise ValueError(f"Historical header not found in {sheet_name}")

    cols = raw.iloc[hist_header].astype(str).str.strip().tolist()
    hist = raw.iloc[hist_header+1:].copy()
    hist.columns = cols

    # normalize names and keep A–H equivalents
    rename = {
        "RT Busbar":"RT_Busbar", "RT Hub":"RT_Hub",
        "DA Busbar":"DA_Busbar", "DA Hub":"DA_Hub",
        "Busbar":"RT_Busbar", "Hub":"RT_Hub"
    }
    hist = hist.rename(columns=rename)
    keep = [c for c in ["Date","HE","P/OP","Gen","RT_Busbar","RT_Hub","DA_Busbar","DA_Hub"] if c in hist.columns]
    hist = hist[keep].dropna(subset=["Date","HE"])

    # type parsing
    hist["Date"] = pd.to_datetime(hist["Date"])
    hist["HE"] = pd.to_numeric(hist["HE"], errors="coerce").astype("Int64")
    for c in ["Gen","RT_Busbar","RT_Hub","DA_Busbar","DA_Hub"]:
        if c in hist.columns:
            hist[c] = hist[c].map(_money_to_float)

    # --- Forwards: find "Peak" and "Off Peak" header cells (K–M block)
    fwd_header = None
    max_r, max_c = min(80, raw.shape[0]), min(80, raw.shape[1])
    for r in range(max_r):
        for c in range(max_c-1):
            v1 = str(raw.iat[r, c]).strip()
            v2 = str(raw.iat[r, c+1]).strip()
            if v1 == "Peak" and v2 in ("Off Peak","Off-Peak","Off_Peak"):
                fwd_header = (r, c)
                break
        if fwd_header: break
    if fwd_header is None:
        raise ValueError(f"Forward headers (Peak/Off Peak) not found in {sheet_name}")

    r0, c0 = fwd_header
    month_col, peak_col, off_col = c0-1, c0, c0+1
    fwd = raw.iloc[r0+1:, [month_col, peak_col, off_col]].copy()
    fwd.columns = ["Month","Peak","Off_Peak"]
    fwd = fwd[fwd["Month"].notna()]
    fwd["Month"] = pd.to_datetime(fwd["Month"], errors="coerce", infer_datetime_format=True)
    fwd = fwd[fwd["Month"].notna()].copy()
    for c in ["Peak","Off_Peak"]:
        fwd[c] = fwd[c].map(_money_to_float)
    fwd["Market"] = sheet_name.upper()
    fwd = fwd[["Market","Month","Peak","Off_Peak"]].reset_index(drop=True)
    return hist.reset_index(drop=True), fwd

def main():
    if not os.path.exists(INPUT_XLSX):
        raise FileNotFoundError(f"Missing {INPUT_XLSX}")

    xls = pd.ExcelFile(INPUT_XLSX)
    print("Sheets found:", xls.sheet_names)

    fw_all = []
    for sheet, outname in SHEET_TO_ASSET_CSV.items():
        if sheet not in xls.sheet_names:
            print(f"⚠️ Missing sheet {sheet}; skipping")
            continue
        hist, fwd = extract_sheet(sheet)
        hist.to_csv(OUT_DIR / outname, index=False)
        print(f"✅ Wrote {OUT_DIR/outname} ({len(hist):,} rows)")
        fw_all.append(fwd)

    if fw_all:
        fwd_all = pd.concat(fw_all, ignore_index=True)
        outfw = OUT_DIR / "forward_curves.csv"
        fwd_all.to_csv(outfw, index=False)
        print(f"✅ Wrote {outfw} ({len(fwd_all):,} rows)")

if __name__ == "__main__":
    main()
