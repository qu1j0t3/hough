import logging
import logging.config
import logging.handlers
import signal
import sys
import traceback
from multiprocessing import Manager, Process


def setup_queue_logging(q):
    h = logging.handlers.QueueHandler(q)
    root = logging.getLogger()
    root.addHandler(h)
    root.setLevel(logging.DEBUG)


def start_logger_process(log_level, results_file):
    logq = Manager().Queue(-1)
    listener = Process(target=_logger_process, args=(logq, log_level, results_file))
    listener.start()
    return logq, listener


def _logger_process(q, log_level, results_file):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    _setup_logger_process_logging(log_level, results_file)
    try:
        while True:
            record = q.get()
            if record is None:
                break
            logger = logging.getLogger(record.name)
            logger.handle(record)
    except EOFError:
        # print("Logger EOFError, aborting...", file=sys.stderr)
        pass
    except Exception:
        print("Exception in logger process:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


def _setup_logger_process_logging(log_level, results_file):
    logd = {
        "version": 1,
        "formatters": {
            "detailed": {
                "class": "logging.Formatter",
                "format": "%(asctime)s %(name)-8s %(levelname)-8s %(processName)-25s %(message)s",
            },
            "raw": {"class": "logging.Formatter", "format": "%(message)s"},
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "level": log_level},
            "file": {
                "class": "logging.FileHandler",
                "filename": "hough.log",
                "mode": "a",
                "formatter": "detailed",
                "level": logging.DEBUG,
            },
            "csv": {
                "class": "logging.FileHandler",
                "filename": results_file,
                "mode": "a",
                "formatter": "raw",
            },
        },
        "loggers": {
            "csv": {"handlers": ["csv"]},
            "hough": {"handlers": ["file", "console"]},
        },
        "root": {"level": logging.DEBUG, "handlers": []},
    }
    logging.config.dictConfig(logd)
