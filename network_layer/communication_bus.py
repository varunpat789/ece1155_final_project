import simpy
from network_layer.packet import Packet
from typing import Any, Protocol


class PacketMonitor(Protocol):
    def observe_packet(self, packet: Packet) -> None:
        pass


class CommunicationBus:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.base_latency = 1.0
        self.delay_factor = 0.05
        self.stores: dict[str, simpy.Store] = {}
        self.packet_log: list[dict[str, Any]] = []
        self.blocked_packet_log: list[dict[str, Any]] = []
        self.blacklisted_sources: set[str] = set()
        self.packet_monitors: list[PacketMonitor] = []
        self.latency_log: list[dict[str, Any]] = []

    def get_store(self, destination: str) -> simpy.Store:
        if destination not in self.stores:
            self.stores[destination] = simpy.Store(self.env)
        return self.stores[destination]

    def add_monitor(self, monitor: PacketMonitor):
        self.packet_monitors.append(monitor)

    def add_to_blacklist(self, source: str):
        self.blacklisted_sources.add(source)

    def remove_from_blacklist(self, source: str):
        self.blacklisted_sources.discard(source)

    def is_blacklisted(self, source: str) -> bool:
        return source in self.blacklisted_sources

    def send(self, packet: Packet) -> simpy.Process:
        packet.send_time = self.env.now
        log_entry = {
            "time": self.env.now,
            "source": packet.source,
            "destination": packet.destination,
            "data": dict(packet.data),
            "blocked": False,
            "blocked_reason": "",
        }
        self.packet_log.append(log_entry)

        for monitor in self.packet_monitors:
            monitor.observe_packet(packet)

        if self.is_blacklisted(packet.source):
            log_entry["blocked"] = True
            log_entry["blocked_reason"] = "blacklisted_source"
            self.blocked_packet_log.append(log_entry)
            return self.env.process(self.drop(packet))

        return self.env.process(self.deliver(packet))

    def drop(self, packet: Packet):
        yield self.env.timeout(0)

    def deliver(self, packet: Packet):
        store = self.get_store(packet.destination)
        queue_depth_at_send = len(store.items)
        backed_up_delay = queue_depth_at_send * self.delay_factor

        yield self.env.timeout(self.base_latency + backed_up_delay)
        yield store.put(packet)

        deliver_time = self.env.now
        send_time = packet.send_time if packet.send_time is not None else packet.timestamp
        self.latency_log.append(
            {
                "send_time": send_time,
                "deliver_time": deliver_time,
                "latency": deliver_time - send_time,
                "source": packet.source,
                "destination": packet.destination,
                "queue_depth": queue_depth_at_send,
            }
        )

    def receive(self, destination: str):
        return self.get_store(destination).get()