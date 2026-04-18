"""
Plots mean legitimate-packet latency over time for the three scenarios on the
same axes, with the attack window shaded. Uses a log y-axis so baseline and
defended (both near 1s) remain visible alongside attack (hundreds of seconds).

Usage:
  python plot_compare.py
Inputs:
  latency_baseline.csv
  latency_attack.csv
  latency_defended.csv
  experiment_summary.json   (optional, used for attack-window shading)
Output:
  latency_compare.png
"""

import csv
import json
import os
import matplotlib.pyplot as plt
import numpy as np

BIN_SIZE_S = 30.0  # seconds per bin

# (label, csv_path, color, linestyle, linewidth)
SCENARIOS = [
    ("baseline", "latency_baseline.csv", "tab:green", "-",  3.0),
    ("attack",   "latency_attack.csv",   "tab:red",   "-",  2.0),
    ("defended", "latency_defended.csv", "tab:blue",  "--", 2.0),
]


def load(path):
    rows = []
    with open(path) as f:
        for row in csv.DictReader(f):
            rows.append((float(row["send_time"]), float(row["latency"])))
    return rows


def bin_stats(samples, bin_size):
    """Return (bin_centers, mean_latency) arrays."""
    if not samples:
        return np.array([]), np.array([])
    samples.sort()
    max_t = samples[-1][0]
    n_bins = int(max_t // bin_size) + 1
    buckets = [[] for _ in range(n_bins)]
    for t, lat in samples:
        idx = int(t // bin_size)
        buckets[idx].append(lat)
    centers, means = [], []
    for i, bucket in enumerate(buckets):
        if not bucket:
            continue
        centers.append(i * bin_size + bin_size / 2)
        means.append(np.mean(bucket))
    return np.array(centers), np.array(means)


def main():
    attack_start = attack_stop = None
    if os.path.exists("experiment_summary.json"):
        with open("experiment_summary.json") as f:
            cfg = json.load(f).get("config", {})
            attack_start = cfg.get("attack_start_s")
            attack_stop = cfg.get("attack_stop_s")

    fig, ax = plt.subplots(1, 1, figsize=(12, 6))

    for label, path, color, linestyle, linewidth in SCENARIOS:
        if not os.path.exists(path):
            print(f"skipping {label}: {path} not found")
            continue
        samples = load(path)
        centers, means = bin_stats(samples, BIN_SIZE_S)
        if centers.size == 0:
            continue
        ax.plot(centers, means, label=label, color=color,
                linestyle=linestyle, linewidth=linewidth)

    if attack_start is not None and attack_stop is not None:
        ax.axvspan(attack_start, attack_stop, color="grey", alpha=0.15,
                   label="attack window")

    ax.set_yscale("log")
    ax.set_ylim(bottom=0.5)
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(loc="upper left")
    ax.set_ylabel(f"Mean latency per {int(BIN_SIZE_S)}s bin (s, log scale)")
    ax.set_xlabel("Simulation time (s)")
    ax.set_title("Packet Latency: baseline vs attack vs defended")

    plt.tight_layout()
    plt.savefig("latency_compare.png", dpi=120)
    print("Wrote latency_compare.png")
    plt.show()


if __name__ == "__main__":
    main()