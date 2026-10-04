import argparse
import logging
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from netscope.utils.paths import data_dir
from netscope.repositories.database import Repository
from netscope.ui.window import Window


def main(argv=None):
    parser=argparse.ArgumentParser(description='NetScope local network monitor')
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--demo-records',action='store_true',help='Open an isolated demo and generate randomized records for all pages')
    parser.add_argument('--smoke-test',action='store_true',help='Isolated DEMO startup, no live network access; quits after 3 seconds')
    parser.add_argument('--data-dir',type=Path,help='Explicit local data location (DEMO still uses its own child directory)')
    parser.add_argument('--screenshot',type=Path,help='Save startup screenshot during smoke test')
    args=parser.parse_args(argv)
    demo=args.demo or args.demo_records or args.smoke_test
    root=(args.data_dir/('demo' if demo else 'live')) if args.data_dir else data_dir(demo)
    root.mkdir(parents=True,exist_ok=True)
    handler=RotatingFileHandler(root/'netscope.log',maxBytes=1_000_000,backupCount=3,encoding='utf-8')
    logging.basicConfig(handlers=[handler],level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    app=QApplication(sys.argv[:1])
    app.setApplicationName('NetScope')
    app.setOrganizationName('NetScope')
    app.setStyle('Fusion')
    repo=Repository(root/'netscope.db',mode='demo' if demo else 'live')
    repo.cleanup(repo.setting('retention',30))
    window=Window(repo,demo,args.smoke_test)
    window.show()
    if args.demo_records:
        QTimer.singleShot(0,window.generate_demo)
    if args.smoke_test:
        if args.demo_records:
            def demo_ready():
                if args.screenshot:
                    QTimer.singleShot(200,lambda:window.grab().save(str(args.screenshot)))
                QTimer.singleShot(500,window.quit)
            window.demo_populated.connect(demo_ready)
            QTimer.singleShot(25000,window.quit)
        else:
            if args.screenshot:
                QTimer.singleShot(2200,lambda:window.grab().save(str(args.screenshot)))
            QTimer.singleShot(3000,window.quit)
    result=app.exec()
    if args.smoke_test and args.demo_records and not window.demo_generation_succeeded:
        return 1
    return result
