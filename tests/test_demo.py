import time
import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from netscope.models import Probe
from netscope.repositories.database import Repository,compare_snapshots
from netscope.services.demo import populate
from netscope.ui.window import Window
from netscope.network import system
import json


def test_random_demo_fills_all_data_and_preserves_preferences(tmp_path):
    repo=Repository(tmp_path/'demo.db',mode='demo')
    repo.set_setting('language','ru')
    count=populate(repo,seed=1)
    assert 10<=count<=18 and len(repo.devices())==count
    assert all(repo.note(d['id']).startswith('DEMO') for d in repo.devices())
    assert len(repo.traffic_history('DEMO'))==180
    assert len(repo.events())>count
    assert len(repo.setting('demo_connections'))==9
    assert len(repo.setting('demo_diagnostics'))==3
    assert len(repo.snapshots())==3
    a,b=repo.snapshots()[:2]
    assert compare_snapshots(json.loads(b['data']),json.loads(a['data']))['changed']
    before={d['mac'] for d in repo.devices()}
    populate(repo,seed=2)
    assert before!={d['mac'] for d in repo.devices()}
    assert len(repo.snapshots())==3
    assert repo.setting('language')=='ru'


def test_population_refuses_live_database(tmp_path):
    repo=Repository(tmp_path/'live.db')
    repo.merge_scan([Probe('192.168.1.2',True,3)],now=123)
    before=repo.export_history()
    with pytest.raises(ValueError):
        populate(repo)
    assert repo.export_history()==before


def test_settings_button_opens_isolated_demo_and_returns_live(tmp_path,monkeypatch):
    monkeypatch.setattr(system,'command',lambda *a,**k:pytest.fail('Demo called a network command'))
    # No interface enumeration or live probes are allowed in this UI scenario.
    import netscope.ui.window as module
    monkeypatch.setattr(module,'interfaces',lambda:[])
    monkeypatch.setattr(module,'local_connections',lambda:pytest.fail('Demo read live connections'))
    app=QApplication.instance() or QApplication([])
    folder=tmp_path/'live';folder.mkdir()
    repo=Repository(folder/'netscope.db')
    repo.set_setting('onboarded',True)
    repo.set_setting('language','ru')
    repo.merge_scan([Probe('192.168.1.22',True,5)],now=456)
    original=repo.export_history()
    window=Window(repo,smoke=True)
    window.show()
    app.processEvents()
    window.navigate(8)
    assert window.demo_button.text()=='Демо-записи'
    window.demo_button.click()
    child=window.demo_window
    deadline=time.monotonic()+10
    while child.demo_generating and time.monotonic()<deadline:
        app.processEvents()
        time.sleep(.01)
    assert not child.demo_generating
    assert child.demo and child.repo.mode=='demo'
    assert child.repo.path!=repo.path
    assert repo.export_history()==original
    assert child.devices_table.rowCount()>=10
    assert child.connection_table.rowCount()==9
    assert child.diagnostic_table.rowCount()==3
    assert len(child.rx_chart.values)==180
    assert child.comparison.rowCount()>0
    assert child.map.devices
    assert child.overview_events.rowCount()>0
    child.return_to_live()
    assert window.isVisible() and not child.isVisible()
    assert repo.export_history()==original
    window.quit()
    app.processEvents()
