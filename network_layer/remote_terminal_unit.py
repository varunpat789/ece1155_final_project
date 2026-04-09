import random
from typing import Any
import simpy
from network_layer.packet import Packet
from network_layer.communication_bus import CommunicationBus
from sim_layer.utils import convert_time


class RemoteTerminalUnit:
    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        bus: CommunicationBus,
        input_voltage: float = 345_000.0,
        output_voltage: float = 13_800.0,
        load_mw: float = 80.0,
    ):
        self.env = env
        self.name = name
        self.bus = bus
        self.input_voltage = input_voltage
        self.output_voltage = output_voltage
        self.load_mw = load_mw
        self.breaker_closed = True
        self.alarm = False
        self.event_log: list[str] = []

    def log(self, msg: str):
        entry = f"[{convert_time(self.env.now)}] {self.name}: {msg}"
        self.event_log.append(entry)
        print(entry)

    def run(self):
        while True:
            self.load_mw = max(10, self.load_mw + random.uniform(-3, 3))
            self.alarm = self.output_voltage > 14_500

            pkt = Packet(
                source=self.name,
                destination="SCADA",
                timestamp=self.env.now,
                size=64,
                data={
                    "type": "telemetry",
                    "input_voltage": self.input_voltage,
                    "output_voltage": self.output_voltage,
                    "load_mw": self.load_mw,
                    "breaker_closed": self.breaker_closed,
                    "alarm": self.alarm,
                },
            )
            self.bus.send(pkt)
            yield self.env.timeout(5)

    def listen(self):
        while True:
            pkt: Packet = yield self.bus.receive(self.name)
            self.handle(pkt.data)

    def handle(self, cmd: dict[str, Any]):
        action = cmd.get("action")
        if action == "open_breaker":
            self.breaker_closed = False
            self.log("Breaker OPENED")
        elif action == "close_breaker":
            self.breaker_closed = True
            self.log("Breaker CLOSED")
        elif action == "set_output_voltage":
            self.output_voltage = cmd.get("voltage", self.output_voltage)
            self.log(f"Output voltage set to {self.output_voltage:.0f} V")
        elif action == "reduce_voltage":
            self.output_voltage -= cmd.get("volts", 100)
            self.log(f"Output voltage reduced to {self.output_voltage:.0f} V")
