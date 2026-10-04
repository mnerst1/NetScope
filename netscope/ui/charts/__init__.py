import math
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QLinearGradient
from PySide6.QtWidgets import QWidget


class SparkChart(QWidget):
    def __init__(self, parent=None, color='#5d92ff'):
        super().__init__(parent)
        self.values = []
        self.color = color
        self.setMinimumHeight(150)
        self.setMinimumWidth(260)

    def set_values(self, values):
        self.values = list(values)[-180:]
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(42,16,-18,-25)
        valid = [v for v in self.values if v is not None]
        ymax = max(max(valid,default=1)*1.15,1)
        p.setPen(QColor('#71819c'))
        for i in range(5):
            y = rect.top()+rect.height()*i/4
            p.setPen(QPen(QColor(120,140,165,35),1))
            p.drawLine(QPointF(rect.left(),y),QPointF(rect.right(),y))
            p.setPen(QColor('#71819c'))
            p.drawText(QRectF(0,y-8,36,16),Qt.AlignRight,f'{ymax*(4-i)/4:.0f}')
        if len(self.values)<2:
            return
        path = QPainterPath()
        active = False
        for i,v in enumerate(self.values):
            x = rect.left()+rect.width()*i/(len(self.values)-1)
            if v is None:
                active = False
                continue
            point = QPointF(x,rect.bottom()-rect.height()*v/ymax)
            if active:
                path.lineTo(point)
            else:
                path.moveTo(point)
            active = True
        p.setPen(QPen(QColor(self.color),2.5))
        p.drawPath(path)


class NetworkMap(QWidget):
    def __init__(self, i18n):
        super().__init__()
        self.i18n = i18n
        self.devices = []
        self.interface = None
        self.setMinimumHeight(360)

    def set_data(self, interface, devices):
        self.interface,self.devices = interface,devices
        self.update()

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.interface:
            return
        w,h=self.width(),self.height()
        root=QPointF(w/2,75)
        pc=QPointF(w/2,190)
        peers=[d for d in self.devices if d['ip'] not in (self.interface.ip,self.interface.gateway)][:16]
        p.setPen(QPen(QColor('#526a91'),1.5,Qt.DashLine))
        if self.interface.gateway:
            p.drawLine(root,pc)
        points=[]
        for i,d in enumerate(peers):
            row=i//8
            n=min(8,len(peers)-row*8)
            point=QPointF((i%8+1)*w/(n+1),310+row*115)
            points.append((point,d))
            p.drawLine(pc,point)
        def node(point,title,subtitle,online=True):
            p.setBrush(QColor('#1e314e' if online else '#343947'))
            p.setPen(QPen(QColor('#5d92ff' if online else '#6d7584'),2))
            p.drawEllipse(point,22,22)
            p.setPen(QColor('#6e89af'))
            p.drawText(QRectF(point.x()-75,point.y()+27,150,22),Qt.AlignCenter,title[:24])
            p.drawText(QRectF(point.x()-75,point.y()+49,150,18),Qt.AlignCenter,subtitle)
        if self.interface.gateway:
            node(root,self.i18n.t('gateway'),self.interface.gateway)
        node(pc,self.i18n.t('current_pc'),self.interface.ip)
        for point,d in points:
            node(point,d['name'] or d['hostname'] or self.i18n.t(d['kind']),d['ip'],d['online'])
