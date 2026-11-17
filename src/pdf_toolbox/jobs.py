from collections.abc import Callable
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from .pdf import Cancelled


class JobSignals(QObject):
    progress = Signal(int, int)
    finished = Signal(object, object)


class Job(QRunnable):
    def __init__(self, run: Callable):
        super().__init__()
        self.run_job = run
        self.cancel = Event()
        self.signals = JobSignals()

    @Slot()
    def run(self):
        try:
            result = self.run_job(self.cancel, self.signals.progress.emit)
        except Exception as error:
            self.signals.finished.emit(None, error)
        else:
            self.signals.finished.emit(result, None)


class Jobs(QObject):
    """Keep callbacks on the Qt thread and retain job signals until delivery."""

    def __init__(self, parent=None, threads=2):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(threads)
        self.active: dict[JobSignals, tuple[Job, Callable]] = {}

    def submit(self, work, done, progress=None):
        job = Job(work)
        self.active[job.signals] = job, done
        job.signals.finished.connect(self.finish)
        if progress:
            job.signals.progress.connect(progress)
        self.pool.start(job)
        return job.cancel

    @Slot(object, object)
    def finish(self, result, error):
        _, done = self.active.pop(self.sender())
        done(result, error)

    def cancel_all(self):
        for job, _ in self.active.values():
            job.cancel.set()


def message_for(error):
    if isinstance(error, Cancelled):
        return "Cancelled. No output files were saved."
    if isinstance(error, (ValueError, FileExistsError)) and error.args:
        if type(error) in {ValueError, FileExistsError} and len(error.args) == 1:
            return str(error)
    if isinstance(error, PermissionError):
        return "Access was denied. Choose a folder you can write to."
    if isinstance(error, OSError):
        return "The file could not be read or saved. Check access and available disk space."
    return "The PDF could not be processed. Check that the file opens in a PDF reader."
