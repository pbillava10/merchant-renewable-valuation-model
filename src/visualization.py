import os
import matplotlib.pyplot as plt
from .config import CFG

def plot_distribution(sim_prices, p75, out_path, title):
    plt.figure(figsize=(6,4))
    plt.hist(sim_prices, bins=50)
    plt.axvline(p75, linestyle="--")
    plt.title(title)
    plt.xlabel("$ / MWh"); plt.ylabel("Frequency")
    os.makedirs(CFG.OUT_FIGS, exist_ok=True)
    plt.tight_layout()
    plt.savefig(out_path, dpi=160)
    plt.close()
