import random
from typing import Any
import simpy
from network_layer.packet import Packet
from network_layer.communication_bus import CommunicationBus
from sim_layer.utils import convert_time


class SmartMeter:
    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        bus: CommunicationBus,
        mdms_name: str,
        voltage: float = 120.0,
        base_consumption_kw: float = 2.5,
    ):
        self.env = env
        self.name = name
        self.bus = bus
        self.mdms_name = mdms_name
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
                0.2,
                self.consumption_kw + random.uniform(-0.3, 0.3),
            )
            pkt = Packet(
                source=self.name,
                destination=self.mdms_name,
                timestamp=self.env.now,
                size=64,
                data={
                    "type": "meter_reading",
                    "voltage": self.voltage + random.uniform(-2, 2),
                    "consumption_kw": round(self.consumption_kw, 3),
                    "demand_response_active": self.demand_response_active,
                },
            )
            self.bus.send(pkt)
            yield self.env.timeout(15)

    def listen(self):
        while True:
            pkt: Packet = yield self.bus.receive(self.name)
            self.handle(pkt.data)

    def handle(self, cmd: dict[str, Any]):
        action = cmd.get("action")
        if action == "demand_response_on":
            self.demand_response_active = True
            self.consumption_kw *= 0.7
            self.log(f"Demand-response ON — load reduced to {self.consumption_kw:.2f} kW")
        elif action == "demand_response_off":
            self.demand_response_active = False
            self.log("Demand-response OFF")
        elif action == "reduce_voltage":
            self.voltage -= cmd.get("volts", 5)
            self.log(f"Voltage reduced to {self.voltage:.1f} V")
