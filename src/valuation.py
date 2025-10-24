import numpy as np
import pandas as pd
from .config import CFG
from .utils import percentile_from_p_level, monthly_discount_rate, safe_div

def p_level_price(sim_prices: np.ndarray, p_level: int):
    return float(np.percentile(sim_prices, percentile_from_p_level(p_level)))

def compute_components(asset: str, product: str, gen_fc: pd.DataFrame, fw: pd.DataFrame,
                       hist_basis_means: dict, p75_price: float, neg_p75_price: float = None):
    # gen-weighted forward hub
    gw_hub = 0.0
    total_gen = gen_fc["expected_mwh"].sum()
    for _, r in gen_fc.iterrows():
        row_fw = fw[(fw["year"]==r["year"])&(fw["month"]==r["month"])]
        if row_fw.empty: continue
        gw_hub += (r["peak_mwh"]*row_fw["fw_peak"].iloc[0] + r["off_mwh"]*row_fw["fw_off"].iloc[0])
    hub_component = safe_div(gw_hub, total_gen)

    # basis component (0 for hub products)
    if product.endswith("HUB"):
        basis_comp = 0.0
    else:
        basis_comp = 0.0
        for _, r in gen_fc.iterrows():
            b_peak = hist_basis_means.get(((int(r["month"]), "Peak"), product[:2]), 0.0)   # 'RT'/'DA'
            b_off  = hist_basis_means.get(((int(r["month"]), "Off-Peak"), product[:2]), 0.0)
            basis_comp += r["peak_mwh"]*b_peak + r["off_mwh"]*b_off
        basis_comp = safe_div(basis_comp, total_gen)

    base = hub_component + basis_comp
    risk_adj = p75_price - base
    neg_adj = (neg_p75_price - p75_price) if neg_p75_price is not None else 0.0
    return hub_component, basis_comp, risk_adj, neg_adj, p75_price

def dcf_monthly(mean_price: float, gen_fc: pd.DataFrame, wacc_annual: float):
    r_m = (1 + wacc_annual) ** (1/12) - 1
    pv = 0.0
    for i, rr in enumerate(gen_fc.itertuples(index=False), start=1):
        cf = mean_price * getattr(rr, "expected_mwh")
        pv += cf / ((1 + r_m) ** i)
    return float(pv)

def summarize_npvs(merchant_p50_price: float, fixed_p75_price: float, gen_fc: pd.DataFrame):
    m_npv = dcf_monthly(merchant_p50_price, gen_fc, CFG.WACC_ANNUAL)
    f_npv = dcf_monthly(fixed_p75_price, gen_fc, CFG.WACC_ANNUAL)
    delta = safe_div(f_npv - m_npv, m_npv) * 100.0 if m_npv else 0.0
    return m_npv, f_npv, delta
