from PyQt6.QtCore import QThread

class WorkerThread(QThread):
    def __init__(self, worker):
        super().__init__()
        self.worker = worker

    def run(self):
        self.worker.run()