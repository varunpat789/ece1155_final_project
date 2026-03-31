import simpy

from network_layer.packet import Packet


class CommunicationBus:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.base_latency = 1.0
        self.delay_factor = 0.05
        self.stores: dict[str, simpy.Store] = {}

    def get_store(self, destination: str) -> simpy.Store:
        if destination not in self.stores:
            self.stores[destination] = simpy.Store(self.env)
        return self.stores[destination]

    def send(self, packet: Packet) -> simpy.Process:
        return self.env.process(self.deliver(packet))

    def deliver(self, packet: Packet):
        store = self.get_store(packet.destination)
        
        yield self.env.timeout(self.base_latency)
        backed_up_delay = len(store.items) * self.delay_factor
        yield self.env.timeout(backed_up_delay)
        
        yield store.put(packet)

    def receive(self, destination: str):
        return self.get_store(destination).get()
