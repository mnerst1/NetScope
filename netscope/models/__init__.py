from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Interface:
    name: str
    ip: str
    netmask: str
    subnet: str
    mac: str = ""
    ipv6: str = ""
    gateway: str = ""
    dns: str = ""
    kind: str = ""
    speed: int = 0

    def to_dict(self):
        return asdict(self)


@dataclass
class Probe:
    ip: str
    online: bool
    latency: float | None = None
    mac: str = ""
    hostname: str = ""
