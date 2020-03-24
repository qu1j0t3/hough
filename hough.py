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

import logging
import logging.config
import logging.handlers
import os
import threading
from multiprocessing import Queue

import numpy as np
from docopt import docopt
from imageio import imread, imwrite
from skimage.color import rgb2gray
from skimage.draw import line_aa
from skimage.exposure import is_low_contrast
from skimage.feature import canny
from skimage.filters import threshold_otsu
from skimage.morphology import binary_dilation
from skimage.transform import downscale_local_mean, probabilistic_hough_line
from skimage.util import crop

VERSION = "hough 0.2"
WINDOW_SIZE = 150

# numpy's little helpers


def grey(x):
    return 0.3 if x else 0.0


def bool_to_255(x):
    return 255 if x else 0


def sum(a):
    return a.sum()


bool_to_255f = np.vectorize(bool_to_255)
greyf = np.vectorize(grey)
hough_prec = np.deg2rad(0.02)
hough_theta_h = np.arange(np.deg2rad(-93.0), np.deg2rad(-87.0), hough_prec)
hough_theta_v = np.arange(np.deg2rad(-3.0), np.deg2rad(3.0), hough_prec)
hough_theta_hv = np.concatenate((hough_theta_v, hough_theta_h))


def logger_thread(q):
    while True:
        record = q.get()
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)


def hough_angles(pos, neg, orientation="row"):
    height, width = pos.shape
    if orientation == "row":
        axis = 1
        length = int(width * 0.15)
        theta = hough_theta_h
    else:
        axis = 0
        length = int(height * 0.15)
        theta = hough_theta_v
    sums = np.apply_along_axis(sum, axis, neg)
    line = sums.argmax(0)

    # Grab a +/- WINDOW-SIZE strip for evaluation. We've already cropped out the margins.
    if orientation == "row":
        cropped = pos[
            max(line - WINDOW_SIZE, 0) : min(line + WINDOW_SIZE, height)  # noqa: E203
        ]
    else:
        cropped = pos[
            :, max(line - WINDOW_SIZE, 0) : min(line + WINDOW_SIZE, width)  # noqa: E203
        ]
    edges = binary_dilation(canny(cropped, 2))
    edges_grey = greyf(edges)

    lines = probabilistic_hough_line(edges, line_length=length, line_gap=2, theta=theta)

    angles = []
    for ((x0, y0), (x1, y1)) in lines:
        # Ensure line is moving rightwards/upwards
        if orientation == "row":
            k = 1 if x1 > x0 else -1
            offset = 0
        else:
            k = 1 if y1 > y0 else -1
            offset = 90
        angles.append(offset - np.rad2deg(np.math.atan2(k * (y1 - y0), k * (x1 - x0))))
        rr, cc, val = line_aa(c0=x0, r0=y0, c1=x1, r1=y1)
        for k, v in enumerate(val):
            edges_grey[rr[k], cc[k]] = (1 - v) * edges_grey[rr[k], cc[k]] + v

    return (angles, sums[line], edges_grey)


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
            "raw": {"class": "logging.Formatter", "format": "%(message)s"},
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "level": "INFO"},
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
        logger.info(f"Processing {f}")
        filename = os.path.basename(f)
        page = imread(f)

        if page.ndim != 1:  # probably RGB
            logger.debug("Multichannel - converting to grayscale")
            page = rgb2gray(page)
        pageh, pagew = page.shape
        logger.debug("{} - {}".format(filename, page.shape))

        # Remove the margins, which are often dirty due to skewing
        # 0.33" of an 8.5" page is approximately 1/25th
        pos = crop(page, pagew // 25)

        if is_low_contrast(pos):
            logger.debug("{} - low contrast - blank page?".format(filename))
            logger_csv.info(f'"{f}","","",{pagew},{pageh}')
            continue

        neg = 255 - pos

        h_angles, v_sums_row, h_edges_grey = hough_angles(pos, neg, "row")
        v_angles, h_sums_col, v_edges_grey = hough_angles(pos, neg, "column")

        angles = []

        if h_angles and v_sums_row > h_sums_col:
            angle = np.median(h_angles)
            imwrite("out/{}_{}_hlines.png".format(filename, angle), h_edges_grey)
            logger.debug("{}  Hough H angle: {} deg (median)".format(filename, angle))
        elif v_angles:
            angle = np.median(v_angles)
            imwrite("out/{}_{}_vlines.png".format(filename, angle), v_edges_grey)
            logger.debug("{}  Hough V angle: {} deg (median)".format(filename, angle))
        else:
            imwrite("out/{}_no_hlines.png".format(filename), h_edges_grey)
            logger.debug("{}  FAILED horizontal Hough".format(filename))
            imwrite("out/{}_no_vlines.png".format(filename), v_edges_grey)
            logger.debug("{}  FAILED vertical Hough".format(filename))

            # We didn't find a good feature at the H or V sum peaks.
            # Let's brutally dilate everything and look for a vertical margin!
            small = downscale_local_mean(neg, (2, 2))
            t = threshold_otsu(small)
            dilated = binary_dilation(small > t, np.ones((60, 60)))

            edges = canny(dilated, 3)
            edges_grey = greyf(edges)
            lines = probabilistic_hough_line(
                edges, line_length=int(pageh * 0.04), line_gap=6, theta=hough_theta_hv,
            )

            for ((x_0, y_0), (x_1, y_1)) in lines:
                if abs(x_1 - x_0) > abs(y_1 - y_0):
                    # angle is <= π/4 from horizontal or vertical
                    dir, x0, y0, x1, y1 = "H", x_0, y_0, x_1, y_1
                else:
                    dir, x0, y0, x1, y1 = "V", y_0, -x_0, y_1, -x_1
                # flip angle so that X delta is positive (East quadrants).
                k = 1 if x1 > x0 else -1
                a = np.rad2deg(np.math.atan2(k * (y1 - y0), k * (x1 - x0)))

                # Zero angles are suspicious -- could be a cropping margin.
                # If not, they don't add information anyway.
                if a != 0:
                    angles.append(-a)
                    rr, cc, val = line_aa(c0=x_0, r0=y_0, c1=x_1, r1=y_1)
                    for k, v in enumerate(val):
                        edges_grey[rr[k], cc[k]] = (1 - v) * edges_grey[
                            rr[k], cc[k]
                        ] + v

            if angles:
                angle = np.mean(angles)
                imwrite(
                    "out/{}_{}_lines_vertical.png".format(filename, angle), edges_grey
                )
                imwrite(
                    "out/{}_{}_lines_verticaldilated.png".format(filename, angle),
                    bool_to_255f(dilated),
                )
                logger.debug(
                    "{}  angle vertical: {} deg (mean)  {} deg (median)".format(
                        filename, angle, np.median(angles)
                    )
                )
            else:
                angle = None
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
