import numpy as np
import pandas as pd
from .config import CFG
from .utils import safe_div

def _bootstrap_series(s: pd.Series, rng):
    if s is None or len(s)==0: return 0.0
    return float(s.iloc[rng.integers(0, len(s))])

def _regime_hub_draw(bkt: dict, p_high: float, is_rt: bool, rng):
    if is_rt:
        if rng.random() < p_high and len(bkt["rt_hub_high"])>0:
            return _bootstrap_series(bkt["rt_hub_high"], rng)
        if len(bkt["rt_hub_low"])>0:
            return _bootstrap_series(bkt["rt_hub_low"], rng)
        return _bootstrap_series(bkt["rt_hub"], rng)
    return _bootstrap_series(bkt["da_hub"], rng)

def _basis_draw_stressed(basis_series: pd.Series, hub_price: float, alpha: float, rng):
    if basis_series is None or len(basis_series)==0: return 0.0
    b = _bootstrap_series(basis_series, rng)
    csf = safe_div(abs(b), max(abs(hub_price), 1e-6))  # congestion stress factor
    return float(b * (1.0 + alpha * csf))

def simulate_merchant_price_per_mwh(
    buckets: dict,
    gen_forecast: pd.DataFrame,
    fw: pd.DataFrame,
    product: str,
    p_high: float,
    negative_rule: bool,
    seed: int,
    n_sims: int
):
    """
    product ∈ {'RT_HUB','RT_BUS','DA_HUB','DA_BUS'}
    Returns np.array of merchant $/MWh across sims.
    """
    rng = np.random.default_rng(seed)
    out = np.zeros(n_sims, dtype=float)

    for s in range(n_sims):
        tot_rev = 0.0
        tot_gen = 0.0
        for _, r in gen_forecast.iterrows():
            key_peak = (int(r["month"]), "Peak")
            key_off  = (int(r["month"]), "Off-Peak")
            fw_row = fw[(fw["year"]==r["year"])&(fw["month"]==r["month"])]
            fw_peak = float(fw_row["fw_peak"].iloc[0]) if not fw_row.empty else 0.0
            fw_off  = float(fw_row["fw_off"].iloc[0])  if not fw_row.empty else 0.0

            peak_mwh = max(rng.normal(r["peak_mwh"], r["std_mwh"]*r["peak_pct"]), 0.0)
            off_mwh  = max(rng.normal(r["off_mwh"],  r["std_mwh"]*r["off_pct"]),  0.0)

            for per, mwh, fw_price in [("Peak", peak_mwh, fw_peak), ("Off-Peak", off_mwh, fw_off)]:
                if mwh <= 0: continue
                bkt = buckets.get((int(r["month"]), per))
                if bkt is None: continue
                is_rt = product.startswith("RT")

                hub_draw = _regime_hub_draw(bkt, p_high, is_rt, rng)
                hub_mean = float(bkt["rt_hub"].mean()) if is_rt else float(bkt["da_hub"].mean())
                residual = hub_draw - hub_mean
                hub_sim = fw_price + residual

                if product.endswith("HUB"):
                    node_sim = hub_sim
                else:
                    basis_series = bkt["rt_basis"] if is_rt else bkt["da_basis"]
                    basis_sim = _basis_draw_stressed(basis_series, hub_sim, CFG.BASIS_STRESS_ALPHA, rng)
                    node_sim = hub_sim + basis_sim

                eff_mwh = mwh if not (negative_rule and node_sim < 0) else 0.0
                tot_rev += eff_mwh * node_sim
                tot_gen += eff_mwh

        out[s] = tot_rev / tot_gen if tot_gen > 0 else 0.0
    return out
