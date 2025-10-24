import argparse
import os
import numpy as np
import pandas as pd

from src.config import CFG
from src.utils import ensure_dirs
from src.data_loader import load_assets, load_forwards
from src.analysis import build_hist_buckets
from src.forecasting import forecast_generation, forecast_hub_forwards
from src.monte_carlo import simulate_merchant_price_per_mwh
from src.valuation import p_level_price, compute_components, summarize_npvs
from src.visualization import plot_distribution

ASSETS   = list(CFG.ASSETS.keys())
PRODUCTS = list(CFG.PRODUCTS)

def main(p_level: int, sims: int, neg_rule: bool):
    ensure_dirs(CFG.PROC_DIR, CFG.OUT_RESULTS, CFG.OUT_FIGS)

    assets = load_assets()
    forwards = load_forwards()

    price_rows, npv_rows, gen_fc_all = [], [], []

    for asset in ASSETS:
        market = CFG.ASSETS[asset]["market"]
        df = assets[asset]

        buckets, p_high = build_hist_buckets(df)
        gen_fc = forecast_generation(df)
        fw_mkt = forecast_hub_forwards(forwards, market)

        # basis means for component breakdown
        hist_basis_means = {}
        for (month, period), b in buckets.items():
            hist_basis_means[((month, period), "RT")] = float(b["rt_basis"].mean()) if len(b["rt_basis"])>0 else 0.0
            hist_basis_means[((month, period), "DA")] = float(b["da_basis"].mean()) if len(b["da_basis"])>0 else 0.0

        sim_p50_prices = {}

        for product in PRODUCTS:
            sims_prices = simulate_merchant_price_per_mwh(
                buckets=buckets, gen_forecast=gen_fc, fw=fw_mkt,
                product=product, p_high=p_high,
                negative_rule=False, seed=CFG.REAL_RANDOM_SEED if hasattr(CFG, "REAL_RANDOM_SEED") else CFG.RANDOM_SEED,
                n_sims=sims
            )
            p75_price = p_level_price(sims_prices, p_level=p_level)

            neg_p75_price = None
            if neg_rule:
                sims_prices_neg = simulate_merchant_price_per_mwh(
                    buckets=buckets, gen_forecast=gen_fc, fw=fw_mkt,
                    product=product, p_high=p_high,
                    negative_rule=True, seed=CFG.RANDOM_SEED, n_sims=sims
                )
                neg_p75_price = p_level_price(sims_prices_neg, p_level=p_level)

            hub_comp, basis_comp, risk_adj, neg_adj, p75_out = compute_components(
                asset=asset, product=product, gen_fc=gen_fc, fw=fw_mkt,
                hist_basis_means=hist_basis_means, p75_price=p75_price, neg_p75_price=neg_p75_price
            )

            price_rows.append({
                "asset": asset, "market": market, "product": product,
                "hub_component": round(hub_comp, 2),
                "basis_component": round(basis_comp, 2),
                "risk_adj": round(risk_adj, 2),
                "neg_adj": round(neg_adj, 2),
                "p75_price": round(p75_out, 2)
            })

            plot_distribution(
                sim_prices=sims_prices, p75=p75_price,
                out_path=os.path.join(CFG.OUT_FIGS, f"{asset}_{product}_dist.png"),
                title=f"{asset} {product} Distribution (P75={p75_price:.2f})"
            )

            sim_p50_prices[product] = float(np.percentile(sims_prices, 50))

        # DCF (primary compare RT_BUS merchant P50 vs fixed P75)
        m_p50 = sim_p50_prices.get("RT_BUS", 0.0)
        f_p75 = [r for r in price_rows if r["asset"]==asset and r["product"]=="RT_BUS"][-1]["p75_price"]
        m_npv, f_npv, delta = summarize_npvs(m_p50, f_p75, gen_fc)
        npv_rows.append({
            "asset": asset, "market": market,
            "merchant_p50_price": round(m_p50,2),
            "fixed_p75_price": round(f_p75,2),
            "merchant_p50_npv": round(m_npv,2),
            "fixed_p75_npv": round(f_npv,2),
            "delta_pct": round(delta,2)
        })

        gtmp = gen_fc.copy()
        gtmp["asset"] = asset; gtmp["market"] = market
        gen_fc_all.append(gtmp)

    # outputs
    prices_df = pd.DataFrame(price_rows).sort_values(["asset","product"])
    prices_df.to_csv(os.path.join(CFG.OUT_RESULTS, "prices_summary.csv"), index=False)

    genout = pd.concat(gen_fc_all, ignore_index=True)
    genout[["year","month","asset","market","expected_mwh","peak_mwh","off_mwh","peak_pct","off_pct"]].to_csv(
        os.path.join(CFG.OUT_RESULTS, "generation_forecast.csv"), index=False
    )

    npvs = pd.DataFrame(npv_rows)
    npvs.to_csv(os.path.join(CFG.OUT_RESULTS, "npv_summary.csv"), index=False)

    print("\n=== DONE ===")
    print(f"Wrote: {CFG.OUT_RESULTS}prices_summary.csv")
    print(f"Wrote: {CFG.OUT_RESULTS}generation_forecast.csv")
    print(f"Wrote: {CFG.OUT_RESULTS}npv_summary.csv")
    print(f"Figures in: {CFG.OUT_FIGS}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--p", type=int, default=CFG.P_LEVEL, help="P-level (e.g., 75 → 25th percentile)")
    ap.add_argument("--sims", type=int, default=CFG.N_SIMS, help="Monte Carlo iterations")
    ap.add_argument("--neg-rule", action="store_true", help="Zero output when node price < 0")
    args = ap.parse_args()
    main(p_level=args.p, sims=args.sims, neg_rule=args.neg_rule)
