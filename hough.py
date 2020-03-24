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
  hough [-hv] FILE ...

Arguments:
  FILE              Input file(s) to process

Options:
  -h --help         Display this help and exit
  --version         Display the version number and exit
  -v --verbose      print status messages

"""

from docopt import docopt
from imageio import imread, imwrite
import logging
import logging.config
import logging.handlers
from multiprocessing import Process, Queue
import numpy as np
import os
from skimage.draw import line_aa
from skimage.exposure import is_low_contrast
from skimage.feature import canny
from skimage.filters import threshold_otsu
from skimage.morphology import binary_dilation
from skimage.transform import downscale_local_mean, probabilistic_hough_line
from skimage.util import crop
import sys
import threading
import time

VERSION = "hough 0.2"


def grey(x):
    return 0.3 if x else 0.0


def bool_to_255(x):
    return 255 if x else 0


def sum(a):
    return a.sum()


def logger_thread(q):
    while True:
        record = q.get()
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)


greyf = np.vectorize(grey)

bool_to_255f = np.vectorize(bool_to_255)

hough_prec = np.deg2rad(0.02)
hough_theta_h = np.arange(np.deg2rad(-93.0), np.deg2rad(-87.0), hough_prec)
hough_theta_v = np.arange(np.deg2rad(-3.0), np.deg2rad(3.0), hough_prec)
hough_theta_hv = np.concatenate((hough_theta_v, hough_theta_h))


if __name__ == "__main__":
    arguments = docopt(__doc__, version=VERSION)

    logq = Queue()
    logd = {
        "version": 1,
        "formatters": {
            "detailed": {
                "class": "logging.Formatter",
                "format": "%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s",
            },
            "raw": {"class": "logging.Formatter", "format": "%(message)s",},
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "level": "INFO",},
            "file": {
                "class": "logging.FileHandler",
                "filename": "hough.log",
                "mode": "w",
                "formatter": "detailed",
            },
            "csv": {
                "class": "logging.FileHandler",
                "filename": "results.csv",
                "mode": "w",
                "formatter": "raw",
            },
        },
        "loggers": {"csv": {"handlers": ["csv"]}},
        "root": {"level": "DEBUG", "handlers": ["console", "file"]},
    }
    logging.config.dictConfig(logd)
    lp = threading.Thread(target=logger_thread, args=(logq,))
    lp.start()
    logger = logging.getLogger("hough")
    logger_csv = logging.getLogger("csv")

    try:
        os.mkdir("out")
    except OSError:
        pass

    for f in arguments.FILE:
        filename = os.path.basename(f)
        logger.info(f"Processing {f}")
        page = imread(f)
        if page.ndim == 3:  # probably RGB
            logger.debug("Multichannel - extracting 2nd channel")
            page = page[:, :, 1]  # extract green channel
        pageh, pagew = page.shape
        logger.debug("{} - {}".format(filename, page.shape))

        # Remove about 1/4" from page margin, because this is often dirty
        # due to skewing
        pos = crop(page, 150)

        angles = []
        angle = None
        if is_low_contrast(pos):
            logger.debug("{} - low contrast - blank page?".format(filename))
        else:
            neg = 255 - pos

            # ----------
            # find row with maximum sum - this should pass thru the centre of the horizontal rule

            vsums = np.apply_along_axis(sum, 1, neg)
            row = vsums.argmax(0)

            # Detect edges
            cropped = pos[max(row - 150, 0) : min(row + 150, pageh)]
            # This dilation is dangerous if it's going to touch the page edges,
            # since then a lot of 0/90° lines will be found, likely ruining the results.
            edges = binary_dilation(canny(cropped, 2))
            hedgesg = greyf(edges)

            # Now try Hough transform
            lines = probabilistic_hough_line(
                edges, line_length=int(pagew * 0.15), line_gap=2, theta=hough_theta_h
            )

            hangles = []
            for ((x0, y0), (x1, y1)) in lines:
                # Ensure line is moving rightwards
                k = 1 if x1 > x0 else -1
                hangles.append(-np.rad2deg(np.math.atan2(k * (y1 - y0), k * (x1 - x0))))
                rr, cc, val = line_aa(c0=x0, r0=y0, c1=x1, r1=y1)
                for k, v in enumerate(val):
                    hedgesg[rr[k], cc[k]] = (1 - v) * hedgesg[rr[k], cc[k]] + v

            # ----------
            # find col with maximum sum - this should pass thru the centre of a vertical rule

            hsums = np.apply_along_axis(sum, 0, neg)
            col = hsums.argmax(0)

            # Detect edges
            cropped = pos[:, max(col - 150, 0) : min(col + 150, pageh)]
            c = canny(cropped, 2)
            edges = binary_dilation(c)
            vedgesg = greyf(edges)

            # Now try Hough transform
            lines = probabilistic_hough_line(
                edges, line_length=int(pageh * 0.15), line_gap=2, theta=hough_theta_v
            )

            vangles = []
            for ((x0, y0), (x1, y1)) in lines:
                # Ensure line is moving upwards
                k = 1 if y1 > y0 else -1
                vangles.append(
                    90 - np.rad2deg(np.math.atan2(k * (y1 - y0), k * (x1 - x0)))
                )
                rr, cc, val = line_aa(c0=x0, r0=y0, c1=x1, r1=y1)
                for k, v in enumerate(val):
                    vedgesg[rr[k], cc[k]] = (1 - v) * vedgesg[rr[k], cc[k]] + v
            # ----------

            if hangles and vsums[row] > hsums[col]:
                angle = a = np.median(hangles)
                imwrite("out/{}_{}_hlines.png".format(filename, a), hedgesg)
                logger.debug("{}  Hough H angle: {} deg (median)".format(filename, a))
            elif vangles:
                angle = a = np.median(vangles)
                imwrite("out/{}_{}_vlines.png".format(filename, a), vedgesg)
                logger.debug("{}  Hough V angle: {} deg (median)".format(filename, a))
            else:
                imwrite("out/{}_no_hlines.png".format(filename), hedgesg)
                logger.debug("{}  FAILED horizontal Hough".format(filename))
                imwrite("out/{}_no_vlines.png".format(filename), vedgesg)
                logger.debug("{}  FAILED vertical Hough".format(filename))

                # If we didn't find a good feature at the horizontal sum peak,
                # let's brutally dilate everything and look for a vertical margin
                small = downscale_local_mean(neg, (2, 2))
                t = threshold_otsu(small)
                dilated = binary_dilation(small > t, np.ones((60, 60)))

                edges = canny(dilated, 3)
                edgesg = greyf(edges)
                # Now try Hough transform
                lines = probabilistic_hough_line(
                    edges,
                    line_length=int(pageh * 0.04),
                    line_gap=6,
                    theta=hough_theta_hv,
                )

                angles = []
                for ((x_0, y_0), (x_1, y_1)) in lines:
                    # angle is <= π/4 from horizontal or vertical
                    if abs(x_1 - x_0) > abs(y_1 - y_0):
                        dir, x0, y0, x1, y1 = "H", x_0, y_0, x_1, y_1
                    else:
                        dir, x0, y0, x1, y1 = "V", y_0, -x_0, y_1, -x_1
                    # flip angle so that X delta is positive (East quadrants).
                    k = 1 if x1 > x0 else -1
                    a = np.rad2deg(np.math.atan2(k * (y1 - y0), k * (x1 - x0)))
                    # Zero angles are suspicious -- could be a cropping margin. If not, they don't add information anyway.
                    if a != 0:
                        angles.append(-a)
                        rr, cc, val = line_aa(c0=x_0, r0=y_0, c1=x_1, r1=y_1)
                        # logger.debut("{}  line: {} {}   {},{} - {},{}".format(filename, a, dir, x_0, y_0, x_1, y_1))
                        for k, v in enumerate(val):
                            edgesg[rr[k], cc[k]] = (1 - v) * edgesg[rr[k], cc[k]] + v

                if angles:
                    a = np.mean(angles)
                    angle = a
                    imwrite("out/{}_{}_lines_vertical.png".format(filename, a), edgesg)
                    imwrite(
                        "out/{}_{}_lines_verticaldilated.png".format(filename, a),
                        bool_to_255f(dilated),
                    )
                    logger.debug(
                        "{}  angle vertical: {} deg (mean)  {} deg (median)".format(
                            filename, a, np.median(angles)
                        )
                    )
                else:
                    imwrite("out/{}_dilated.png".format(filename), dilated)
                    imwrite("out/{}_dilate_edges.png".format(filename), edges)
                    logger.debug("{}  FAILED vertical".format(filename))

        logger_csv.info(
            '"{}",{},{},{},{}'.format(
                f, angle or "", np.var(angles) if angles else "", pagew, pageh
            )
        )

    # end logging thread
    logq.put(None)
    lp.join()
