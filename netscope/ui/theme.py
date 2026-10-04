ACCENTS={'Blue':'#5d92ff','Violet':'#a383ff','Cyan':'#39c5dc','Green':'#3dcc9d','Orange':'#efa45d','Red':'#f16b79','Pink':'#e882cc'}


def palette(theme,system_dark=True):
    from PySide6.QtGui import QPalette,QColor
    dark=theme=='dark' or (theme=='system' and system_dark)
    p=QPalette()
    for role,color in ((QPalette.Window,'#0b1019' if dark else '#f3f5fa'),
                       (QPalette.Base,'#141d2b' if dark else '#ffffff'),
                       (QPalette.AlternateBase,'#0b1019' if dark else '#f3f5fa'),
                       (QPalette.Button,'#141d2b' if dark else '#ffffff'),
                       (QPalette.Text,'#e7edf7' if dark else '#18243a'),
                       (QPalette.WindowText,'#e7edf7' if dark else '#18243a'),
                       (QPalette.ButtonText,'#e7edf7' if dark else '#18243a'),
                       (QPalette.Highlight,'#5d92ff'),(QPalette.HighlightedText,'#08111f')):
        p.setColor(role,QColor(color))
    return p


def stylesheet(theme, style, accent, system_dark=True):
    from netscope.utils.paths import asset
    down=asset('chevron.svg').as_posix()
    up=asset('chevron-up.svg').as_posix()
    check=asset('check.svg').as_posix()
    dark = theme=='dark' or (theme=='system' and system_dark)
    bg = '#0b1019' if dark else '#f3f5fa'
    panel = '#141d2b' if dark else '#ffffff'
    text = '#e7edf7' if dark else '#18243a'
    muted = '#8595ad' if dark else '#61718a'
    border = '#26344a' if dark else '#dce3ef'
    if style=='oled' and dark:
        bg,panel='#000000','#0b0b0c'
    if style=='graphite' and dark:
        bg,panel,border='#16171b','#202227','#363941'
    radius=4 if style in ('minimal','compact') else 14
    size=12 if style=='compact' else 13
    if style=='glass':
        border='#456082' if dark else '#bacbe3'
    return f'''
    QWidget {{ color:{text}; font-family:'Segoe UI'; font-size:{size}px; }}
    QMainWindow,QDialog {{ background:{bg}; }}
    QScrollArea,QStackedWidget {{ background:transparent; border:none; }}
    QWidget#page {{ background:{bg}; }}
    QFrame#sidebar {{ background:{panel}; border-right:1px solid {border}; }}
    QFrame#card,QFrame#panel {{ background:{panel}; border:1px solid {border}; border-radius:{radius}px; }}
    QLabel#title {{ font-size:28px; font-weight:650; }}
    QLabel#brand {{ font-size:23px; font-weight:700; }}
    QLabel#metric {{ font-size:34px; font-weight:650; }}
    QLabel#muted {{ color:{muted}; }}
    QLabel#badge {{ color:{accent}; background:{panel}; border:1px solid {border}; border-radius:8px; padding:6px; }}
    QPushButton {{ background:{panel}; border:1px solid {border}; border-radius:8px; padding:9px 14px; }}
    QPushButton:hover {{ border-color:{accent}; }}
    QPushButton:checked,QPushButton#primary {{ background:{accent}; color:#08111f; font-weight:600; }}
    QPushButton:disabled {{ color:{muted}; }}
    QPushButton#nav {{ text-align:left; border:none; padding:12px 16px; }}
    QLineEdit,QTextEdit,QComboBox,QSpinBox {{ background:{panel}; border:1px solid {border}; border-radius:7px; padding:8px; selection-background-color:{accent}; }}
    QComboBox QAbstractItemView {{ background:{panel}; selection-background-color:{accent}; }}
    QTableWidget {{ background:{panel}; alternate-background-color:{bg}; border:1px solid {border}; border-radius:10px; selection-background-color:{border}; }}
    QHeaderView::section {{ background:{panel}; color:{muted}; padding:12px 6px; border:none; border-bottom:1px solid {border}; }}
    QTableWidget::item {{ padding:6px; border:none; }}
    QListWidget {{ background:{panel}; border:1px solid {border}; border-radius:8px; }}
    QListWidget::item {{ padding:12px; }}
    QListWidget::item:selected {{ background:{border}; }}
    QComboBox::drop-down {{ border:none; width:24px; }}
    QComboBox::down-arrow {{ image:url("{down}"); width:14px; height:14px; }}
    QSpinBox::up-button {{ subcontrol-origin:border; subcontrol-position:top right; width:24px; border:none; }}
    QSpinBox::down-button {{ subcontrol-origin:border; subcontrol-position:bottom right; width:24px; border:none; }}
    QSpinBox::up-arrow {{ image:url("{up}"); width:12px; height:12px; }}
    QSpinBox::down-arrow {{ image:url("{down}"); width:12px; height:12px; }}
    QCheckBox {{ spacing:9px; }}
    QCheckBox::indicator {{ width:18px; height:18px; border:1px solid {border}; border-radius:5px; background:{panel}; }}
    QCheckBox::indicator:checked {{ background:{accent}; image:url("{check}"); }}
    QMenu {{ background:{panel}; border:1px solid {border}; padding:5px; }}
    QMenu::item {{ padding:8px 20px; }}
    QMenu::item:selected {{ background:{border}; }}
    QLabel#toast {{ background:{panel}; color:{text}; border:1px solid {accent}; border-radius:12px; padding:12px; }}
    QToolTip {{ background:{panel}; color:{text}; border:1px solid {accent}; }}
    QScrollBar:vertical {{ width:8px; background:{bg}; }}
    QScrollBar::handle:vertical {{ background:{border}; border-radius:4px; min-height:24px; }}
    QScrollBar:horizontal {{ height:8px; background:{bg}; }}
    QScrollBar::handle:horizontal {{ background:{border}; border-radius:4px; min-width:24px; }}
    '''
