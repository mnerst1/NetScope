import json
import socket
import time
from pathlib import Path
import pytest
from netscope.models import Probe
from netscope.network import system
from netscope.repositories.database import Repository, compare_snapshots
from netscope.i18n import catalogs, validate, LOCALES


@pytest.fixture
def repo(tmp_path):
    return Repository(tmp_path/'test.db')


def test_subnet_and_mac():
    assert str(system.subnet('192.168.1.24','255.255.255.0'))=='192.168.1.0/24'
    assert system.normalize_mac('AA-BB-CC-00-01-02')=='AA:BB:CC:00:01:02'
    assert system.normalize_mac('invalid')==''
    assert len(system.scan_targets('192.168.1.0/24'))==254


@pytest.mark.parametrize('network',['8.8.8.0/24','192.168.0.0/16','127.0.0.0/24','::1/128','224.0.0.0/24'])
def test_scan_constraints(network):
    with pytest.raises(ValueError):
        system.scan_targets(network)


@pytest.mark.parametrize('ip',['8.8.8.8','192.168.2.1','192.168.1.0','192.168.1.255','127.0.0.1','::1','example.org','192.168.1.2; whoami'])
def test_target_constraints(ip):
    with pytest.raises(ValueError):
        system.validate_target(ip,'192.168.1.0/24')


def test_parsers():
    text='  192.168.1.1     aa-bb-cc-dd-ee-01    dynamic\n 192.168.1.255 ff-ff-ff-ff-ff-ff static'
    assert system.parse_arp(text)=={'192.168.1.1':'AA:BB:CC:DD:EE:01'}
    assert system.parse_ping('Reply from 192.168.1.1: bytes=32 time=3ms TTL=64',0)==3
    assert system.parse_ping('Ответ от 192.168.1.1: число байт=32 время<1мс TTL=64',0)==1
    assert system.parse_ping('Reply from 192.168.1.1: Destination host unreachable.',0) is None
    assert system.parse_ping('Request timed out.',1) is None
    assert system.parse_ping('Reply: bytes=32 duration=7 xyz TTL=64',0)==7


def test_merge_mac_dhcp_preserves_user_metadata(repo):
    repo.merge_scan([Probe('192.168.1.2',True,2,'AA:BB:CC:DD:EE:01')],now=100)
    device=repo.devices()[0]
    repo.update_device(device['id'],name='My NAS',trusted=1,tags='home')
    repo.note(device['id'],'A note')
    repo.merge_scan([Probe('192.168.1.3',True,4,'AA:BB:CC:DD:EE:01')],now=200)
    devices=repo.devices()
    assert len(devices)==1 and devices[0]['ip']=='192.168.1.3'
    assert devices[0]['name']=='My NAS' and devices[0]['first_seen']==100
    assert repo.note(device['id'])=='A note'
    assert repo.availability(device['id'])==100


def test_ip_reuse_is_different_device(repo):
    repo.merge_scan([Probe('192.168.1.2',True,2,'AA:BB:CC:DD:EE:01')],now=100)
    repo.merge_scan([Probe('192.168.1.2',True,2,'AA:BB:CC:DD:EE:02')],now=200)
    assert len(repo.devices())==2


def test_offline_and_loss(repo):
    repo.merge_scan([Probe('192.168.1.2',True,2)],now=100)
    device=repo.devices()[0]
    events=repo.merge_scan([Probe('192.168.1.2',False)],now=200)
    assert events[0]['kind']=='offline'
    assert repo.devices()[0]['last_seen']==100
    assert repo.availability(device['id'])==50
    assert repo.history(device['id'])[-1]['ms'] is None


def test_unproven_arp_is_not_new_device(repo):
    assert repo.merge_scan([Probe('192.168.1.2',False,None,'AA:BB:CC:DD:EE:01')])==[]
    assert repo.devices()==[]


def test_sql_parameterization_and_settings(repo):
    repo.set_setting('language',"'; DROP TABLE devices; --")
    assert repo.setting('language')=="'; DROP TABLE devices; --"
    assert repo.devices()==[]
    with pytest.raises(ValueError):
        repo.update_device('x',ip='8.8.8.8')
    assert Repository(repo.path).setting('language')==repo.setting('language')


def test_retention(repo):
    now=time.time()
    repo.merge_scan([Probe('192.168.1.2',True,1)],now=now-40*86400)
    repo.merge_scan([Probe('192.168.1.2',False)],now=now)
    did=repo.devices()[0]['id']
    repo.cleanup(30,now)
    assert len(repo.history(did))==1
    assert len(repo.devices())==1
    assert repo.availability(did)==0


def test_snapshots(repo):
    repo.merge_scan([Probe('192.168.1.2',True,1)])
    repo.snapshot('Before')
    d=repo.devices()[0]
    repo.update_device(d['id'],trusted=1)
    repo.snapshot('After')
    snapshots=repo.snapshots()
    result=compare_snapshots(json.loads(snapshots[1]['data']),json.loads(snapshots[0]['data']))
    assert len(result['changed'])==1 and result['added']==[] and result['removed']==[]
    assert compare_snapshots([],repo.devices())['added']


def test_port_constraints_before_any_socket(monkeypatch):
    def forbidden(*args,**kwargs):
        pytest.fail('socket created for invalid request')
    monkeypatch.setattr(socket,'socket',forbidden)
    for options in [{'consent':False},{'consent':True,'ports':(12345,)},{'consent':True,'ports':(80,80)}]:
        with pytest.raises(ValueError):
            system.check_ports('192.168.1.2','192.168.1.0/24',**options)
    with pytest.raises(ValueError):
        system.check_ports('8.8.8.8','192.168.1.0/24',consent=True)


def test_port_rate_limit(monkeypatch):
    sleeps=[]
    class Fake:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def settimeout(self,t):assert t<=0.35
        def connect_ex(self,target):return 0
    monkeypatch.setattr(socket,'socket',lambda *a:Fake())
    monkeypatch.setattr(time,'sleep',sleeps.append)
    assert system.check_ports('192.168.1.2','192.168.1.0/24',(80,443),True)==[(80,True),(443,True)]
    assert sleeps==[0.15,0.15]


def test_i18n_completeness():
    data=validate()
    assert len(data)==23
    canonical=set(data['en'])
    assert len(canonical)==122
    for locale,entries in data.items():
        assert set(entries)==canonical,locale
        assert all(v.strip() for v in entries.values()),locale


def test_literal_ui_keys_exist():
    import ast
    canonical=set(catalogs()['en'])
    for path in (Path(__file__).parents[1]/'netscope'/'ui').rglob('*.py'):
        tree=ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr in ('t','button') and node.args and isinstance(node.args[0],ast.Constant) and isinstance(node.args[0].value,str):
                assert node.args[0].value in canonical,(path,node.args[0].value)
