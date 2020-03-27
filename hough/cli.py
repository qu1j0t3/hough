#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#    This file is part of "hough", which detects skew angles in scanned images
#    Copyright (C) 2016-2020 Toby Thain, toby@telegraphics.com.au
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""hough - straighten scanned pages using the Hough transform.

Usage:
  hough (-h | --help)
  hough [options] <file>...

Arguments:
  file                          Input file(s) to process

Options:
  -h --help                     Display this help and exit
  -v --verbose                  print status messages
  -d --debug                    retain debug image output in out/ directory
                                (also enables --verbose)
  --version                     Display the version number and exit
  -c --csv                      Save rotation results in CSV format
  --results=<file>              Save rotation results to named file.
                                Extension comes from format (.csv, ...)
                                [default: results]
  --histogram                   Display rotation angle histogram summary
                                (implies --csv)
  -j <jobs> --jobs=<jobs>       Specify the number of jobs to run
                                simultaneously. Default: total # of CPUs
"""

import datetime
import logging
import logging.config
import logging.handlers
import os
import threading
from multiprocessing import Pool, Queue, cpu_count

import filetype
import fitz
from docopt import docopt

import hough

from . import process
from .stats import histogram


def _logger_thread(q):
    while True:
        record = q.get()
        if record is None:
            break
        # this avoids double-logging
        if record.name == "worker_csv":
            record.name = "csv"
        elif record.name == "worker_hough":
            record.name = "hough"
        logger = logging.getLogger(record.name)
        logger.handle(record)


def _setup_logging(log_level, results_file):
    logq = Queue()
    logd = {
        "version": 1,
        "formatters": {
            "detailed": {
                "class": "logging.Formatter",
                "format": "%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s",
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
    lp = threading.Thread(target=_logger_thread, args=(logq,))
    lp.start()
    return logq, lp


def run():
    arguments = docopt(__doc__, version=hough.__version__, more_magic=True)

    if arguments.debug:
        arguments["verbose"] = True
        log_level = logging.DEBUG
    elif arguments.verbose:
        log_level = logging.INFO
    else:
        log_level = logging.WARNING
    results_file = arguments.results + ".csv"
    arguments["now"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    if arguments.histogram:
        arguments["csv"] = True
    if arguments.jobs:
        jobs = int(arguments.jobs)
    else:
        jobs = cpu_count()

    logq, lp = _setup_logging(log_level, results_file)
    logger = logging.getLogger("hough")
    logger.info(f"=== Run started @ {arguments.now} ===")
    if arguments.csv:
        logger_csv = logging.getLogger("csv")
        if not os.path.exists(results_file) or os.path.getsize(results_file) == 0:
            logger_csv.info(
                '"Input File","Page Number","Computed angle","Variance of computed angles","Image width (px)","Image height (px)"'
            )

    if arguments.debug and not os.path.isdir(f"out/{arguments.now}"):
        os.makedirs(f"out/{arguments.now}")

    # the pool that launched 1,000 Houghs...
    try:
        pool = Pool(jobs, initializer=process._init_worker, initargs=(logq, arguments,))
        results = []
        for f in arguments.file:
            kind = filetype.guess(f)
            # TODO: Handle multi-page TIFFs here as well
            if kind.mime == "application/pdf":
                pdf = fitz.open(f)
                for page in range(len(pdf)):
                    results.append(
                        pool.apply_async(process.process_page, (f, page, kind.mime))
                    )
            else:
                results.append(pool.apply_async(process.process_file, (f,)))
        pool.close()
        for x in results:
            res = x.get()
            if arguments.debug:
                logger.debug(res)
        if arguments.histogram:
            histogram(results_file)

    except KeyboardInterrupt:
        pool.terminate()
        pool.join()

    # end logging thread
    logq.put(None)
    lp.join()

    logger.info(f"=== Run ended @ {datetime.datetime.utcnow().isoformat()} ===")
    exit(0)


if __name__ == "__main__":
    run()
