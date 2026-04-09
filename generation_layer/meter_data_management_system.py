from typing import Any
import simpy
from network_layer.communication_bus import CommunicationBus
from network_layer.packet import Packet
from sim_layer.utils import convert_time


class MeterDataManagementSystem:
    MAX_METER_VOLTAGE = 127.0
    MIN_METER_VOLTAGE = 108.0
    DEMAND_RESPONSE_KW = 4.0

    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        bus: CommunicationBus,
        meter_names: list[str],
    ):
        self.env = env
        self.name = name
        self.bus = bus
        self.meter_names = set(meter_names)
        self.readings: dict[str, dict[str, Any]] = {}
        self.event_log: list[dict[str, Any]] = []

    def log(self, msg: str, level: str = "INFO"):
        entry = {"time": convert_time(self.env.now), "raw_time": self.env.now, "level": level, "msg": msg}
        self.event_log.append(entry)
        print(f"[{entry['time']}] {self.name}: {msg}")

    def run(self):
        while True:
            pkt: Packet = yield self.bus.receive(self.name)
            if pkt.source not in self.meter_names:
                continue
            d = pkt.data
            self.readings[pkt.source] = {**d, "_time": self.env.now}

            v = d.get("voltage", 120)
            kw = d.get("consumption_kw", 0)

            if v > self.MAX_METER_VOLTAGE:
                self.log(f"{pkt.source} over-voltage {v:.1f} V, reduce", "WARN")
                self.send_command(pkt.source, {"action": "reduce_voltage", "volts": 5})
                self._alert_scada(f"{pkt.source} over-voltage {v:.1f} V")

            elif v < self.MIN_METER_VOLTAGE:
                self.log(f"{pkt.source} under-voltage {v:.1f} V", "WARN")
                self._alert_scada(f"{pkt.source} under-voltage {v:.1f} V")

            if kw > self.DEMAND_RESPONSE_KW and not d.get("demand_response_active"):
                self.log(f"{pkt.source} excess consumption {kw:.2f} kW, demand response", "WARN")
                self.send_command(pkt.source, {"action": "demand_response_on"})

    def send_command(self, target: str, cmd: dict[str, Any]):
        pkt = Packet(
            source=self.name,
            destination=target,
            timestamp=self.env.now,
            size=64,
            data=cmd,
        )
        self.bus.send(pkt)

    def _alert_scada(self, message: str):
        pkt = Packet(
            source=self.name,
            destination="SCADA",
            timestamp=self.env.now,
            size=64,
            data={"type": "mdms_alert", "message": message},
        )
        self.bus.send(pkt)
