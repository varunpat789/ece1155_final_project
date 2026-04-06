from typing import Any
import simpy
from network_layer.communication_bus import CommunicationBus
from network_layer.packet import Packet
from sim_layer.utils import convert_time


class SCADA:
    def __init__(self, env: simpy.Environment, bus: CommunicationBus, known_nodes: list[str]):
        self.env = env
        self.bus = bus
        self.known_nodes = known_nodes
        self.debug = False
        self.max_rtu_voltage = 225

    def run(self):
        while True:
            pkt: Packet = yield self.bus.receive("SCADA")

            if self.debug:
                print(f"[{convert_time(self.env.now)}] SCADA received pkt from {pkt.source}")

            voltage = pkt.data.get("voltage", 0)

            #  safety system for rtu
            if voltage > self.max_rtu_voltage and pkt.source in self.known_nodes and "RTU" in pkt.source:
                self.send_command(pkt.source, {"action": "reduce_voltage", "volts": 15})

    def send_command(self, target: str, cmd: dict[str, Any]):
        pkt = Packet(
            source="SCADA",
            destination=target,
            timestamp=self.env.now,
            size=64,
            data=cmd,
        )

        if self.debug:
            print(f"[{convert_time(self.env.now)}] SCADA -> {target}: {cmd}")

        self.bus.send(pkt)
