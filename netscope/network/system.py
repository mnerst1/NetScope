"""Read-only OS adapters. Discovery never sends packets outside the selected subnet."""
import ipaddress
import json
import re
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
import psutil
from netscope.models import Interface, Probe

PORTS = (21, 22, 53, 80, 139, 443, 445, 554, 631, 3389, 8080, 8443)
LOCAL_NETWORKS = tuple(ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16','169.254.0.0/16'))


def is_local_network(net):
    return net.version == 4 and any(net.subnet_of(n) for n in LOCAL_NETWORKS)


def command(args, timeout=8):
    if sys.platform=='win32':
        import ctypes
        encoding=f'cp{ctypes.windll.kernel32.GetOEMCP()}'
    else:
        encoding='utf-8'
    return subprocess.run(args, capture_output=True, text=True, encoding=encoding, errors="replace", timeout=timeout,
                          creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                          shell=False)


def normalize_mac(value):
    raw = re.sub(r"[^0-9A-Fa-f]", "", value)
    return ":".join(raw[i:i+2] for i in range(0, 12, 2)).upper() if len(raw) == 12 else ""


def subnet(ip, mask):
    return ipaddress.ip_network(f"{ip}/{mask}", strict=False)


def validate_target(ip, network):
    addr = ipaddress.ip_address(ip)
    net = ipaddress.ip_network(network, strict=False)
    if not isinstance(addr, ipaddress.IPv4Address) or not is_local_network(net):
        raise ValueError("Local private IPv4 required")
    if addr not in net or addr in (net.network_address, net.broadcast_address) or addr.is_loopback:
        raise ValueError("Target outside authorized local subnet")
    return str(addr)


def scan_targets(network):
    net = ipaddress.ip_network(network, strict=False)
    if not is_local_network(net) or net.prefixlen < 24:
        raise ValueError("Select a private IPv4 /24 or smaller subnet (maximum 254 hosts)")
    return [str(ip) for ip in net.hosts()]


def windows_config():
    if sys.platform != "win32":
        return {}
    from netscope.network.windows import configuration
    try:
        return configuration()
    except OSError:
        pass
    # Fixed script; no user-controlled interpolation. Structured JSON avoids translated ipconfig text.
    script = "Get-NetIPConfiguration | Select-Object InterfaceAlias,@{n='Gateway';e={$_.IPv4DefaultGateway.NextHop}},@{n='DNS';e={($_.DNSServer.ServerAddresses -join ', ')}} | ConvertTo-Json -Compress"
    result = command(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], 12)
    if result.returncode:
        return {}
    rows = json.loads(result.stdout or "[]")
    if isinstance(rows, dict):
        rows = [rows]
    return {r["InterfaceAlias"]: r for r in rows}


def interfaces():
    try:
        config = windows_config()
    except (OSError, ValueError, subprocess.TimeoutExpired):
        config = {}
    stats = psutil.net_if_stats()
    items = []
    for name, addresses in psutil.net_if_addrs().items():
        if not stats.get(name) or not stats[name].isup:
            continue
        v4 = [a for a in addresses if a.family == socket.AF_INET and not ipaddress.ip_address(a.address).is_loopback]
        mac = next((normalize_mac(a.address) for a in addresses if a.family == psutil.AF_LINK), "")
        v6 = ", ".join(a.address for a in addresses if a.family == socket.AF_INET6)
        for address in v4:
            if not address.netmask:
                continue
            c = config.get(name, {})
            gateway = c.get("Gateway") or ""
            if isinstance(gateway, list):
                gateway = gateway[0] if gateway else ""
            items.append(Interface(name, address.address, address.netmask, str(subnet(address.address, address.netmask)),
                                   mac, v6, gateway, c.get("DNS") or "",
                                   c.get('Kind') or ("Wi-Fi" if any(x in name.lower() for x in ("wi-fi", "wlan", "wireless")) else "LAN"), stats[name].speed))
    # Interfaces with default routes are preferred. No public connectivity probe is needed.
    return sorted(items, key=lambda x: (not bool(x.gateway), config.get(x.name,{}).get('Metric',999), x.name))


def parse_arp(text):
    rows = {}
    for line in text.splitlines():
        match = re.search(r"\b((?:\d{1,3}\.){3}\d{1,3})\s+([0-9a-fA-F:-]{17})", line)
        if match:
            try:
                ipaddress.IPv4Address(match[1])
                mac = normalize_mac(match[2])
                if mac not in ("00:00:00:00:00:00", "FF:FF:FF:FF:FF:FF"):
                    rows[match[1]] = mac
            except ValueError:
                pass
    return rows


def arp_table(source=None):
    try:
        args=["arp","-a"]
        if source and sys.platform=='win32':
            args += ['-N',str(ipaddress.IPv4Address(source))]
        return parse_arp(command(args).stdout)
    except (OSError, subprocess.TimeoutExpired):
        return {}


