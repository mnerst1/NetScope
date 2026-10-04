"""Rich randomized demo datasets. No network calls; never writes to a live repository."""
import math
import random
import time
from netscope.models import Probe
from netscope.services.monitor import demo_interface

PROFILES=(('router','Gateway'),('pc','Workstation'),('tv','Living room TV'),
          ('phone','Phone'),('server','Home NAS'),('other','Studio speaker'),
          ('device','Tablet'),('pc','Laptop'),('other','Office printer'),
          ('other','Smart lamp'),('server','Media server'),('device','Camera'),
          ('other','Thermostat'),('phone','Guest phone'),('device','Game console'),
          ('other','Kitchen speaker'),('pc','Studio PC'),('other','E-reader'))


def connections(rng=None):
    rng=rng or random.Random()
    rows=[]
    for process,ports in [('DEMO-browser.exe',(443,8080)),('DEMO-media.exe',(554,8090)),
                          ('DEMO-sync.exe',(443,445)),('DEMO-server.exe',(8080,8443))]:
        pid=rng.randint(1000,45000)
        for port in ports:
            listening=rng.choice((True,False))
            rows.append({'protocol':'TCP','local':f'192.168.50.10:{port if listening else rng.randint(49152,65000)}',
                         'remote':'' if listening else f'192.168.50.{rng.randint(14,220)}:{port}',
                         'status':'LISTEN' if listening else 'ESTABLISHED','pid':pid,'process':process})
    rows.append({'protocol':'UDP','local':'192.168.50.10:5353','remote':'','status':'NONE',
                 'pid':rng.randint(1000,45000),'process':'DEMO-discovery.exe'})
    return rows


def populate(repo,seed=None):
    if repo.mode!='demo':
        raise ValueError('Demo population requires an isolated demo repository')
    rng=random.Random(seed)
    now=time.time()
    count=rng.randint(10,len(PROFILES))
    profiles=list(PROFILES[:2])+rng.sample(list(PROFILES[2:]),count-2)
    ips=[1,10]+rng.sample([n for n in range(14,221)],count-2)
    specs=[{'ip':f'192.168.50.{ip}','mac':f'02:DE:{rng.randrange(256):02X}:{rng.randrange(256):02X}:{rng.randrange(256):02X}:{ip:02X}',
            'kind':kind,'hostname':f'DEMO-{name.replace(" ","-")}',
            'name':name,'base':rng.uniform(1,35),'phase':rng.uniform(0,6)}
           for ip,(kind,name) in zip(ips,profiles)]
    # Replace only the explicitly designated synthetic database; preserve its UI preferences.
    with repo.connect() as c:
        for table in ('observations','latency_samples','events','snapshots','notes','traffic','devices'):
            c.execute(f'DELETE FROM {table}')
    for n in range(90):
        probes=[]
        for index,spec in enumerate(specs):
            online=index<2 or n==0 or ((n+index*3)%19<15 and rng.random()>0.025)
            if n==89 and index==count-1:
                online=False
            latency=round(max(0.5,spec['base']+math.sin(n/5+spec['phase'])*4+rng.uniform(-1,3)),1) if online else None
            probes.append(Probe(spec['ip'],online,latency,spec['mac'],spec['hostname']))
        repo.merge_scan(probes,now=now-(90-n)*30,scope=demo_interface().subnet)
        if n==44:
            repo.snapshot('DEMO • A',now=now-(90-n)*30)
        if n==74:
            devices=repo.devices()
            repo.update_device(devices[0]['id'],trusted=1,tags='DEMO, home')
            repo.snapshot('DEMO • B',now=now-(90-n)*30)
    by_ip={d['ip']:d for d in repo.devices()}
    for index,spec in enumerate(specs):
        d=by_ip[spec['ip']]
        repo.update_device(d['id'],name='DEMO • '+spec['name'],kind=spec['kind'],
                           tags=rng.choice(('DEMO, home','DEMO, studio','DEMO, guest')),
                           favorite=int(index<2 or rng.random()<0.2),trusted=int(index<2 or rng.random()<0.55))
        repo.note(d['id'],f'DEMO • Synthetic {spec["kind"]} #{rng.randint(100,999)}. Generated locally for interface preview.')
    repo.snapshot('DEMO • C',now=now)
    with repo.connect() as c:
        for n in range(180):
            rx=round(max(0.1,30+24*math.sin(n/11)+rng.uniform(-4,9)),2)
            tx=round(max(0.05,6+5*math.sin(n/18+1)+rng.uniform(-1,2)),2)
            c.execute('INSERT INTO traffic VALUES(?,?,?,?)',(now-(180-n)*2,'DEMO',rx,tx))
    repo.set_setting('demo_connections',connections(rng))
    repo.set_setting('demo_diagnostics',[['local',True,demo_interface().ip],
                     ['gateway',True,f'{rng.uniform(1,12):.1f} ms'],
                     ['dns',rng.choice((True,False)),demo_interface().dns]])
    return count
