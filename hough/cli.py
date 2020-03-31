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
  hough [options] [FILE] ...
  hough [options] [--results=<file>] [FILE] ...
  hough (-r | --rotate) [options] [--results=<file>]
  hough (-r | --rotate) [options] [--results=<file>] [FILE] ...

Arguments:
  FILE                          input files to analyze/rotate

Options:
  -h --help                     display this help and exit
  --version                     display the version number and exit
  -v --verbose                  print status messages
  -d --debug                    retain debug image output in debug/ dir
                                (also enables --verbose)
  --histogram                   display rotation angle histogram summary
  -o DIR, --out=DIR             store output results/images in named
                                directory. Directory is created if it
                                does not exist [default: out/TIMESTAMP]
  --results=<file>              save results in FILE under output path,
                                or specify path to results file for
                                rotation [default: results.csv]
  -w <workers> --workers=<#>    specify the number of workers to run
                                simultaneously. Default: total # of CPUs
  -r --rotate                   rotates the files passed on the command
                                line, or if none given, those listed
                                in the results file.
"""

import csv
import datetime
import logging
import os
import sys
import time
from multiprocessing import Pool, cpu_count, freeze_support

from docopt import docopt
from tqdm import tqdm

import hough

from . import log_utils


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


def _process_args(arguments):
    if arguments.debug:
        arguments["verbose"] = True
        arguments["log_level"] = logging.DEBUG
    elif arguments.verbose:
        arguments["log_level"] = logging.INFO
    else:
        arguments["log_level"] = logging.WARNING
    arguments["pbar_disable"] = arguments.quiet or arguments.verbose or arguments.debug

    arguments["now"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
    if arguments.out == "out/TIMESTAMP":
        arguments["out"] = f"out/{arguments.now}"
    else:
        arguments["out"] = os.path.abspath(arguments.out)
    if not os.path.isdir(arguments.out):
        try:
            os.makedirs(arguments.out)
        except Exception:
            print(f"Unable to create output directory f{arguments.out}! Exiting...")
            return -1
    if arguments.debug and not os.path.isdir(f"debug/{arguments.now}"):
        os.makedirs(f"debug/{arguments.now}")

    # --rotate needs files to process, or results
    if arguments.rotate and len(arguments.FILE) == 0:
        if (
            not os.path.exists(arguments.results)
            or os.path.getsize(arguments.results) == 0
        ):
            print(
                f"No results in {arguments.results} to rotate and no files specified!"
            )
            return -1
    # --rotate with args, or files given. Was a results file path specified?
    elif os.path.split(arguments.results)[0]:
        arguments["results"] = os.path.abspath(arguments.results)
    else:
        arguments["results"] = os.path.join(arguments.out, arguments.results)

    if arguments.workers:
        arguments["workers"] = int(arguments.workers)
    else:
        arguments["workers"] = cpu_count()

    return arguments


def run(argv=sys.argv[1:]):
    if len(argv) == 0:
        print(__doc__.strip("\n"))
        return 0
    arguments = docopt(__doc__, argv=argv, version=hough.__version__, more_magic=True)
    arguments = _process_args(arguments)
    if arguments == -1:
        return -1

    logq, listener = log_utils.start_logger_process(
        arguments.log_level, arguments.results
    )

    results = []

    # The pool that launched 1,000 Houghs...
    # We do it this way, not with a map, until https://github.com/tqdm/tqdm/issues/548 is fixed
    with Pool(
        processes=arguments.workers,
        initializer=hough.analyse._init_worker,
        initargs=(logq, arguments.debug, arguments.now,),
    ) as p:
        try:
            log_utils.setup_queue_logging(logq)
            logger = logging.getLogger("hough")
            logger.info(
                f"=== Run started @ {datetime.datetime.utcnow().isoformat()} ==="
            )

            pages = []
            for f in arguments.FILE:
                pages += hough.get_pages(f)

            if pages:
                with tqdm(
                    total=len(pages),
                    disable=arguments.pbar_disable,
                    unit="pg",
                    desc="Analysis: ",
                ) as pbar:
                    for i, result in enumerate(
                        p.imap_unordered(hough.analyse_page, pages)
                    ):
                        pbar.update()
                        results.append(result)
            p.close()
            p.join()
        except KeyboardInterrupt:
            import sys

            print("Caught KeyboardInterrupt, terminating workers...", file=sys.stderr)
            _abort(p, logq, listener)
            return -1

    logger_csv = logging.getLogger("csv")
    if not os.path.exists(arguments.results) or os.path.getsize(arguments.results) == 0:
        logger_csv.info(
            '"Input File","Page Number","Computed angle","Variance of computed angles","Image width (px)","Image height (px)"'
        )

    read_csv = False
    # might be rotating a previously generated csv file...
    if (
        not results
        and os.path.exists(arguments.results)
        and os.path.getsize(arguments.results) > 0
    ):
        with open(arguments.results, newline="") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row[0] == "Input File":
                    continue
                for idx in [1, 4, 5]:
                    row[idx] = int(row[idx]) if row[idx] else ""
                for idx in [2, 3]:
                    row[idx] = float(row[idx]) if row[idx] else ""
                results.append([tuple(row)])
        read_csv = True

    if arguments.histogram:
        try:
            hough.histogram(results)
        except Exception:
            import sys
            import traceback

            logger.error(f"Exception in histogram process: \n{traceback.format_exc()}")
            _abort(None, logq, listener)
            return -1

    dictresults = {}
    num_pages = 0
    for result in results:
        for image in result:
            num_pages += 1
            dictresults.setdefault(image[0], []).append(image)
            (fname, pagenum, angle, variance, pagew, pageh) = image
            if not read_csv:
                logger_csv.info(
                    '"{}",{},{},{},{},{}'.format(
                        fname, pagenum, angle, variance, pagew, pageh,
                    )
                )

    if arguments.rotate:
        with tqdm(
            total=num_pages,
            disable=arguments.pbar_disable,
            unit="pg",
            desc="Rotation: ",
        ) as pbar:
            for f in dictresults:
                for i, result in enumerate(
                    hough.rotate(
                        sorted(dictresults[f], key=lambda x: int(x[1]) if x[1] else 0),
                        arguments.out,
                        generator=True,
                    )
                ):
                    pbar.update()

    logger.info(f"=== Run ended @ {datetime.datetime.utcnow().isoformat()} ===")

    # end logging process
    logq.put(None)
    listener.join()

    return 0


if __name__ == "__main__":
    freeze_support()
    exit(run())
