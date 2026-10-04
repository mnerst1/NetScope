import logging
from PySide6.QtCore import QObject, Signal, QRunnable, Slot


class Signals(QObject):
    result = Signal(object)
    error = Signal(str)
    finished = Signal()


class Task(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = Signals()

    @Slot()
    def run(self):
        try:
            self.signals.result.emit(self.function())
        except Exception as e:
            logging.exception('Background operation failed')
            self.signals.error.emit(type(e).__name__)
        finally:
            self.signals.finished.emit()
