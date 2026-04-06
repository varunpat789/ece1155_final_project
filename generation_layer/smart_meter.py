from typing import Any
import simpy
from network_layer.packet import Packet
from network_layer.communication_bus import CommunicationBus
from sim_layer.utils import convert_time

class SmartMeter:
    def __init__(self, env: simpy.Environment, name: str, bus: CommunicationBus, voltage: float = 120.0):
        self.env = env
        self.name = name
        self.bus = bus
        self.voltage = voltage

    def run(self):
        while True:
            pkt = Packet(
                source=self.name,
                destination="MDMS",  # Send to MDMS, not SCADA
                timestamp=self.env.now,
                size=64,
                data={"voltage": self.voltage, "type": "meter_reading"},
            )
            self.bus.send(pkt)
            yield self.env.timeout(5)

    def listen(self):
        while True:
            pkt: Packet = yield self.bus.receive(self.name)
            self.listen_cb(pkt.data)

    def listen_cb(self, cmd: dict[str, Any]):
        if cmd.get("action") == "reduce_voltage":
            self.voltage -= cmd.get("volts", 10)
            print(f"[{convert_time(self.env.now)}] {self.name} executed cmd: {cmd}, new voltage={self.voltage}")