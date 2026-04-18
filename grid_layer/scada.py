from typing import Any
import simpy
from network_layer.communication_bus import CommunicationBus
from network_layer.packet import Packet
from sim_layer.utils import convert_time


class SCADA:
    MAX_RTU_OUTPUT_V = 14_200
    PS_OVERLOAD_FRACTION = 0.95

    def __init__(
        self,
        env: simpy.Environment,
        bus: CommunicationBus,
        known_stations: list[str],
        known_rtus: list[str],
    ):
        self.env = env
        self.bus = bus
        self.known_stations = set(known_stations)
        self.known_rtus = set(known_rtus)
        self.event_log: list[dict[str, Any]] = []
        self.telemetry: dict[str, dict[str, Any]] = {}

    def log(self, msg: str, level: str = "INFO"):
        entry = {"time": convert_time(self.env.now), "raw_time": self.env.now, "level": level, "msg": msg}
        self.event_log.append(entry)
        prefix = "WARNING " if level == "WARN" else ("ERROR " if level == "ALARM" else "")
        print(f"[{entry['time']}] SCADA {prefix}{msg}")

    def run(self):
        while True:
            pkt: Packet = yield self.bus.receive("SCADA")
            src = pkt.source
            d = pkt.data

            self.telemetry[src] = {**d, "_time": self.env.now}

            ptype = d.get("type", "")

            if src in self.known_stations and ptype == "telemetry":
                mw = d.get("output_mw", 0)
                capacity = d.get("capacity_mw", 500)
                overload_limit = capacity * self.PS_OVERLOAD_FRACTION
                if mw > overload_limit:
                    self.log(
                        f"{src} over-generating ({mw:.1f}/{capacity:.0f} MW), capping",
                        "WARN",
                    )
                    self.send_command(src, {"action": "limit_output", "mw": capacity * 0.8})
                if not d.get("online", True):
                    self.log(f"{src} reports OFFLINE", "ALARM")

            elif src in self.known_rtus and ptype == "telemetry":
                ov = d.get("output_voltage", 0)
                if ov > self.MAX_RTU_OUTPUT_V:
                    self.log(f"{src} output voltage {ov:.0f} V too high, reduce", "WARN")
                    self.send_command(src, {"action": "reduce_voltage", "volts": 200})
                if d.get("alarm"):
                    self.log(f"{src} raised an alarm!", "ALARM")

            elif ptype == "mdms_alert":
                self.log(f"MDMS alert: {d.get('message', d)}", "WARN")

    def send_command(self, target: str, cmd: dict[str, Any]):
        pkt = Packet(
            source="SCADA",
            destination=target,
            timestamp=self.env.now,
            size=64,
            data=cmd,
        )
        self.log(f"CMD, {target}: {cmd}")
        self.bus.send(pkt)
