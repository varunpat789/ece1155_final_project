import simpy
from grid_layer.scada import SCADA
from network_layer.communication_bus import CommunicationBus

# from network_layer.packet import Packet
from generation_layer.power_station import PowerStation

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE


def main():
    env = simpy.Environment()
    bus = CommunicationBus(env)

    stations = {
        "PS-1": PowerStation(env, "PS-1", bus, voltage=676767.0),
        "PS-2": PowerStation(env, "PS-2", bus, voltage=1234123.0),
        "PS-3": PowerStation(env, "PS-3", bus, voltage=54343.0),
    }

    scada = SCADA(env, bus, stations)

    for station in stations.values():
        env.process(station.run())
        env.process(station.listen())

    env.process(scada.run())
    env.run(until=100 * MINUTE)


if __name__ == "__main__":
    main()
