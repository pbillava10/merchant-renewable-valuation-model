
# Merchant Renewable Valuation Model

A reproducible Python project for valuing merchant renewable assets (wind/solar) over a 5‑year term using:
- Historical hourly prices and generation (node vs. hub)
- Monthly forward hub curves (Peak/Off‑Peak)
- Gen‑weighted basis from history
- Monte Carlo simulation of merchant revenues
- P‑level risk‑adjusted fixed prices (default **P75**)
- Discounted cash flow (monthly WACC) summaries

This repository is structured for clear data prep, forecasting, simulation, valuation, and reporting—matching typical internal “company‑standard” readme expectations (purpose, setup, run, outputs, methods, and assumptions).

---

## Quick Start

```bash
# 1) Clone & enter
git clone <this-repo-url>
cd AVANGRID

# 2) Create virtual environment (Python 3.10+ recommended)
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Place the Excel into data/raw
#    Required: data/raw/HackathonDataset.xlsx

# 5) Convert the Excel tabs to normalized CSVs
python convert_to_csv.py

# 6) Run the valuation (default P75, 3000 sims)
python main.py --p 75 --sims 3000

# Optional flags
#   --neg-rule   Apply a conservative rule to zero gen-weighted price when node price < 0
python main.py --p 75 --sims 3000 --neg-rule
```

Outputs are written to `outputs/results/` (CSVs) and `outputs/figures/` (PNGs).

---

## What This Project Produces

### CSVs (under `outputs/results/`)
- `prices_summary.csv` — For each **asset × product (RT/DA × HUB/BUS)**, reports:
  - Gen‑weighted **hub component**, **basis component**, and **risk adjustment** to reach the **P‑level price**
  - If `--neg-rule` is used, includes the incremental negative‑price adjustment
- `generation_forecast.csv` — Year‑month expected gen (MWh), peak/off splits, and monthly standard deviation proxies
- `npv_summary.csv` — DCF by asset/product: monthly discounted values aggregated to totals (WACC from config)

### Figures (under `outputs/figures/`)
- Distribution histograms of simulated **merchant $/MWh** with the **P‑level** marker per asset/product.

> The repo already contains example figures for **Howling_Gale**, **Mantero**, and **Valentino** (DA/RT × HUB/BUS).

---

## Repository Layout

```
AVANGRID/
├─ convert_to_csv.py                 # Normalize Excel → CSV per market/asset
├─ main.py                           # Orchestration: loads data, simulates, prices, writes reports/plots
├─ requirements.txt
├─ data/
│  └─ raw/
│     ├─ HackathonDataset.xlsx       # (you provide) source workbook
│     ├─ caiso_howling_gale.csv     # created by convert_to_csv.py
│     ├─ ercot_valentino.csv        # created by convert_to_csv.py
│     └─ miso_mantero.csv           # created by convert_to_csv.py
├─ outputs/
│  ├─ results/                       # CSV outputs (created at runtime)
│  └─ figures/                       # PNG figures (created at runtime)
└─ src/
   ├─ analysis.py                    # Historical bucketing & volatility regime tagging
   ├─ config.py                      # Project configuration (assets, products, WACC, P-level defaults, paths)
   ├─ data_loader.py                 # Load & augment CSVs; add peak/off tags, basis, etc.
   ├─ forecasting.py                 # Monthly gen & hub forward expansion across forecast window
   ├─ monte_carlo.py                 # Merchant price $/MWh simulation by month/period
   ├─ valuation.py                   # P-level price, component breakdown, NPV summary
   └─ visualization.py               # Histogram plots of simulated merchant prices
```

---

## Assets & Products

Defined in `src/config.py`:

- **Assets** (example defaults)
  - `Valentino` (ERCOT, Wind)
  - `Mantero`   (MISO,  Wind)
  - `Howling_Gale` (CAISO, Solar)
- **Products**: `RT_HUB`, `RT_BUS`, `DA_HUB`, `DA_BUS`

You can change assets/markets/types, forecast years, WACC, and defaults (P‑level, number of sims, negative‑price rule) in `Config`.

---

## Data Preparation

1. **Input Excel**: `data/raw/HackathonDataset.xlsx` (you provide)
   - Sheets (e.g., ERCOT, MISO, CAISO) contain:
     - Historical **RT/DA Hub & Busbar** hourly prices
     - Historical **Generation** (MWh)
     - Monthly **forward hub prices** (Peak/Off‑Peak) for the forecast window
