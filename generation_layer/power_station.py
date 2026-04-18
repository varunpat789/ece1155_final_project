import random
from typing import Any
import simpy
from network_layer.packet import Packet
from network_layer.communication_bus import CommunicationBus
from sim_layer.utils import convert_time


class PowerStation:
    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        bus: CommunicationBus,
        voltage: float = 345_000.0,
        capacity_mw: float = 500.0,
    ):
        self.env = env
        self.name = name
        self.bus = bus
        self.voltage = voltage
        self.capacity_mw = capacity_mw
        self.output_mw = capacity_mw * 0.8
        # note: output capped by SCADA
        self.output_cap_mw: float | None = None
        self.online = True
        self.event_log: list[str] = []

    def log(self, msg: str):
        entry = f"[{convert_time(self.env.now)}] {self.name}: {msg}"
        self.event_log.append(entry)
        print(entry)

    def run(self):
        while True:
            if self.online:
                self.output_mw = max(
                    0,
                    min(self.capacity_mw, self.output_mw + random.uniform(-5, 5)),
                )
                if self.output_cap_mw is not None and self.output_mw > self.output_cap_mw:
                    self.output_mw = self.output_cap_mw

            pkt = Packet(
                source=self.name,
                destination="SCADA",
                timestamp=self.env.now,
                size=64,
                data={
                    "type": "telemetry",
                    "voltage": self.voltage,
                    "output_mw": self.output_mw,
                    "capacity_mw": self.capacity_mw,
                    "online": self.online,
                },
            )

            self.bus.send(pkt)
            yield self.env.timeout(10)

    def listen(self):
        while True:
            pkt: Packet = yield self.bus.receive(self.name)
            self.handle(pkt.data)

    def handle(self, cmd: dict[str, Any]):
        action = cmd.get("action")
        if action == "reduce_voltage":
            self.voltage -= cmd.get("volts", 10)
            self.log(f"Voltage reduced to {self.voltage:.1f} V")
        elif action == "limit_output":
            cap = cmd.get("mw", self.capacity_mw)
            self.output_cap_mw = cap
            if self.output_mw > cap:
                self.output_mw = cap
            self.log(f"Output capped at {cap:.1f} MW (current {self.output_mw:.1f} MW)")
        elif action == "clear_limit":
            self.output_cap_mw = None
            self.log("Output cap cleared")
        elif action == "shutdown":
            self.online = False
            self.output_mw = 0
            self.log("Station OFFLINE (shutdown command)")
        elif action == "restore":
            self.online = True
            self.output_mw = self.capacity_mw * 0.8
            self.output_cap_mw = None
            self.log(f"Station ONLINE, output={self.output_mw:.1f} MW")
