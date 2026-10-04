import json
import time
import math
import ipaddress
from datetime import datetime
from pathlib import Path
import psutil
from PySide6.QtCore import Qt, QTimer, QThreadPool, QUrl, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut, QColor, QGuiApplication
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QFrame,QVBoxLayout,QHBoxLayout,QGridLayout,
 QStackedWidget,QLabel,QPushButton,QLineEdit,QComboBox,QSpinBox,QCheckBox,QTextEdit,QTableWidgetItem,
 QFileDialog,QDialog,QDialogButtonBox,QFormLayout,QMenu,QSystemTrayIcon,QScrollArea,QColorDialog,QListWidget)
from netscope.i18n import I18n, LOCALES
from netscope.network.system import interfaces, scan_targets, local_connections, check_ports, PORTS
from netscope.services.monitor import monitor, seed_demo, demo_interface, diagnostics, health, export
from netscope.repositories.database import compare_snapshots
from netscope.workers import Task
from netscope.ui.widgets import Card, Toast, SortItem, label, table
from netscope.ui.charts import SparkChart, NetworkMap
from netscope.ui.theme import stylesheet, ACCENTS
from netscope.utils.paths import asset

PAGES=('overview','devices','map','traffic','connections','events','diagnostics','reports','settings')
KINDS=('device','router','pc','phone','server','tv','other')


def timestamp(ts):
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else '—'


