from dataclasses import dataclass, field
from typing import Any
from sim_layer.utils import convert_time


@dataclass
class Packet:
    source: str
    destination: str
    timestamp: float
    size: int = 64
    data: dict[str, Any] = field(default_factory=dict)
    send_time: float | None = None

    def __str__(self):
        return f"[{convert_time(self.timestamp)}] {self.source} -> {self.destination}: {self.data}"
