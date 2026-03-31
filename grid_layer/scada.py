from typing import Any

import simpy
from network_layer.communication_bus import CommunicationBus
from network_layer.packet import Packet
from generation_layer.power_station import PowerStation
from sim_layer.utils import convert_time


class SCADA:
    def __init__(self, env: simpy.Environment, bus: CommunicationBus, stations: dict[str, PowerStation]):
        self.env = env
        self.bus = bus
        self.stations = stations

    def run(self):
        while True:
            pkt: Packet = yield self.bus.receive("SCADA")
            print(f"[{self.env.now:.1f}]  SCADA recieved pkt: {pkt}")

            voltage = pkt.data.get("voltage", 0)
            if voltage > 225 and pkt.source in self.stations:
                self.send_command(pkt.source, {"action": "reduce_voltage", "volts": 15})

    def send_command(self, target: str, cmd: dict[str, Any]):
        pkt = Packet(
            source="SCADA",
            destination=target,
            timestamp=self.env.now,
            size=64,
            data=cmd,
        )
        
        print(f"[{convert_time(self.env.now)}]  SCADA → {target}: {cmd}")
        self.bus.send(pkt)
