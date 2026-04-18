"""
Runs three scenarios back-to-back and writes one latency CSV per scenario:
  1. baseline   -- no attacker running
  2. attack     -- attacker running, no honeypot / ML detector / blacklist
  3. defended   -- attacker running, honeypot + ML detector + blacklist active

Each scenario gets a fresh SimPy environment and the same RNG seed so the
only thing that differs between runs is the attack / defense configuration.

Usage:
  python run_experiments.py
Outputs:
  latency_baseline.csv
  latency_attack.csv
  latency_defended.csv
  experiment_summary.json
"""

import csv
import json
import random
import simpy

from attack_layer.dos_attack import CongestionGenerator
from defense_layer.MLAttackDetector import MLAttackDetector
from generation_layer.meter_data_management_system import MeterDataManagementSystem
from generation_layer.smart_meter import SmartMeter
from generation_layer.power_station import PowerStation
from grid_layer.scada import SCADA
from honeypot_layer.honeypot import Honeypot
from network_layer.communication_bus import CommunicationBus
from network_layer.remote_terminal_unit import RemoteTerminalUnit

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE

# Shorter than test.py so three runs complete quickly; bump for the final report.
SIM_DURATION = 30 * MINUTE
ATTACK_START = 10 * MINUTE
ATTACK_STOP = 20 * MINUTE
ATTACK_INTERVAL = 0.05  # seconds between attacker packets
RNG_SEED = 42


def build_grid(env, bus):
    stations = {
        "PS-1": PowerStation(env, "PS-1", bus, voltage=345_000.0, capacity_mw=600.0),
        "PS-2": PowerStation(env, "PS-2", bus, voltage=345_000.0, capacity_mw=400.0),
        "PS-3": PowerStation(env, "PS-3", bus, voltage=500_000.0, capacity_mw=800.0),
    }
    rtus = {
        "RTU-North": RemoteTerminalUnit(env, "RTU-North", bus, input_voltage=345_000.0, output_voltage=13_800.0, base_load_mw=60.0),
        "RTU-South": RemoteTerminalUnit(env, "RTU-South", bus, input_voltage=345_000.0, output_voltage=13_600.0, base_load_mw=50.0),
    }
    north_meters = {f"HOME-{i}": SmartMeter(env, f"HOME-{i}", bus, mdms_name="MDMS-North", feeder="RTU-North", voltage=120.0, base_consumption_kw=2.0 + i * 0.3) for i in range(1, 6)}
    south_meters = {f"HOME-{i}": SmartMeter(env, f"HOME-{i}", bus, mdms_name="MDMS-South", feeder="RTU-South", voltage=120.0, base_consumption_kw=1.5 + i * 0.2) for i in range(6, 11)}
    mdms_north = MeterDataManagementSystem(env, "MDMS-North", bus, meter_names=list(north_meters.keys()), rtu_map={"RTU-North": rtus["RTU-North"]})
    mdms_south = MeterDataManagementSystem(env, "MDMS-South", bus, meter_names=list(south_meters.keys()), rtu_map={"RTU-South": rtus["RTU-South"]})
    scada = SCADA(env, bus, known_stations=list(stations.keys()), known_rtus=list(rtus.keys()))
    return stations, rtus, north_meters, south_meters, mdms_north, mdms_south, scada


def known_sources(stations, rtus, north, south, mdms_n, mdms_s):
    return {
        *stations.keys(),
        *rtus.keys(),
        *north.keys(),
        *south.keys(),
        mdms_n.name,
        mdms_s.name,
        "SCADA",
    }


def start_grid_processes(env, stations, rtus, north, south, mdms_n, mdms_s, scada):
    for ps in stations.values():
        env.process(ps.run())
        env.process(ps.listen())
    for rtu in rtus.values():
        env.process(rtu.run())
        env.process(rtu.listen())
    for meter in {**north, **south}.values():
        env.process(meter.run())
        env.process(meter.listen())
    env.process(mdms_n.run())
    env.process(mdms_s.run())
    env.process(scada.run())


def run_scenario(name: str, with_attack: bool, with_defense: bool):
    """Run one scenario end-to-end and return a dict of results."""
    random.seed(RNG_SEED)  # identical randomness across scenarios

    env = simpy.Environment()
    bus = CommunicationBus(env)
    stations, rtus, north, south, mdms_n, mdms_s, scada = build_grid(env, bus)
    start_grid_processes(env, stations, rtus, north, south, mdms_n, mdms_s, scada)

    honeypot = None
    ml_detector = None
    if with_defense:
        sources = known_sources(stations, rtus, north, south, mdms_n, mdms_s)
        ml_detector = MLAttackDetector()
        honeypot = Honeypot(env, "HONEYPOT-MONITOR", bus, sources, ml_detector)
        bus.add_monitor(honeypot)

    attacker = None
    if with_attack:
        attacker = CongestionGenerator(
            env,
            bus,
            attacker_ip="FAKE-IP-1",
            target="SCADA",
            interval=ATTACK_INTERVAL,
            start_time=ATTACK_START,
            stop_time=ATTACK_STOP,
        )
        env.process(attacker.run())

    print(f"\n[{name}] running  attack={with_attack}  defense={with_defense}")
    env.run(until=SIM_DURATION)

    # Filter out attacker traffic so the plot shows the effect on legitimate
    # grid packets rather than the attack traffic itself.
    legit_latency = [row for row in bus.latency_log if row["source"] != "FAKE-IP-1"]

    csv_path = f"latency_{name}.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["send_time", "deliver_time", "latency", "source", "destination", "queue_depth"],
        )
        writer.writeheader()
        writer.writerows(legit_latency)

    summary = {
        "scenario": name,
        "total_packets_on_bus": len(bus.packet_log),
        "blocked_packets": len(bus.blocked_packet_log),
        "legit_packets_delivered": len(legit_latency),
        "avg_legit_latency": (sum(r["latency"] for r in legit_latency) / len(legit_latency) if legit_latency else 0.0),
        "max_legit_latency": max((r["latency"] for r in legit_latency), default=0.0),
        "blacklisted_sources": sorted(bus.blacklisted_sources),
        "attacker_packets_sent": attacker.packets_sent if attacker else 0,
        "csv_path": csv_path,
    }
    print(f"[{name}] delivered={summary['legit_packets_delivered']}  avg_latency={summary['avg_legit_latency']:.3f}s  max_latency={summary['max_legit_latency']:.3f}s  blocked={summary['blocked_packets']}  blacklist={summary['blacklisted_sources']}")
    return summary


def main():
    results = [
        run_scenario("baseline", with_attack=False, with_defense=False),
        run_scenario("attack", with_attack=True, with_defense=False),
        run_scenario("defended", with_attack=True, with_defense=True),
    ]

    with open("experiment_summary.json", "w") as f:
        json.dump(
            {
                "config": {
                    "sim_duration_s": SIM_DURATION,
                    "attack_start_s": ATTACK_START,
                    "attack_stop_s": ATTACK_STOP,
                    "attack_interval_s": ATTACK_INTERVAL,
                    "rng_seed": RNG_SEED,
                },
                "scenarios": results,
            },
            f,
            indent=2,
        )
    print("\nWrote experiment_summary.json")
    print("CSVs: latency_baseline.csv, latency_attack.csv, latency_defended.csv")


if __name__ == "__main__":
    main()
