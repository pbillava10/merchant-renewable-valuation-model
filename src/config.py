from dataclasses import dataclass

@dataclass
class Config:
    ASSETS: dict = None
    PRODUCTS: tuple = ("RT_HUB", "RT_BUS", "DA_HUB", "DA_BUS")
    PEAK_HOURS: tuple = tuple(range(7, 23))    # HE 7–22
    PEAK_DAYS: tuple = (0,1,2,3,4)            # Mon–Fri
    FORECAST_START_YEAR: int = 2026
    FORECAST_YEARS: int = 5
    WACC_ANNUAL: float = 0.05
    N_SIMS: int = 3000
    P_LEVEL: int = 75
    RANDOM_SEED: int = 504
    NEGATIVE_PRICE_RULE_DEFAULT: bool = False
    ROLLING_STD_HOURS: int = 24*30            # regime window
    BASIS_STRESS_ALPHA: float = 0.3           # congestion stress scaler
    RAW_DIR: str = "data/raw/"
    PROC_DIR: str = "data/processed/"
    OUT_RESULTS: str = "outputs/results/"
    OUT_FIGS: str = "outputs/figures/"

    def __post_init__(self):
        if self.ASSETS is None:
            self.ASSETS = {
                "Valentino":    {"market": "ERCOT", "type": "Wind"},
                "Mantero":      {"market": "MISO",  "type": "Wind"},
                "Howling_Gale": {"market": "CAISO", "type": "Solar"},
            }

CFG = Config()
