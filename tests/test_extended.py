import json
from netscope.models import Probe
from netscope.network.system import scan_targets,validate_target
from netscope.network.vendor import lookup,catalog
from netscope.repositories.database import Repository
from netscope.services.monitor import export,seed_demo
from netscope.services.reporting import html_report
import pytest


@pytest.mark.parametrize('scope',['192.0.2.0/24','198.51.100.0/24','240.0.0.0/24','0.0.0.0/24'])
def test_reserved_subnets_rejected(scope):
    with pytest.raises(ValueError):scan_targets(scope)
    with pytest.raises(ValueError):validate_target(scope.split('/')[0][:-1]+'1',scope)


def test_stale_arp_and_ip_reuse_offline(tmp_path):
    r=Repository(tmp_path/'db')
    r.merge_scan([Probe('192.168.1.2',True,1,'00:11:22:33:44:55')])
    did=r.devices()[0]['id']
    r.merge_scan([Probe('192.168.1.2',False,None,'00:11:22:33:44:55'),Probe('192.168.1.3',True,1,'00:11:22:33:44:55')],scope='192.168.1.0/24')
    assert len(r.devices())==1 and r.devices()[0]['ip']=='192.168.1.3'
    assert r.devices()[0]['online']==1
    r.merge_scan([Probe('192.168.1.3',True,1,'00:11:22:33:44:66')],scope='192.168.1.0/24')
    assert next(d for d in r.devices() if d['id']==did)['online']==0


def test_vendor_local_randomized_unknown():
    assert len(catalog())>30000
    assert lookup('02:11:22:33:44:55')==''
    assert lookup('FF:FF:FF:FF:FF:FF')==''
    assert lookup('00:00:0C:00:00:01')


def test_exports_and_html_escape(tmp_path):
    repo=Repository(tmp_path/'db')
    seed_demo(repo)
    device=repo.devices()[0]
    repo.update_device(device['id'],name='<script>alert(1)</script>')
    export(tmp_path/'devices.csv',repo.devices())
    assert (tmp_path/'devices.csv').read_bytes().startswith(b'\xef\xbb\xbf')
    export(tmp_path/'history.json',repo.export_history())
    assert len(json.loads((tmp_path/'history.json').read_text(encoding='utf-8'))['devices'])==7
    html_report(tmp_path/'report.html',repo,True,'Report',['Name','IP','Status','Trust','Availability'],{'online':'Online','offline':'Offline','trusted':'Trusted','unknown':'Unknown'})
    page=(tmp_path/'report.html').read_text(encoding='utf-8')
    assert '<script>' not in page and '&lt;script&gt;' in page and 'DEMO' in page
