import csv
import json
import math
import random
import time
from netscope.models import Probe, Interface
from netscope.network.system import discover, ping


def demo_interface():
    return Interface('DEMO', '192.168.50.10', '255.255.255.0', '192.168.50.0/24', '02:00:00:00:00:10',
                     'fd00::10', '192.168.50.1', '192.168.50.1', 'Wi-Fi', 866)


def demo_scan():
    devices = [('1','Gateway'),('10','Workstation'),('14','Living room TV'),('23','Studio speaker'),('28','Phone'),('42','NAS'),('67','Tablet')]
    return [Probe('192.168.50.'+ip, True, round(1+random.random()*14,1), '02:00:00:00:00:'+f'{int(ip):02X}',name) for ip,name in devices]


def seed_demo(repo):
    if repo.devices():
        return
    for n in range(60):
        probes = demo_scan()
        probes[-1].online = n % 15 < 12
        probes[-1].latency = probes[-1].latency if probes[-1].online else None
        repo.merge_scan(probes, now=time.time()-(60-n)*30)
    for d in repo.devices():
        if d['ip'].endswith(('.1','.10','.42')):
            repo.update_device(d['id'], trusted=1, favorite=1,
                               kind='router' if d['ip'].endswith('.1') else 'pc' if d['ip'].endswith('.10') else 'server')
    repo.snapshot('DEMO A')


def monitor(repo, interface, demo=False):
    if demo:
        probes=[]
        for d in repo.devices():
            online=d['ip'] in (interface.ip,interface.gateway) or random.random()>0.1
            probes.append(Probe(d['ip'],online,round(random.uniform(1,35),1) if online else None,d['mac'],d['hostname']))
    else:
        probes=discover(interface, [d['ip'] for d in repo.devices() if d['ip'].startswith(interface.ip.rsplit('.',1)[0]+'.')])
    from netscope.network.vendor import lookup
    events = repo.merge_scan(probes, vendor=None if demo else lookup, scope=interface.subnet)
    repo.cleanup(repo.setting('retention',30))
    return events


def health(repo, interface):
    # Honest sampled metric: no score until a gateway is known and has been observed.
    gateway = next((d for d in repo.devices() if d['ip']==interface.gateway),None)
    if not gateway:
        return None
    h = repo.history(gateway['id'],20)
    if not h:
        return None
    available = sum(x['online'] for x in h)/len(h)
    ms = [x['ms'] for x in h if x['ms'] is not None]
    if not ms:
        return 0 if not available else None
    latency = sum(ms)/len(ms)
    return round(max(0, min(100, 100*available - min(30,latency/5))))


def diagnostics(interface, demo=False):
    if demo:
        return [('local',True,interface.ip),('gateway',True,'2 ms'),('dns',True,interface.dns)]
    results = [('local',True,interface.ip)]
    p = ping(interface.gateway) if interface.gateway else None
    results.append(('gateway',bool(p and p.online), f'{p.latency} ms' if p and p.online else ''))
    # DNS check asks only the configured LOCAL resolver for localhost, never an external service.
    from netscope.network.system import command
    import ipaddress
    import subprocess
    dns = interface.dns.split(',')[0].strip()
    try:
        if dns and ipaddress.ip_address(dns).is_private:
            r = command(['nslookup','localhost',dns],5)
            results.append(('dns',r.returncode==0,dns))
        else:
            results.append(('dns',None,dns))
    except (ValueError,OSError,subprocess.TimeoutExpired):
        results.append(('dns',False,dns))
    return results


def export(path, data):
    if str(path).lower().endswith('.csv'):
        rows = data if isinstance(data,list) else data.get('devices',[])
        with open(path,'w',newline='',encoding='utf-8-sig') as f:
            if rows:
                writer = csv.DictWriter(f,fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    else:
        with open(path,'w',encoding='utf-8') as f:
            json.dump(data,f,ensure_ascii=False,indent=2)