class Window(QMainWindow):
    demo_populated=Signal()
    def __init__(self,repo,demo=False,smoke=False):
        super().__init__()
        self.repo,self.demo,self.smoke=repo,demo,smoke
        self.i18n=I18n(repo.setting('language','en'))
        self.pool=QThreadPool(self)
        self.pool.setMaxThreadCount(3)
        self.tasks=set()
        self.interface=demo_interface() if demo else None
        self.interface_list=[self.interface] if demo else []
        self.page_index=0
        self.scanning=False
        self.paused=False
        self.connection_busy=False
        self.traffic_busy=False
        self.last_io=None
        self.rx,self.tx=0.,0.
        self.last_scan=None
        self.port_busy=False
        self.port_last=0.
        self.allow_quit=False
        self.demo_window=None
        self.demo_owner=None
        self.demo_generating=False
        self.demo_generation_succeeded=False
        self.setWindowTitle('NetScope • Day 014'+(' • DEMO' if demo else ''))
        self.setWindowIcon(QIcon(str(asset('netscope.ico'))))
        self.resize(1440,900)
        self.setMinimumSize(1280,720)
        self.toast=Toast(self)
        self.scan_timer=QTimer(self)
        self.scan_timer.timeout.connect(self.scan)
        self.io_timer=QTimer(self)
        self.io_timer.timeout.connect(self.sample_io)
        self.io_timer.start(2000)
        self.connection_timer=QTimer(self)
        self.connection_timer.timeout.connect(self.refresh_connections)
        self.connection_timer.start(7000)
        self.make_tray()
        self.i18n.changed.connect(lambda:QTimer.singleShot(0,self.rebuild))
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _:QTimer.singleShot(0,self.rebuild) if self.repo.setting('theme','dark')=='system' else None)
        if demo:
            seed_demo(repo)
        self.rebuild()
        QShortcut(QKeySequence('Ctrl+K'),self,activated=self.palette)
        QShortcut(QKeySequence('F5'),self,activated=self.scan)
        if not demo:
            self.job(interfaces,self.interfaces_ready)
        else:
            self.activate_monitor()

    def t(self,key):
        return self.i18n.t(key)

    def job(self,fn,callback=None,finished=None):
        task=Task(fn)
        self.tasks.add(task)
        if callback:
            task.signals.result.connect(callback)
        task.signals.error.connect(lambda _:self.toast.show_text(self.t('error')))
        def done():
            self.tasks.discard(task)
            if finished:
                finished()
        task.signals.finished.connect(done)
        self.pool.start(task)

    def button(self,key,callback,primary=False):
        w=QPushButton(self.t(key))
        if primary:
            w.setObjectName('primary')
        w.clicked.connect(callback)
        return w

    def make_tray(self):
        self.tray=QSystemTrayIcon(self.windowIcon(),self)
        self.tray.setToolTip('NetScope'+(' • DEMO' if self.demo else ''))
        self.tray.activated.connect(lambda reason:self.showNormal() if reason==QSystemTrayIcon.DoubleClick else None)
        if not self.smoke and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def rebuild(self):
        app=QApplication.instance()
        # Retire old pages before changing the global style; avoid restyling dozens of stale trees.
        old=self.takeCentralWidget()
        if old:
            old.hide()
            old.deleteLater()
            from PySide6.QtCore import QCoreApplication, QEvent
            QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
        app.setLayoutDirection(Qt.RightToLeft if self.i18n.language in ('ar','fa') else Qt.LeftToRight)
        dark=QGuiApplication.styleHints().colorScheme()==Qt.ColorScheme.Dark
        from netscope.ui.theme import palette
        app.setPalette(palette(self.repo.setting('theme','dark'),dark))
        app.setStyleSheet(stylesheet(self.repo.setting('theme','dark'),self.repo.setting('style','fluent'),self.repo.setting('accent','#5d92ff'),dark))
        root=QWidget()
        layout=QHBoxLayout(root)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)
        sidebar=QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(224)
        sl=QVBoxLayout(sidebar)
        sl.setContentsMargins(16,26,16,20)
        sl.addWidget(label('◉  NetScope','brand'))
        sl.addWidget(label('DAY 014  /  v1.0.0','muted'))
        sl.addSpacing(28)
        self.nav=[]
        symbols=('◈','▦','⌘','↗','⇄','≡','◎','▤','⚙')
        for i,key in enumerate(PAGES):
            b=QPushButton(symbols[i]+'   '+self.t(key))
            b.setObjectName('nav')
            b.setCheckable(True)
            b.clicked.connect(lambda checked=False,index=i:self.navigate(index))
            sl.addWidget(b)
            self.nav.append(b)
        sl.addStretch()
        sl.addWidget(label('DEMO' if self.demo else self.t('local_only'),'badge'))
        sl.addWidget(label(self.t('privacy_hint'),'muted'))
        layout.addWidget(sidebar)
        self.stack=QStackedWidget()
        layout.addWidget(self.stack,1)
        self.builders=(self.overview_page,self.devices_page,self.map_page,self.traffic_page,self.connections_page,
                       self.events_page,self.diagnostics_page,self.reports_page,self.settings_page)
        for key,builder in zip(PAGES,self.builders):
            page=QWidget()
            page.setObjectName('page')
            vl=QVBoxLayout(page)
            vl.setContentsMargins(28,24,28,24)
            vl.setSpacing(18)
            header=QHBoxLayout()
            header.addWidget(label(self.t(key),'title'))
            header.addStretch()
            if self.demo:
                header.addWidget(label('DEMO','badge'))
            if key=='overview':
                self.status_label=label(self.t('ready'),'badge')
                header.addWidget(self.status_label)
                self.pause_button=self.button('pause',self.toggle_pause)
                header.addWidget(self.pause_button)
                self.scan_button=self.button('scan',self.scan,True)
                header.addWidget(self.scan_button)
            vl.addLayout(header)
            builder(vl)
            scroll=QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            self.stack.addWidget(scroll)
        self.setCentralWidget(root)
        menu=QMenu()
        menu.addAction(self.t('show'),self.showNormal)
        menu.addAction(self.t('pause'),self.toggle_pause)
        menu.addAction(self.t('scan'),self.scan)
        menu.addAction(self.t('export'),self.export_devices)
        menu.addSeparator()
        menu.addAction(self.t('quit'),self.quit)
        self.tray.setContextMenu(menu)
        self.tray_menu=menu
        self.navigate(self.page_index)
        self.refresh()

    def navigate(self,index):
        self.page_index=index
        self.stack.setCurrentIndex(index)
        for i,b in enumerate(self.nav):
            b.setChecked(i==index)
        if index==4:
            self.refresh_connections()

    def overview_page(self,vl):
        vl.addWidget(label(self.t('overview_hint'),'muted'))
        cards=QHBoxLayout()
        self.cards={}
        for key in ('online','unknown','health','download'):
            c=Card(self.t(key),'—','Mbps' if key=='download' else '')
            cards.addWidget(c)
            self.cards[key]=c
        vl.addLayout(cards)
        grid=QGridLayout()
        chartpanel=QFrame()
        chartpanel.setObjectName('panel')
        cp=QVBoxLayout(chartpanel)
        cp.addWidget(label(self.t('latency')+' • '+self.t('gateway')+' / ms','badge'))
        self.gateway_chart=SparkChart()
        cp.addWidget(self.gateway_chart)
        cp.addWidget(label(self.t('health_hint'),'muted'))
        grid.addWidget(chartpanel,0,0)
        infopanel=QFrame()
        infopanel.setObjectName('panel')
        ip=QVBoxLayout(infopanel)
        ip.addWidget(label(self.t('interface'),'badge'))
        self.interface_info=label(self.t('loading'))
        ip.addWidget(self.interface_info)
        ip.addStretch()
        grid.addWidget(infopanel,0,1)
        grid.setColumnStretch(0,3)
        grid.setColumnStretch(1,2)
        vl.addLayout(grid)
        vl.addWidget(label(self.t('events'),'badge'))
        self.overview_events=table([self.t('last_seen'),self.t('device'),self.t('status')])
        vl.addWidget(self.overview_events,1)

    def devices_page(self,vl):
        bar=QHBoxLayout()
        self.device_search=QLineEdit()
        self.device_search.setPlaceholderText(self.t('search'))
        self.device_search.textChanged.connect(self.refresh_devices)
        bar.addWidget(self.device_search,1)
        self.device_filter=QComboBox()
        for k in ('all','online','offline','unknown','trusted','favorite'):
            self.device_filter.addItem(self.t(k),k)
        self.device_filter.currentIndexChanged.connect(self.refresh_devices)
        bar.addWidget(self.device_filter)
        bar.addWidget(self.button('export',self.export_devices))
        bar.addWidget(self.button('snapshot',self.save_snapshot))
        vl.addLayout(bar)
        self.devices_table=table([self.t(k) for k in ('name','status','ipv4','mac','type','latency','availability','trusted')])
        self.devices_table.itemDoubleClicked.connect(self.open_selected)
        self.devices_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.devices_table.customContextMenuRequested.connect(self.device_menu)
        vl.addWidget(self.devices_table,1)
        vl.addWidget(self.button('details',self.open_selected))
        self.devices_empty=label(self.t('empty'),'muted')
        vl.addWidget(self.devices_empty)

    def map_page(self,vl):
        vl.addWidget(label(self.t('map_hint'),'muted'))
        self.map=NetworkMap(self.i18n)
        self.map.setMinimumHeight(480)
        vl.addWidget(self.map,1)

    def traffic_page(self,vl):
        vl.addWidget(label(self.t('traffic_hint'),'muted'))
        row=QHBoxLayout()
        self.rx_card=Card(self.t('download'),'—','Mbps')
        self.tx_card=Card(self.t('upload'),'—','Mbps')
        row.addWidget(self.rx_card)
        row.addWidget(self.tx_card)
        vl.addLayout(row)
        vl.addWidget(label(self.t('download')+' / Mbps','badge'))
        self.rx_chart=SparkChart(color='#39c5dc')
        vl.addWidget(self.rx_chart)
        vl.addWidget(label(self.t('upload')+' / Mbps','badge'))
        self.tx_chart=SparkChart(color='#a383ff')
        vl.addWidget(self.tx_chart)
        vl.addStretch()

    def connections_page(self,vl):
        vl.addWidget(label(self.t('access_hint'),'muted'))
        row=QHBoxLayout()
        self.connection_search=QLineEdit()
        self.connection_search.setPlaceholderText(self.t('search'))
        self.connection_search.textChanged.connect(self.filter_connections)
        row.addWidget(self.connection_search,1)
        self.connection_filter=QComboBox()
        self.connection_filter.addItems([self.t('all'),'LISTEN','ESTABLISHED','UDP'])
        self.connection_filter.currentIndexChanged.connect(self.filter_connections)
        row.addWidget(self.connection_filter)
        row.addWidget(self.button('scan',self.refresh_connections))
        vl.addLayout(row)
        self.connection_table=table([self.t(k) for k in ('protocol','local','remote','status','pid','process')])
        self.connection_rows=self.repo.setting('demo_connections',[]) if self.demo else []
        vl.addWidget(self.connection_table,1)
        self.connection_status=label('','muted')
        vl.addWidget(self.connection_status)

    def events_page(self,vl):
        self.event_search=QLineEdit()
        self.event_search.setPlaceholderText(self.t('search'))
        self.event_search.textChanged.connect(self.refresh_events)
        vl.addWidget(self.event_search)
        self.event_table=table([self.t(k) for k in ('last_seen','device','status','ipv4')])
        vl.addWidget(self.event_table,1)
        vl.addWidget(self.button('export',self.export_history))

    def diagnostics_page(self,vl):
        vl.addWidget(label(self.t('diagnostics_hint'),'muted'))
        self.diagnostic_button=self.button('scan',self.run_diagnostics,True)
        vl.addWidget(self.diagnostic_button)
        self.diagnostic_table=table([self.t('type'),self.t('status'),self.t('details')])
        vl.addWidget(self.diagnostic_table,1)
        self.all_interfaces=label('','muted')
        vl.addWidget(self.all_interfaces)

    def reports_page(self,vl):
        row=QHBoxLayout()
        row.addWidget(self.button('snapshot',self.save_snapshot,True))
        row.addWidget(self.button('export',self.export_history))
        row.addWidget(self.button('report',self.export_report))
        row.addStretch()
        vl.addLayout(row)
        vl.addWidget(label(self.t('compare'),'badge'))
        row=QHBoxLayout()
        self.snapshot_a,self.snapshot_b=QComboBox(),QComboBox()
        row.addWidget(self.snapshot_a,1)
        row.addWidget(self.snapshot_b,1)
        row.addWidget(self.button('compare',self.compare))
        vl.addLayout(row)
        self.comparison=table([self.t('status'),self.t('name'),self.t('ipv4'),self.t('details')])
        vl.addWidget(self.comparison,1)
        vl.addWidget(label(self.t('report_hint'),'muted'))

    def settings_page(self,vl):
        form=QFormLayout()
        form.setSpacing(16)
        language=QComboBox()
        for code,native in LOCALES.items():
            language.addItem(native,code)
        language.setCurrentIndex(language.findData(self.i18n.language))
        language.currentIndexChanged.connect(lambda _:self.change_language(language.currentData()))
        form.addRow(self.t('language'),language)
        self.interface_combo=QComboBox()
        self.populate_interfaces()
        self.interface_combo.currentIndexChanged.connect(self.select_interface)
        form.addRow(self.t('interface'),self.interface_combo)
        for setting,values in [('theme',('light','dark','system')),('style',('fluent','glass','graphite','minimal','compact','oled'))]:
            combo=QComboBox()
            for value in values:
                combo.addItem(self.t(value),value)
            combo.setCurrentIndex(combo.findData(self.repo.setting(setting,values[1] if setting=='theme' else values[0])))
            combo.currentIndexChanged.connect(lambda _,c=combo,k=setting:self.change_appearance(k,c.currentData()))
            form.addRow(self.t(setting),combo)
        colors=QHBoxLayout()
        for color in ACCENTS.values():
            b=QPushButton('●')
            b.setFixedWidth(42)
            b.setStyleSheet(f'color:{color}; font-size:23px;')
            b.clicked.connect(lambda checked=False,c=color:self.change_appearance('accent',c))
            colors.addWidget(b)
        colors.addWidget(self.button('custom',self.custom_accent))
        form.addRow(self.t('accent'),colors)
        for key,minimum,maximum,default in [('interval',15,3600,60),('retention',1,365,30)]:
            spin=QSpinBox()
            spin.setRange(minimum,maximum)
            spin.setValue(self.repo.setting(key,default))
            spin.setSuffix(' '+self.t('seconds' if key=='interval' else 'days'))
            spin.valueChanged.connect(lambda value,k=key:self.setting_changed(k,value))
            form.addRow(self.t(key),spin)
        for key,default in [('discovery',False),('notifications',True),('notify_offline',False),('tray',True),('autostart',False)]:
            check=QCheckBox(self.t(key))
            check.setChecked(self.repo.setting(key,default))
            if key=='autostart':
                check.setEnabled(not self.demo and __import__('sys').platform=='win32' and not self.smoke)
            check.toggled.connect(lambda value,k=key:self.setting_changed(k,value))
            form.addRow('',check)
        vl.addLayout(form)
        vl.addWidget(label(self.t('consent'),'muted'))
        vl.addWidget(label(self.t('privacy_hint'),'badge'))
        vl.addWidget(label(self.t('demo_hint'),'muted'))
        self.demo_button=self.button('demo_records',self.generate_demo,True)
        self.demo_button.setEnabled(not self.demo_generating)
        vl.addWidget(self.demo_button)
        if self.demo and self.demo_owner:
            vl.addWidget(self.button('live_records',self.return_to_live))
        vl.addStretch()

    def generate_demo(self):
        if not self.demo:
            if self.demo_window is None:
                from netscope.repositories.database import Repository
                path=Path(self.repo.path).resolve().parent.parent/'demo'
                path.mkdir(parents=True,exist_ok=True)
                repo=Repository(path/'settings-preview.db',mode='demo')
                for key,default in [('language','en'),('theme','dark'),('style','fluent'),('accent','#5d92ff')]:
                    repo.set_setting(key,self.repo.setting(key,default))
                self.demo_window=Window(repo,demo=True,smoke=self.smoke)
                self.demo_window.demo_owner=self
                self.demo_window.tray.hide()
                self.demo_window.rebuild()
            child=self.demo_window
            self.paused_before_demo=self.paused
            self.paused=True
            self.scan_timer.stop()
            self.io_timer.stop()
            self.connection_timer.stop()
            self.pause_button.setText(self.t('resume'))
            child.move(self.pos())
            child.resize(self.size())
            child.showNormal()
            self.hide()
            child.generate_demo()
            return
        if self.demo_generating:
            return
        self.demo_generating=True
        self.demo_generation_succeeded=False
        self.scan_timer.stop()
        self.io_timer.stop()
        self.connection_timer.stop()
        self.demo_button.setEnabled(False)
        self.status_label.setText(self.t('loading'))
        # Drain old demo work asynchronously before replacing its records.
        def start_when_idle():
            if self.tasks:
                QTimer.singleShot(50,start_when_idle)
                return
            from netscope.services.demo import populate
            def ready(_):
                self.last_io=None
                self.refresh()
                self.show_demo_data()
                self.navigate(0)
                self.toast.show_text(self.t('saved')+' • DEMO')
                self.demo_generation_succeeded=True
                self.demo_populated.emit()
            def finish():
                self.demo_generating=False
                self.demo_button.setEnabled(True)
                self.status_label.setText(self.t('ready'))
                if not self.demo_owner or self.isVisible():
                    self.io_timer.start(2000)
                    self.connection_timer.start(7000)
                    if not self.paused:
                        self.scan_timer.start(self.repo.setting('interval',60)*1000)
            self.job(lambda:populate(self.repo),ready,finish)
        start_when_idle()

    def show_demo_data(self):
        if not self.demo:
            return
        from netscope.services.demo import connections
        self.connection_rows=self.repo.setting('demo_connections',None) or connections()
        self.filter_connections()
        rows=self.repo.traffic_history('DEMO')
        if rows:
            self.rx,self.tx=rows[-1]['rx'],rows[-1]['tx']
            self.rx_card.value.setText(f'{self.rx:.2f}')
            self.tx_card.value.setText(f'{self.tx:.2f}')
            self.cards['download'].value.setText(f'{self.rx:.2f}')
            self.rx_chart.set_values([r['rx'] for r in rows])
            self.tx_chart.set_values([r['tx'] for r in rows])
        results=self.repo.setting('demo_diagnostics',None) or diagnostics(self.interface,True)
        self.fill(self.diagnostic_table,[[self.t(k),self.t('passed' if ok else 'failed' if ok is False else 'skipped'),detail] for k,ok,detail in results])
        if self.snapshot_a.count()>1:
            self.snapshot_a.setCurrentIndex(1)
            self.snapshot_b.setCurrentIndex(0)
            self.compare()

    def return_to_live(self):
        if self.demo_owner:
            self.scan_timer.stop()
            self.io_timer.stop()
            self.connection_timer.stop()
            self.hide()
            owner=self.demo_owner
            owner.paused=getattr(owner,'paused_before_demo',False)
            owner.pause_button.setText(owner.t('resume' if owner.paused else 'pause'))
            owner.showNormal()
            owner.io_timer.start(2000)
            owner.connection_timer.start(7000)
            owner.activate_monitor()

    def change_language(self,code):
        self.repo.set_setting('language',code)
        self.i18n.set_language(code)

    def change_appearance(self,key,value):
        self.repo.set_setting(key,value)
        QTimer.singleShot(0,self.rebuild)

    def custom_accent(self):
        color=QColorDialog.getColor(QColor(self.repo.setting('accent','#5d92ff')),self,self.t('accent'))
        if color.isValid():
            self.change_appearance('accent',color.name())

    def setting_changed(self,key,value):
        if key=='autostart':
            try:
                from netscope.services.startup import set_autostart
                set_autostart(value)
            except OSError:
                self.toast.show_text(self.t('error'))
                return
        self.repo.set_setting(key,value)
        if key in ('interval','discovery'):
            self.activate_monitor()

    def populate_interfaces(self):
        if not hasattr(self,'interface_combo'):
            return
        self.interface_combo.blockSignals(True)
        self.interface_combo.clear()
        self.interface_combo.addItem(self.t('selected'),None)
        for i in self.interface_list:
            self.interface_combo.addItem(f'{i.name}  •  {i.ip}  /  {i.subnet}',i.to_dict())
        selected=next((n+1 for n,i in enumerate(self.interface_list) if self.interface and (i.name,i.ip)==(self.interface.name,self.interface.ip)),0)
        self.interface_combo.setCurrentIndex(selected)
        self.interface_combo.blockSignals(False)

    def select_interface(self,index):
        data=self.interface_combo.currentData()
        if not data:
            return
        if self.scanning:
            self.populate_interfaces()
            self.toast.show_text(self.t('loading'))
            return
        from netscope.models import Interface
        self.interface=Interface(**data)
        self.repo.set_setting('interface',data)
        self.last_io=None
        self.refresh()
        self.activate_monitor()

    def interfaces_ready(self,items):
        self.interface_list=items
        saved=self.repo.setting('interface',{})
        self.interface=next((i for i in items if (i.name,i.ip)==(saved.get('name'),saved.get('ip'))),items[0] if items else None)
        self.populate_interfaces()
        self.refresh()
        if not self.repo.setting('onboarded',False) and not self.smoke:
            self.onboarding()
        self.activate_monitor()

    def onboarding(self):
        dialog=QDialog(self)
        dialog.setWindowTitle('NetScope')
        dialog.setMinimumWidth(550)
        vl=QVBoxLayout(dialog)
        vl.addWidget(label(self.t('onboarding'),'title'))
        vl.addWidget(label(self.t('consent'),'muted'))
        combo=QComboBox()
        for i in self.interface_list:
            combo.addItem(f'{i.name} • {i.ip} • {i.subnet}',i)
        vl.addWidget(combo)
        allowed=QCheckBox(self.t('discovery'))
        vl.addWidget(allowed)
        interval=QSpinBox()
        interval.setRange(15,3600)
        interval.setValue(60)
        interval.setSuffix(' '+self.t('seconds'))
        form=QFormLayout()
        form.addRow(self.t('interval'),interval)
        vl.addLayout(form)
        notify=QCheckBox(self.t('notifications'))
        notify.setChecked(True)
        vl.addWidget(notify)
        vl.addWidget(self.button('save',dialog.accept,True))
        if dialog.exec()==QDialog.Accepted:
            self.interface=combo.currentData()
            if self.interface:
                self.repo.set_setting('interface',self.interface.to_dict())
            for k,v in [('onboarded',True),('discovery',allowed.isChecked()),('interval',interval.value()),('notifications',notify.isChecked())]:
                self.repo.set_setting(k,v)
            self.rebuild()

    def activate_monitor(self):
        if self.interface and not self.paused and (self.demo or self.repo.setting('discovery',False)):
            self.scan_timer.start(self.repo.setting('interval',60)*1000)
            if not self.smoke:
                self.scan()
        else:
            self.scan_timer.stop()

    def toggle_pause(self):
        self.paused=not self.paused
        self.pause_button.setText(self.t('resume' if self.paused else 'pause'))
        self.activate_monitor()

    def scan(self):
        if self.scanning or self.demo_generating:
            return
        if not self.interface:
            self.toast.show_text(self.t('no_interface'))
            return
        if not self.demo and not self.repo.setting('discovery',False):
            self.toast.show_text(self.t('consent'))
            self.navigate(8)
            return
        if not self.demo:
            try:
                scan_targets(self.interface.subnet)
            except ValueError:
                self.toast.show_text(self.t('subnet_hint'))
                return
        self.scanning=True
        self.scan_button.setEnabled(False)
        self.status_label.setText(self.t('loading'))
        if not self.repo.devices():
            for card in self.cards.values():
                card.set_loading(True)
        def finish():
            self.scanning=False
            self.scan_button.setEnabled(True)
            self.status_label.setText(self.t('ready'))
            for card in self.cards.values():
                card.set_loading(False)
            self.refresh()
        self.job(lambda:monitor(self.repo,self.interface,self.demo),self.scan_ready,finish)

    def scan_ready(self,events):
        self.last_scan=time.time()
        self.status_label.setToolTip(timestamp(self.last_scan))
        self.refresh()
        for e in events:
            if self.repo.setting('notifications',True) and (e['kind']=='new' or (e['kind']=='offline' and self.repo.setting('notify_offline',False))):
                text=self.t('new_device' if e['kind']=='new' else 'offline')+' • '+e['ip']
                self.toast.show_text(text)
                if not self.smoke:
                    self.tray.showMessage('NetScope'+(' DEMO' if self.demo else ''),text,QSystemTrayIcon.Information,5000)

    def refresh(self):
        self.refresh_devices()
        self.refresh_events()
        devices=self.repo.devices()
        current=[d for d in devices if self.interface and ipaddress.ip_address(d['ip']) in ipaddress.ip_network(self.interface.subnet)]
        self.cards['online'].value.setText(str(sum(d['online'] for d in current)))
        self.cards['unknown'].value.setText(str(sum(not d['trusted'] for d in current)))
        score=health(self.repo,self.interface) if self.interface else None
        self.cards['health'].value.setText(str(score) if score is not None else '—')
        if self.interface:
            i=self.interface
            self.interface_info.setText(f'{i.name}  •  {i.kind}\n\nIPv4  {i.ip}\n{i.subnet}\n\n{self.t("gateway")}  {i.gateway or "—"}\nDNS  {i.dns or "—"}\nIPv6  {i.ipv6 or "—"}')
            gateway=next((d for d in devices if d['ip']==i.gateway),None)
            self.gateway_chart.set_values([x['ms'] for x in self.repo.history(gateway['id'])] if gateway else [])
            net=ipaddress.ip_network(i.subnet)
            self.map.set_data(i,[d for d in devices if ipaddress.ip_address(d['ip']) in net])
        else:
            self.interface_info.setText(self.t('no_interface'))
        self.all_interfaces.setText('\n'.join(f'{i.name} • {i.ip} • {i.subnet} • {i.mac} • {i.kind}' for i in self.interface_list))
        for combo in (self.snapshot_a,self.snapshot_b):
            value=combo.currentData()
            combo.clear()
            for s in self.repo.snapshots():
                combo.addItem(timestamp(s['ts'])+' • '+s['label'],s['id'])
            if value:
                combo.setCurrentIndex(max(0,combo.findData(value)))
        if self.demo:
            self.show_demo_data()

    def fill(self,widget,rows,ids=None):
        widget.setSortingEnabled(False)
        widget.setRowCount(len(rows))
        for row,values in enumerate(rows):
            for col,value in enumerate(values):
                item=SortItem()
                item.setData(Qt.DisplayRole,value)
                if ids:
                    item.setData(Qt.UserRole,ids[row])
                widget.setItem(row,col,item)
        widget.setSortingEnabled(True)

    def refresh_devices(self,*_):
        if not hasattr(self,'devices_table'):
            return
        query=self.device_search.text().lower()
        mode=self.device_filter.currentData()
        rows,ids=[],[]
        availability_by_id,latency_by_id=self.repo.metrics()
        for d in self.repo.devices():
            if query and query not in ' '.join(str(d[k]) for k in ('ip','mac','hostname','name','tags','vendor')).lower():
                continue
            if (mode=='online' and not d['online']) or (mode=='offline' and d['online']) or (mode=='unknown' and d['trusted']) or (mode=='trusted' and not d['trusted']) or (mode=='favorite' and not d['favorite']):
                continue
            latency=latency_by_id.get(d['id'])
            availability=availability_by_id.get(d['id'])
            rows.append([('★ ' if d['favorite'] else '')+(d['name'] or d['hostname'] or self.t('device')),
                         self.t('online' if d['online'] else 'offline'),d['ip'],d['mac'] or '—',self.t(d['kind']),
                         f'{latency:.1f} ms' if latency is not None else '—',f'{availability:.1f}%' if availability is not None else '—',self.t('trusted' if d['trusted'] else 'unknown')])
            ids.append(d['id'])
        self.fill(self.devices_table,rows,ids)
        self.devices_empty.setVisible(not rows)

    def refresh_events(self,*_):
        if not hasattr(self,'event_table'):
            return
        events=self.repo.events()
        query=self.event_search.text().lower()
        rows=[[timestamp(e['ts']),e['name'],self.t(e['kind']),e['detail']] for e in events if not query or query in (e['name']+' '+e['detail']+' '+self.t(e['kind'])).lower()]
        self.fill(self.event_table,rows)
        self.fill(self.overview_events,[[timestamp(e['ts']),e['name'],self.t(e['kind'])] for e in events[:8]])

    def selected_device(self):
        item=self.devices_table.item(self.devices_table.currentRow(),0)
        return next((d for d in self.repo.devices() if item and d['id']==item.data(Qt.UserRole)),None)

    def device_menu(self,pos):
        item=self.devices_table.itemAt(pos)
        if not item:
            return
        self.devices_table.selectRow(item.row())
        d=self.selected_device()
        if not d:
            return
        menu=QMenu(self)
        menu.addAction(self.t('details'),self.open_selected)
        for key in ('trusted','favorite'):
            menu.addAction(self.t(key),lambda checked=False,k=key:self.edit_flag(d,k))
        menu.exec(self.devices_table.viewport().mapToGlobal(pos))

    def edit_flag(self,d,key):
        self.repo.update_device(d['id'],**{key:int(not d[key])})
        self.refresh()

    def open_selected(self,*_):
        d=self.selected_device()
        if d:
            self.device_detail(d)

    def device_detail(self,d):
        dialog=QDialog(self)
        dialog.setWindowTitle(self.t('details'))
        dialog.resize(780,800)
        outer=QVBoxLayout(dialog)
        content=QWidget()
        content.setObjectName('page')
        vl=QVBoxLayout(content)
        vl.addWidget(label(d['name'] or d['hostname'] or d['ip'],'title'))
        vl.addWidget(label(self.t('online' if d['online'] else 'offline'),'badge'))
        form=QFormLayout()
        name=QLineEdit(d['name'])
        tags=QLineEdit(d['tags'])
        kind=QComboBox()
        for k in KINDS:
            kind.addItem(self.t(k),k)
        kind.setCurrentIndex(kind.findData(d['kind']))
        trusted,favorite=QCheckBox(self.t('trusted')),QCheckBox(self.t('favorite'))
        trusted.setChecked(bool(d['trusted']))
        favorite.setChecked(bool(d['favorite']))
        for k,w in [('name',name),('type',kind),('tags',tags)]:
            form.addRow(self.t(k),w)
        form.addRow(trusted,favorite)
        for k,v in [('ipv4',d['ip']),('mac',d['mac']),('hostname',d['hostname']),('vendor',d['vendor']),('first_seen',timestamp(d['first_seen'])),('last_seen',timestamp(d['last_seen']))]:
            form.addRow(self.t(k),label(v or '—'))
        vl.addLayout(form)
        h=self.repo.history(d['id'])
        availability=self.repo.availability(d['id'])
        loss=100*sum(not x['online'] for x in h)/len(h) if h else None
        vl.addWidget(label(self.t('availability')+f'  {availability:.1f}%' if availability is not None else self.t('availability')+' —','badge'))
        vl.addWidget(label(self.t('loss')+(f'  {loss:.1f}%' if loss is not None else ' —'),'badge'))
        vl.addWidget(label(self.t('availability_hint'),'muted'))
        chart=SparkChart()
        chart.set_values([x['ms'] for x in h])
        vl.addWidget(label(self.t('latency')+' / ms','badge'))
        vl.addWidget(chart)
        notes=QTextEdit(self.repo.note(d['id']))
        notes.setMaximumHeight(110)
        vl.addWidget(label(self.t('notes'),'badge'))
        vl.addWidget(notes)
        timeline=table([self.t('last_seen'),self.t('status')])
        self.fill(timeline,[[timestamp(e['ts']),self.t(e['kind'])] for e in self.repo.events(d['id'],30)])
        timeline.setMinimumHeight(180)
        vl.addWidget(timeline)
        ports_output=label('','muted')
        port_button=self.button('port_check',lambda:self.ports(d,ports_output,port_button))
        vl.addWidget(label(self.t('port_hint'),'muted'))
        vl.addWidget(port_button)
        vl.addWidget(ports_output)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        row=QHBoxLayout()
        def save():
            self.repo.update_device(d['id'],name=name.text().strip(),kind=kind.currentData(),tags=tags.text().strip(),trusted=int(trusted.isChecked()),favorite=int(favorite.isChecked()))
            self.repo.note(d['id'],notes.toPlainText())
            self.refresh()
            dialog.accept()
        row.addWidget(self.button('close',dialog.reject))
        row.addWidget(self.button('save',save,True))
        outer.addLayout(row)
        dialog.exec()

    def ports(self,d,output,button):
        if self.demo:
            output.setText('DEMO • '+self.t('ports_open')+': 80, 443')
            return
        if not self.interface or self.port_busy or time.monotonic()-self.port_last<15:
            self.toast.show_text(self.t('loading'))
            return
        self.port_busy=True
        self.port_last=time.monotonic()
        button.setEnabled(False)
        output.setText(self.t('loading'))
        def ready(rows):
            from shiboken6 import isValid
            if isValid(output):
                output.setText('\n'.join(f'{p} • {self.t("ports_open" if opened else "ports_closed")}' for p,opened in rows))
        def finish():
            self.port_busy=False
            from shiboken6 import isValid
            if isValid(button):
                button.setEnabled(True)
        self.job(lambda:check_ports(d['ip'],self.interface.subnet,consent=True),ready,finish)

    def sample_io(self):
        if not self.interface or self.traffic_busy:
            return
        self.traffic_busy=True
        iface=self.interface.name
        def work():
            now=time.monotonic()
            if self.demo:
                rx,tx=7+6*math.sin(now/8),1.4+math.sin(now/12)
            else:
                c=psutil.net_io_counters(pernic=True).get(iface)
                if not c:
                    return None
                previous=self.last_io
                self.last_io=(now,c.bytes_recv,c.bytes_sent)
                if not previous:
                    return None
                elapsed=max(now-previous[0],0.01)
                rx=max(0,c.bytes_recv-previous[1])*8/elapsed/1e6
                tx=max(0,c.bytes_sent-previous[2])*8/elapsed/1e6
            self.repo.traffic(iface,rx,tx)
            return rx,tx,self.repo.traffic_history(iface)
        def ready(result):
            if not result:
                return
            self.rx,self.tx,rows=result
            self.rx_card.value.setText(f'{self.rx:.2f}')
            self.tx_card.value.setText(f'{self.tx:.2f}')
            self.cards['download'].value.setText(f'{self.rx:.2f}')
            self.rx_chart.set_values([r['rx'] for r in rows])
            self.tx_chart.set_values([r['tx'] for r in rows])
        self.job(work,ready,lambda:setattr(self,'traffic_busy',False))

    def refresh_connections(self):
        if self.demo or self.connection_busy or self.smoke:
            return
        self.connection_busy=True
        def ready(result):
            self.connection_rows,allowed=result
            self.connection_status.setText('' if allowed else self.t('access_hint'))
            self.filter_connections()
        self.job(local_connections,ready,lambda:setattr(self,'connection_busy',False))

    def filter_connections(self,*_):
        query=self.connection_search.text().lower()
        mode=self.connection_filter.currentText()
        rows=[]
        for r in self.connection_rows:
            if query and query not in ' '.join(map(str,r.values())).lower():
                continue
            if self.connection_filter.currentIndex() and mode not in (r['status'],r['protocol']):
                continue
            rows.append([r[k] for k in ('protocol','local','remote','status','pid','process')])
        self.fill(self.connection_table,rows)

    def run_diagnostics(self):
        if not self.interface:
            self.toast.show_text(self.t('no_interface'))
            return
        self.diagnostic_button.setEnabled(False)
        def ready(rows):
            self.fill(self.diagnostic_table,[[self.t(k),self.t('passed' if ok else 'failed' if ok is False else 'skipped'),detail] for k,ok,detail in rows])
        self.job(lambda:self.repo.setting('demo_diagnostics',None) or diagnostics(self.interface,True) if self.demo else diagnostics(self.interface,False),ready,lambda:self.diagnostic_button.setEnabled(True))

    def export_devices(self):
        path,_=QFileDialog.getSaveFileName(self,self.t('export'),'NetScope-devices'+('-DEMO' if self.demo else '')+'.csv','CSV (*.csv);;JSON (*.json)')
        if path:
            self.job(lambda:export(path,[dict(d,mode='DEMO' if self.demo else 'LIVE') for d in self.repo.devices()]),lambda _:self.toast.show_text(self.t('saved')))

    def export_history(self):
        path,_=QFileDialog.getSaveFileName(self,self.t('export'),'NetScope-history'+('-DEMO' if self.demo else '')+'.json','JSON (*.json);;CSV (*.csv)')
        if path:
            def work():
                data=self.repo.export_history()
                data['mode']='DEMO' if self.demo else 'LIVE'
                if path.lower().endswith('.csv'):
                    from netscope.services.reporting import history_rows
                    export(path,history_rows(data,self.demo))
                else:
                    export(path,data)
            self.job(work,lambda _:self.toast.show_text(self.t('saved')))

    def export_report(self):
        path,_=QFileDialog.getSaveFileName(self,self.t('report'),'NetScope-report'+('-DEMO' if self.demo else '')+'.html','HTML (*.html)')
        if path:
            from netscope.services.reporting import html_report
            title=self.t('report')
            headers=[self.t(k) for k in ('name','ipv4','status','trusted','availability')]
            status={k:self.t(k) for k in ('online','offline','trusted','unknown')}
            self.job(lambda:html_report(path,self.repo,self.demo,title,headers,status),lambda _:self.toast.show_text(self.t('saved')))

    def save_snapshot(self):
        self.repo.snapshot(('DEMO • ' if self.demo else '')+timestamp(time.time()))
        self.refresh()
        self.toast.show_text(self.t('saved'))

    def compare(self):
        snapshots={s['id']:json.loads(s['data']) for s in self.repo.snapshots()}
        a,b=self.snapshot_a.currentData(),self.snapshot_b.currentData()
        if a not in snapshots or b not in snapshots:
            self.toast.show_text(self.t('empty'))
            return
        diff=compare_snapshots(snapshots[a],snapshots[b])
        rows=[]
        for key,items in diff.items():
            for item in items:
                d=item['after'] if key=='changed' else item
                details=''
                if key=='changed':
                    details=', '.join(self.t('ipv4' if f=='ip' else 'status' if f=='online' else 'type' if f=='kind' else f)+': '+str(item['before'].get(f))+' → '+str(d.get(f)) for f in ('ip','online','name','trusted','tags','kind') if item['before'].get(f)!=d.get(f))
                rows.append([self.t(key),d['name'] or d['hostname'],d['ip'],details])
        self.fill(self.comparison,rows)

    def palette(self):
        dialog=QDialog(self)
        dialog.setWindowTitle(self.t('search'))
        dialog.resize(540,430)
        vl=QVBoxLayout(dialog)
        search=QLineEdit()
        search.setPlaceholderText(self.t('search')+' • Ctrl+K')
        vl.addWidget(search)
        items=QListWidget()
        vl.addWidget(items)
        commands=[(self.t(k),lambda index=i:self.navigate(index)) for i,k in enumerate(PAGES)]
        commands += [(self.t('scan'),self.scan),(self.t('pause'),self.toggle_pause),(self.t('export'),self.export_devices)]
        for d in self.repo.devices():
            commands.append((f'{d["name"] or d["hostname"] or self.t("device")} • {d["ip"]}',lambda device=d:self.device_detail(device)))
        current=[]
        def filtered(text):
            items.clear()
            current.clear()
            for name,action in commands:
                if text.lower() in name.lower():
                    items.addItem(name)
                    current.append(action)
            if current:
                items.setCurrentRow(0)
        def execute(*_):
            index=items.currentRow()
            if 0<=index<len(current):
                action=current[index]
                dialog.accept()
                action()
        search.textChanged.connect(filtered)
        search.returnPressed.connect(execute)
        items.itemActivated.connect(execute)
        filtered('')
        search.setFocus()
        dialog.exec()

    def closeEvent(self,event):
        if self.demo_owner and not self.demo_owner.allow_quit:
            self.return_to_live()
            event.ignore()
            return
        if not self.allow_quit and self.repo.setting('tray',True) and self.tray.isVisible() and not self.smoke:
            self.hide()
            event.ignore()
        else:
            self.scan_timer.stop()
            self.io_timer.stop()
            self.connection_timer.stop()
            self.pool.waitForDone(60000)
            self.tray.hide()
            event.accept()

    def quit(self):
        self.allow_quit=True
        if self.demo_window:
            self.demo_window.allow_quit=True
            self.demo_window.close()
        self.close()
