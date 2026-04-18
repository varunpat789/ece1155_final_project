import csv
import matplotlib.pyplot as plt
from collections import defaultdict

by_dest = defaultdict(list)  # destination -> [(send_time, latency), ...]
with open("latency_trace.csv") as f:
    for row in csv.DictReader(f):
        by_dest[row["destination"]].append((float(row["send_time"]), float(row["latency"])))

plt.figure(figsize=(12, 6))
for dest, samples in by_dest.items():
    xs, ys = zip(*samples)
    plt.plot(xs, ys, label=dest, marker=".", linestyle="", markersize=3, alpha=0.6)

plt.xlabel("Simulation time (s)")
plt.ylabel("Latency (s)")
plt.title("Per-packet latency over time")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("latency_plot.png", dpi=120)
plt.show()
