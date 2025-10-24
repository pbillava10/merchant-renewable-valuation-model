# Merchant Renewable Valuation Model  
### Valuation Model and Risk-Adjusted Re-Contracting Tool (2026–2030)

This repository implements a quantitative, reproducible, and decision-oriented valuation model to assess merchant renewable generation assets and determine the risk-adjusted fixed price for re-contracting over a five-year horizon (2026–2030).  

The model is designed for developers and risk teams evaluating post-PPA assets. It ingests real historical and forward market data, simulates future price uncertainty, applies a Certainty-Equivalent (CARA) risk adjustment, and identifies optimal hedge ratios that satisfy defined probability thresholds (e.g., P75).

---

## 1. Key Capabilities

- End-to-end Excel ingestion – Reads `HackathonDataset.xlsx` directly (no manual preprocessing).  
- Hourly valuation – Expands monthly hub forward prices to hourly resolution using standard peak definitions.  
- Basis modeling – Estimates RT and DA basis (Busbar – Hub) from historical data.  
- Stochastic simulation – Generates Monte Carlo price paths for RT/DA busbar prices.  
- Risk-adjusted valuation – Computes Certainty-Equivalent (λ-based) prices and risk premiums.  
- Hedge optimization – Determines both:
  - the CE-optimal hedge ratio, and  
  - the minimum fixed share achieving P≥target (default: P75).  
- Reproducibility – Fully configuration-driven, seeded simulations, deterministic outputs.  
- Comprehensive reporting – Generates complete tables and figures for management review.

---

## 2. Repository Structure

```
merchant-renewable-valuation-model/
│
├── avangrid_pricer/
│   ├── io/xlsx_io.py              # Excel data ingestion and cleaning
│   ├── run.py                     # Main processing workflow
│   ├── sim/scenarios.py           # Monte Carlo simulation engine
│   ├── risk/ce.py                 # Certainty-Equivalent computation
│   ├── hedge/mix_opt.py           # Hedge ratio optimization
│   ├── pricing/pricebook.py       # Pricebook construction
│   ├── reports/                   # Report writers and chart generators
│   └── utils/                     # Logging, seeding, validation utilities
│
├── config/
│   └── model.json                 # Configuration file
│
├── data/
│   └── HackathonDataset.xlsx      # Input dataset
│
├── out/                           # Generated outputs
│
├── requirements.txt
├── main.py
└── README.md
```

---

## 3. Environment Setup

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

**requirements.txt**

```
pandas==2.2.3
numpy==1.26.4
matplotlib==3.9.2
openpyxl==3.1.5
```

---

## 4. Configuration File (`config/model.json`)

```json
{
  "run_name": "valuation_2026_2030",
  "start_month": "2026-01",
  "end_month": "2030-12",
  "tz": "America/New_York",
  "n_sims": 5000,
  "seed": 42,
  "assets": ["ERCOT", "MISO", "CAISO"],
  "risk": { "lambda": 0.0003, "p_levels": [0.5, 0.75, 0.9] },
  "hedge": { "grid_start": 0.0, "grid_end": 1.0, "grid_step": 0.02, "target_p": 0.75 },
  "io": {
    "xlsx_path": "data/HackathonDataset.xlsx",
    "out_dir": "out"
  }
}
```

| Key | Description |
|-----|--------------|
| `lambda` | Risk aversion parameter (CARA). Higher values imply higher risk aversion. |
| `target_p` | Desired probability that hedged revenue ≥ merchant revenue. |
| `n_sims` | Number of Monte Carlo simulation runs per asset. |
| `tz` | Time zone for timestamp localization (DST handled automatically). |

---

## 5. Running the Model

```bash
python main.py -c config/model.json
```

All output files will be written to the directory specified in `out_dir`.

---

## 6. Input Data Specification

Each Excel sheet represents a single asset (e.g., `ERCOT`, `MISO`, `CAISO`).

**Historical Data Columns**
```
Date, HE, Gen, RT Busbar, RT Hub, DA Busbar, DA Hub
```

**Forward Price Columns**
```
Month (e.g., Jan-26), Peak, Off Peak
```

**Formatting and Cleaning**
- Currency symbols (`$`, `,`) and parentheses for negatives are automatically cleaned.  
- Missing months are filled deterministically using:
  1. Month-of-year averages from available forwards,  
  2. Seasonal hub averages from historical hub data,  
  3. Global mean fallback.  

All filled months are logged and summarized in `assumptions.md`.

---

## 7. Methodology Overview

1. **Forward Expansion**  
   Convert monthly hub forwards to hourly prices using peak/off-peak schedules (Mon–Fri, HE 7–22).

2. **Basis Estimation**  
   Compute historical RT and DA basis distributions per asset and model them as normal (μ, σ).

3. **Monte Carlo Simulation**  
   Generate price paths around hub forwards with stochastic basis realizations.

4. **Risk Adjustment (Certainty Equivalent)**  
   Compute CE prices using:
   \[
   CE = -\frac{1}{\lambda} \ln(\mathbb{E}[e^{-\lambda X}])
   \]
   Risk Premium = Expected − CE.

5. **Hedge Optimization**  
   Evaluate hedge mixes between merchant and fixed exposure to identify:
   - CE-optimal hedge ratio, and  
   - Minimum hedge ratio meeting P≥target (P75 by default).

---

## 8. Generated Outputs (`/out`)

| File | Description |
|------|--------------|
| `monthly_generation.csv` | Expected generation by month and period (Peak/Off-Peak). |
| `term_fixed_prices.csv` | Four fixed prices ($/MWh) per asset (RT/DA × hub/busbar). |
| `pricebook.csv` | Comprehensive valuation components and risk-adjusted prices. |
| `price_breakdown.csv` | Hub, Basis, and Risk Premium decomposition. |
| `hedge_summary.csv` | Hedge optimization summary (CE-optimal and P-target). |
| `portfolio_summary.csv` | Manager view summary per asset. |
| `frontier.png` | CE frontier chart. |
| `pcurve.png` | Probability curve for hedge performance. |
| `assumptions.md` | Notes on run parameters and data assumptions. |

---

## 9. Troubleshooting

| Issue | Description | Resolution |
|--------|--------------|-------------|
| `AmbiguousTimeError` | Duplicate hours due to DST | Handled internally via `_safe_localize()`; ensure valid `tz`. |
| `Missing forward values` | Empty forward months | History fallback automatically fills missing months. |
| `Reindex duplicate timestamp` | Non-unique hourly data | Aggregates duplicate timestamps prior to reindexing. |
| `Matplotlib backend error` | No display in headless environments | Set `MPLBACKEND=Agg`. |

---

## 10. Verification Checklist

- Risk premium (Expected – CE) ≥ 0.  
- Hedge summary satisfies P≥target (e.g., ≥0.75).  
- Frontier and P-curve show consistent monotonic behavior.  
- No missing or NaN values in key output columns.

---

## 11. License

MIT License.  
Use, modify, and distribute under open terms with attribution.

---

## 12. Acknowledgments

Developed as part of the Avangrid Hackathon 2025 using anonymized market data.  
Acknowledgment to Avangrid mentors and reviewers for guidance and evaluation framework.

---

## 13. Contact

**Author:** Pallavi Billava, Shreya Galurgi and Sharvari Salgaonkar
**Email:** [pbillava@binghamton.edu](mailto:pbillava@binghamton.edu)  