2. **Conversion**: `convert_to_csv.py` extracts and normalizes each sheet into:
   - `ercot_valentino.csv`, `miso_mantero.csv`, `caiso_howling_gale.csv`
   - Standardized columns: `Date`, `HE`, `P/OP`, `Gen`, `RT_Hub`, `DA_Hub`, `RT_Busbar`, `DA_Busbar`

`data_loader.py` augments the frames:
- Computes **RT_Basis = RT_Busbar − RT_Hub** and **DA_Basis = DA_Busbar − DA_Hub**
- Derives `hour`, `day‑of‑week`, `is_peak` (Mon‑Fri HE 7–22), and `period = Peak/Off‑Peak`

---

## Methodology (at a Glance)

1. **Historical bucketing & regimes** (`analysis.build_hist_buckets`)
   - Bucket history by **(month, Peak/Off‑Peak)**.
   - Compute **RT Hub rolling volatility** over a configurable window (default 30 days of hours).
   - Tag **HIGH/LOW** volatility regimes via median split; keep `p_high` share of HIGH.
2. **Generation forecast** (`forecasting.forecast_generation`)
   - For each month, estimate **expected MWh** and **Peak/Off split** from history.
   - Provide monthly standard deviations as simple dispersion proxies.
3. **Forward hub expansion** (`forecasting.forecast_hub_forwards`)
   - Read the **monthly hub forward curves** (Peak/Off) for the forecast window (default 2026–2030).
4. **Monte Carlo simulation** (`monte_carlo.simulate_merchant_price_per_mwh`)
   - For each month/period draw **hub** prices with regime awareness (favor HIGH with probability `p_high` for RT).
   - Draw **basis** from historical basis distributions (RT or DA).
   - Combine **hub + basis** → node (busbar) price; optionally zero out when node price < 0 if `--neg-rule` is set.
   - Aggregate to **gen‑weighted $/MWh** across the 5‑year horizon.
5. **P‑level pricing & components** (`valuation.p_level_price`, `valuation.compute_components`)
   - Convert **P‑level** to percentile (e.g., P75 → 25th percentile).
   - Compute **gen‑weighted hub** and **basis components**, then add a **risk adjustment** so that the total equals the **P‑level price**.
   - If `--neg-rule` is enabled, also report the incremental **negative‑price adjustment**.
6. **Discounted cash flow** (`valuation.summarize_npvs`)
   - Discount monthly at **(1+WACC)^(1/12)-1**, aggregate by asset/product to produce `npv_summary.csv`.

---

## Configuration

Edit `src/config.py`:

- **Forecast window**: `FORECAST_START_YEAR=2026`, `FORECAST_YEARS=5`
- **Risk appetite**: `P_LEVEL=75` (can be overridden via CLI: `--p 90`, etc.)
- **Simulation**: `N_SIMS=3000`, `RANDOM_SEED=504`
- **WACC**: `WACC_ANNUAL=0.05` (affects DCF only)
- **Peak definition**: `PEAK_HOURS=7–22`, `PEAK_DAYS=Mon–Fri`
- **Folders**: `RAW_DIR`, `OUT_RESULTS`, `OUT_FIGS`

---

## Re‑running with Different P‑Levels

```bash
# P90 (more conservative)
python main.py --p 90 --sims 3000

# P50 (median)
python main.py --p 50 --sims 3000
```

The **P‑level** is interpreted as: “probability that fixed price is better than merchant.” Internally we price to the **(100 − P)th percentile** of simulated merchant $/MWh.

---

## Assumptions & Notes

- Forward curves are **hub‑level** monthly Peak/Off prices; basis is sourced from historical distributions.
- Generation forecasts rely on historical averages by month and Peak/Off splits; no additional plant‑level derates or outages are modeled.
- Market assets in default config: `Valentino` (ERCOT), `Mantero` (MISO), `Howling_Gale` (CAISO).
- Negative price handling is **opt‑in** via `--neg-rule` for conservatism.
- All randomness is controlled via `RANDOM_SEED` for reproducibility.

---

## Troubleshooting

- **Missing CSVs**: Run `python convert_to_csv.py` after placing the Excel at `data/raw/HackathonDataset.xlsx`.
- **Matplotlib backend issues** (headless servers): set `MPLBACKEND=Agg` in the environment.
- **Different calendar/Peak hours**: adjust `PEAK_HOURS`, `PEAK_DAYS` in `config.py`.