def parse_ping(text, returncode):
    # Windows uses localized RTT labels, but the < / = + numeric ms expression is stable.
    matches = re.findall(r"[=<]\s*(\d+(?:[.,]\d+)?)\s*(?:ms|мс|毫秒)", text, re.I)
    ttl = re.search(r"\bTTL[= :]", text, re.I)
    if returncode != 0 or not ttl:
        return None
    if matches:
        return float(matches[0].replace(",", "."))
    # Other Windows language packs can translate the unit. The reply before TTL contains
    # byte count followed by RTT; no invented 0 ms result when parsing is unavailable.
    reply=next((line for line in text.splitlines() if re.search(r'\bTTL[= :]',line,re.I)),'')
    before=re.split(r'\bTTL[= :]',reply,flags=re.I)[0]
    numbers=re.findall(r'[=<]\s*(\d+(?:[.,]\d+)?)',before)
    return float(numbers[-1].replace(',','.')) if len(numbers)>=2 else None


def ping(ip, source=None):
    ip = str(ipaddress.ip_address(ip))
    args = ["ping", "-n", "1", "-w", "650", ip] if sys.platform == "win32" else ["ping", "-c", "1", "-W", "1", ip]
    if source and sys.platform=='win32':
        args[1:1]=['-S',str(ipaddress.IPv4Address(source))]
    try:
        r = command(args, 2.5)
        latency = parse_ping(r.stdout, r.returncode)
        return Probe(ip, r.returncode==0 and bool(re.search(r'\bTTL[= :]',r.stdout,re.I)), latency)
    except (OSError, subprocess.TimeoutExpired):
        return Probe(ip, False)


def discover(interface, known=()):
    targets = scan_targets(interface.subnet)
    before = arp_table(interface.ip)
    # Bounded 12-worker ICMP sweep, one packet per address. No reverse DNS leakage or packet capture.
    with ThreadPoolExecutor(max_workers=12) as pool:
        probes = list(pool.map(lambda target:ping(target,interface.ip), targets))
    arp = {**before, **arp_table(interface.ip)}
    known = set(known)
    result = []
    for p in probes:
        p.mac = arp.get(p.ip, "")
        if p.ip == interface.ip:
            p.online, p.latency, p.mac, p.hostname = True, 0.0, interface.mac, socket.gethostname()
        # ARP cache alone is not proof of current presence. Preserve it as identity metadata.
        if p.online or p.mac or p.ip in known:
            result.append(p)
    hosts=local_hosts()
    for p in result:
        p.hostname=p.hostname or hosts.get(p.ip,'')
    # Targeted NetBIOS node-status lookup on newly discovered hosts only. No DNS or public resolver.
    new=[p for p in result if p.online and not p.hostname and p.ip not in known]
    with ThreadPoolExecutor(max_workers=6) as pool:
        names=list(pool.map(lambda p:local_hostname(p.ip),new))
    for p,name in zip(new,names):
        p.hostname=name
    return result


def local_hosts():
    import os
    from pathlib import Path
    path=Path(os.environ.get('SystemRoot',r'C:\Windows'))/'System32/drivers/etc/hosts' if sys.platform=='win32' else Path('/etc/hosts')
    names={}
    try:
        for line in path.read_text(errors='replace').splitlines():
            cols=line.split('#',1)[0].split()
            if len(cols)>1:
                try:
                    names[str(ipaddress.IPv4Address(cols[0]))]=cols[1]
                except ValueError:
                    pass
    except OSError:
        pass
    return names


def local_hostname(ip):
    if sys.platform!='win32':
        return ''
    try:
        r=command(['nbtstat','-A',str(ipaddress.IPv4Address(ip))],3)
        match=re.search(r'^\s*(\S+)\s+<00>\s+UNIQUE',r.stdout,re.M|re.I)
        if not match:
            match=re.search(r'^\s*(\S+)\s+<00>\s+(?:УНИКАЛЬНЫЙ|EINDEUTIG|唯一|一意)',r.stdout,re.M|re.I)
        return match[1] if match else ''
    except (OSError,subprocess.TimeoutExpired):
        return ''


def local_connections():
    rows = []
    try:
        connections = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, OSError):
        return [], False
    names = {}
    for c in connections:
        if c.status not in ("LISTEN", "ESTABLISHED", "NONE"):
            continue
        if c.pid not in names:
            try:
                names[c.pid] = psutil.Process(c.pid).name() if c.pid else ""
            except (psutil.Error, OSError):
                names[c.pid] = ""
        rows.append({"protocol": "TCP" if c.type == socket.SOCK_STREAM else "UDP", "local": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                     "remote": f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "", "status": c.status,
                     "pid": c.pid or "", "process": names[c.pid]})
    return rows, True


def check_ports(ip, network, ports=PORTS, consent=False):
    import time
    if not consent:
        raise ValueError("Explicit user action required")
    ip = validate_target(ip, network)
    ports = tuple(ports)
    if not ports or len(ports) > len(PORTS) or len(set(ports)) != len(ports) or any(p not in PORTS for p in ports):
        raise ValueError("Port set outside safe allowlist")
    result = []
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.35)
            result.append((port, sock.connect_ex((ip, port)) == 0))
        time.sleep(0.15)
    return result
