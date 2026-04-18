import json
import simpy

from attack_layer.dos_attack import CongestionGenerator
from defense_layer.MLAttackDetector import MLAttackDetector
from generation_layer.meter_data_management_system import MeterDataManagementSystem
from generation_layer.smart_meter import SmartMeter
from honeypot_layer.honeypot import Honeypot
from network_layer.communication_bus import CommunicationBus
from generation_layer.power_station import PowerStation
from grid_layer.scada import SCADA
from network_layer.remote_terminal_unit import RemoteTerminalUnit

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
SIM_DURATION = 2 * HOUR
ATTACK_START = 10 * MINUTE
ATTACK_STOP = 20 * MINUTE


def build_grid(env: simpy.Environment, bus: CommunicationBus):
    stations = {
        "PS-1": PowerStation(env, "PS-1", bus, voltage=345_000.0, capacity_mw=600.0),
        "PS-2": PowerStation(env, "PS-2", bus, voltage=345_000.0, capacity_mw=400.0),
        "PS-3": PowerStation(env, "PS-3", bus, voltage=500_000.0, capacity_mw=800.0),
    }

    rtus = {
        "RTU-North": RemoteTerminalUnit(
            env,
            "RTU-North",
            bus,
            input_voltage=345_000.0,
            output_voltage=13_800.0,
            base_load_mw=60.0,
        ),
        "RTU-South": RemoteTerminalUnit(
            env,
            "RTU-South",
            bus,
            input_voltage=345_000.0,
            output_voltage=13_600.0,
            base_load_mw=50.0,
        ),
    }

    north_meters = {
        f"HOME-{i}": SmartMeter(
            env,
            f"HOME-{i}",
            bus,
            mdms_name="MDMS-North",
            feeder="RTU-North",
            voltage=120.0,
            base_consumption_kw=2.0 + i * 0.3,
        )
        for i in range(1, 6)
    }
    south_meters = {
        f"HOME-{i}": SmartMeter(
            env,
            f"HOME-{i}",
            bus,
            mdms_name="MDMS-South",
            feeder="RTU-South",
            voltage=120.0,
            base_consumption_kw=1.5 + i * 0.2,
        )
        for i in range(6, 11)
    }

    mdms_north = MeterDataManagementSystem(
        env,
        "MDMS-North",
        bus,
        meter_names=list(north_meters.keys()),
        rtu_map={"RTU-North": rtus["RTU-North"]},
    )
    mdms_south = MeterDataManagementSystem(
        env,
        "MDMS-South",
        bus,
        meter_names=list(south_meters.keys()),
        rtu_map={"RTU-South": rtus["RTU-South"]},
    )

    scada = SCADA(
        env,
        bus,
        known_stations=list(stations.keys()),
        known_rtus=list(rtus.keys()),
    )

    return stations, rtus, north_meters, south_meters, mdms_north, mdms_south, scada


def get_valid_source_names(
    stations: dict[str, PowerStation],
    rtus: dict[str, RemoteTerminalUnit],
    north_meters: dict[str, SmartMeter],
    south_meters: dict[str, SmartMeter],
    mdms_north: MeterDataManagementSystem,
    mdms_south: MeterDataManagementSystem,
) -> set[str]:
    return {
        *stations.keys(),
        *rtus.keys(),
        *north_meters.keys(),
        *south_meters.keys(),
        mdms_north.name,
        mdms_south.name,
        "SCADA",
    }


def main():
    env = simpy.Environment()
    bus = CommunicationBus(env)

    stations, rtus, north_meters, south_meters, mdms_north, mdms_south, scada = build_grid(env, bus)
    known_sources = get_valid_source_names(stations, rtus, north_meters, south_meters, mdms_north, mdms_south)
    ml_detector = MLAttackDetector()
    honeypot = Honeypot(env, "HONEYPOT-MONITOR", bus, known_sources, ml_detector)
    bus.add_monitor(honeypot)

    attacker = CongestionGenerator(
        env,
        bus,
        attacker_ip="FAKE-IP-1",
        target="SCADA",
        interval=0.1,
        start_time=ATTACK_START,
        stop_time=ATTACK_STOP,
    )

    for ps in stations.values():
        env.process(ps.run())
        env.process(ps.listen())

    for rtu in rtus.values():
        env.process(rtu.run())
        env.process(rtu.listen())

    for meter in {**north_meters, **south_meters}.values():
        env.process(meter.run())
        env.process(meter.listen())

    env.process(mdms_north.run())
    env.process(mdms_south.run())
    env.process(scada.run())
    env.process(attacker.run())

    print("=" * 60)
    print("Starting Power Grid Sim:")
    print(f"  Duration: {SIM_DURATION // HOUR} hours sim-time")
    print(f"  Attack:   {ATTACK_START // MINUTE}m -> {ATTACK_STOP // MINUTE}m from {attacker.attacker_ip}")
    print("=" * 60)

    env.run(until=SIM_DURATION)

    print("\n" + "=" * 60)
    print("Simulation Complete:")
    print(f"  Total packets on bus: {len(bus.packet_log)}")
    print(f"  Blocked packets:      {len(bus.blocked_packet_log)}")
    print(f"  SCADA events logged:  {len(scada.event_log)}")
    print(f"  Honeypot observations: {len(honeypot.captured_packets)}")
    print(f"  Blacklisted sources:  {sorted(bus.blacklisted_sources)}")
    print("=" * 60)

    print("\nFinal SCADA telemetry snapshot:")
    for node, data in scada.telemetry.items():
        print(f"  {node}: {data}")

    with open("simulation_results.json", "w") as f:
        json.dump(
            {
                "scada_log": scada.event_log,
                "packet_count": len(bus.packet_log),
                "packet_log": bus.packet_log,
                "blocked_packet_count": len(bus.blocked_packet_log),
                "blocked_packet_log": bus.blocked_packet_log,
                "blacklisted_sources": sorted(bus.blacklisted_sources),
                "honeypot_capture_log": honeypot.capture_log,
                "ml_prediction_count": len(ml_detector.records),
                "final_telemetry": {k: {kk: vv for kk, vv in v.items() if kk != "_time"} for k, v in scada.telemetry.items()},
            },
            f,
            indent=2,
        )
    print("\nResults saved to simulation_results.json")


if __name__ == "__main__":
    main()
