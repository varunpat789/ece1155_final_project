import random
from typing import Any
import simpy
from network_layer.packet import Packet
from network_layer.communication_bus import CommunicationBus
from sim_layer.utils import convert_time


class SmartMeter:
    MIN_CONSUMPTION_KW = 0.2
    MAX_CONSUMPTION_KW = 6.0
    MIN_VOLTAGE = 100.0

    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        bus: CommunicationBus,
        mdms_name: str,
        feeder: str,
        voltage: float = 120.0,
        base_consumption_kw: float = 2.5,
    ):
        self.env = env
        self.name = name
        self.bus = bus
        self.mdms_name = mdms_name
        self.feeder = feeder
        self.nominal_voltage = voltage
        self.voltage = voltage
        self.consumption_kw = base_consumption_kw
        self.demand_response_active = False
        self.event_log: list[str] = []

    def log(self, msg: str):
        entry = f"[{convert_time(self.env.now)}] {self.name}: {msg}"
        self.event_log.append(entry)
        print(entry)

    def run(self):
        while True:
            self.consumption_kw = max(
                self.MIN_CONSUMPTION_KW,
                min(self.MAX_CONSUMPTION_KW, self.consumption_kw + random.uniform(-0.2, 0.2)),
            )
            pkt = Packet(
                source=self.name,
                destination=self.mdms_name,
                timestamp=self.env.now,
                size=64,
                data={
                    "type": "meter_reading",
                    "feeder": self.feeder,
                    "voltage": self.voltage + random.uniform(-1, 1),
                    "consumption_kw": round(self.consumption_kw, 3),
                    "demand_response_active": self.demand_response_active,
                },
            )
            self.bus.send(pkt)
            yield self.env.timeout(60)

    def listen(self):
        while True:
            pkt: Packet = yield self.bus.receive(self.name)
            self.handle(pkt.data)

    def handle(self, cmd: dict[str, Any]):
        action = cmd.get("action")
        if action == "demand_response_on":
            if not self.demand_response_active:
                self.demand_response_active = True
                self.consumption_kw *= 0.7
                self.log(f"Demand-response activated load reduced to {self.consumption_kw:.2f} kW")
        elif action == "demand_response_off":
            if self.demand_response_active:
                self.demand_response_active = False
                self.log("Demand-response disactivated")
        elif action == "reduce_voltage":
            new_v = self.voltage - cmd.get("volts", 5)
            self.voltage = max(self.MIN_VOLTAGE, new_v)
            self.log(f"Voltage reduced to {self.voltage:.1f} V")
        elif action == "set_feeder_voltage":
            rtu_v = cmd.get("rtu_voltage")
            rtu_nominal = cmd.get("rtu_nominal", 13_800.0)
            if rtu_v is not None:
                self.voltage = self.nominal_voltage * (rtu_v / rtu_nominal)
