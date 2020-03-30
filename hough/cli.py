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
  -d --debug                    retain debug image output in debug/ directory
                                (also enables --verbose)
  --version                     Display the version number and exit
  -c --csv                      Save rotation results in CSV format
  --results=<file>              Save rotation results to named file.
                                Extension comes from format (.csv, ...)
                                [default: results]
  --histogram                   Display rotation angle histogram summary
                                (implies --csv)
  -w <workers> --workers=<#>    Specify the number of workers to run
                                simultaneously. Default: total # of CPUs
"""

import datetime
import logging
import os
import sys
import time
from multiprocessing import Pool, cpu_count, freeze_support

from docopt import docopt
from tqdm import tqdm

import hough

from . import log_utils, process
from .stats import histogram


def _abort(pool=None, log_queue=None, listener=None):
    try:
        if pool:
            pool.close()
            pool.terminate()
            pool.join()
            # this lets the producers drain their log queues
            time.sleep(0.1)
        if log_queue and listener:
            print(
                f"=== Run killed @ {datetime.datetime.utcnow().isoformat()} ===",
                file=sys.stderr,
            )
            try:
                log_queue.put(None)
                listener.join()
            except Exception:
                pass
    except Exception:
        import traceback

        print("Exception during abort:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


def run(argv=sys.argv[1:]):
    arguments = docopt(__doc__, argv=argv, version=hough.__version__, more_magic=True)

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
    if arguments.workers:
        workers = int(arguments.workers)
    else:
        workers = cpu_count()
    pbar_disable = arguments.quiet or arguments.verbose or arguments.debug

    if arguments.debug and not os.path.isdir(f"debug/{arguments.now}"):
        os.makedirs(f"debug/{arguments.now}")

    logq, listener = log_utils.start_logger_process(log_level, results_file)

    results = []

    # The pool that launched 1,000 Houghs...
    # We do it this way, not with a map, until https://github.com/tqdm/tqdm/issues/548 is fixed
    with Pool(
        processes=workers,
        initializer=process._init_worker,
        initargs=(logq, arguments.debug, arguments.now,),
    ) as p:
        try:
            pages = []
            for f in arguments.file:
                pages += process.get_pages(f)

            log_utils.setup_queue_logging(logq)
            logger = logging.getLogger("hough")
            logger.info(
                f"=== Run started @ {datetime.datetime.utcnow().isoformat()} ==="
            )

            with tqdm(total=len(pages), disable=pbar_disable, unit="pg") as pbar:
                for i, result in enumerate(
                    p.imap_unordered(process.process_page, pages)
                ):
                    pbar.update()
                    results.append(result)
            # for result in p.imap_unordered(process.process_page, pages):
            #    results.append(result)
            p.close()
            p.join()
        except KeyboardInterrupt:
            import sys

            print("Caught KeyboardInterrupt, terminating workers...", file=sys.stderr)
            _abort(p, logq, listener)
            return -1

    if arguments.csv:
        logger_csv = logging.getLogger("csv")
        if not os.path.exists(results_file) or os.path.getsize(results_file) == 0:
            logger_csv.info(
                '"Input File","Page Number","Computed angle","Variance of computed angles","Image width (px)","Image height (px)"'
            )

    for result in results:
        for image in result:
            (fname, pagenum, angle, variance, pagew, pageh) = image
            if arguments.csv:
                logger_csv.info(
                    '"{}",{},{},{},{},{}'.format(
                        fname, pagenum, angle, variance, pagew, pageh,
                    )
                )

    if arguments.histogram:
        try:
            histogram(results)
        except Exception:
            import sys
            import traceback

            logger.error(f"Exception in histogram process: \n{traceback.format_exc()}")
            _abort(None, logq, listener)
            return -1

    logger.info(f"=== Run ended @ {datetime.datetime.utcnow().isoformat()} ===")

    # end logging process
    logq.put(None)
    listener.join()

    return 0


if __name__ == "__main__":
    freeze_support()
    exit(run())
