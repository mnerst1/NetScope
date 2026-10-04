from PySide6.QtCore import Qt, QTimer, QPropertyAnimation
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsOpacityEffect, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView


class SortItem(QTableWidgetItem):
    def __lt__(self,other):
        import ipaddress
        def key(item):
            text=item.text().strip()
            try:
                return (0,int(ipaddress.ip_address(text)))
            except ValueError:
                pass
            try:
                return (1,float(text.rstrip('%').removesuffix(' ms')))
            except ValueError:
                return (2,text.casefold())
        return key(self)<key(other)


def label(text, name=''):
    w=QLabel(text)
    if name:
        w.setObjectName(name)
    w.setWordWrap(True)
    return w


class Card(QFrame):
    def __init__(self,title,value,caption=''):
        super().__init__()
        self.setObjectName('card')
        layout=QVBoxLayout(self)
        layout.setContentsMargins(20,18,20,18)
        layout.addWidget(label(title,'muted'))
        self.value=label(value,'metric')
        layout.addWidget(self.value)
        layout.addWidget(label(caption,'muted'))
        self.effect=QGraphicsOpacityEffect(self.value)
        self.value.setGraphicsEffect(self.effect)
        self.pulse=QPropertyAnimation(self.effect,b'opacity',self)
        self.pulse.setDuration(850)
        self.pulse.setStartValue(0.25)
        self.pulse.setEndValue(0.85)
        self.pulse.setLoopCount(-1)

    def set_loading(self,enabled):
        if enabled:
            self.value.setText('···')
            self.pulse.start()
        else:
            self.pulse.stop()
            self.effect.setOpacity(1.)


def table(headers):
    w=QTableWidget(0,len(headers))
    w.setHorizontalHeaderLabels(headers)
    w.setAlternatingRowColors(True)
    w.setShowGrid(False)
    w.verticalHeader().hide()
    w.setSelectionBehavior(QAbstractItemView.SelectRows)
    w.setSelectionMode(QAbstractItemView.SingleSelection)
    w.setEditTriggers(QAbstractItemView.NoEditTriggers)
    w.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    w.verticalHeader().setDefaultSectionSize(44)
    w.setSortingEnabled(True)
    return w


class Toast(QLabel):
    def __init__(self,parent):
        super().__init__(parent)
        self.setObjectName('toast')
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.hide()
        self.timer=QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide)
        self.effect=QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.animation=QPropertyAnimation(self.effect,b'opacity',self)
        self.animation.setDuration(160)

    def show_text(self,text):
        self.setText(text)
        self.setGeometry(max(20,self.parent().width()-440),24,410,64)
        self.show()
        self.raise_()
        self.animation.setStartValue(0.)
        self.animation.setEndValue(1.)
        self.animation.start()
        self.timer.start(6500)
