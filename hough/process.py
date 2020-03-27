"""
Worker functions for a parallelizable deskewer.
"""
import logging
import os
import signal

import fitz
import numpy as np
from imageio import imread, imwrite
from skimage.color import rgb2gray
from skimage.draw import line_aa
from skimage.exposure import is_low_contrast
from skimage.feature import canny
from skimage.filters import threshold_otsu
from skimage.morphology import binary_dilation
from skimage.transform import downscale_local_mean, probabilistic_hough_line
from skimage.util import crop

import hough


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
            max(line - hough.WINDOW_SIZE, 0) : min(
                line + hough.WINDOW_SIZE, height
            )  # noqa: E203
        ]
    else:
        cropped = pos[
            :,
            max(line - hough.WINDOW_SIZE, 0) : min(
                line + hough.WINDOW_SIZE, width
            ),  # noqa: E203
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


def _init_worker(q, args):
    # Ignore CTRL+C in the workers, see http://jessenoller.com/blog/2009/01/08/multiprocessingpool-and-keyboardinterrupt
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    qh = logging.handlers.QueueHandler(q)
    root = logging.getLogger()
    root.addHandler(qh)
    # this is a global only within the multiprocessing Pool workers, not in the main process.
    global arguments
    arguments = args


def process_page(f, page, mimetype):
    logger = logging.getLogger("worker_hough")
    if mimetype == "application/pdf":
        doc = fitz.open(f)
        imagelist = doc.getPageImageList(page)
        if len(imagelist) == 1:
            logger.info(f"Processing {f} - page {page} - {len(imagelist)} image...")
        else:
            logger.info(f"Processing {f} - page {page} - {len(imagelist)} images...")
        for item in imagelist:
            xref = item[0]
            smask = item[1]
            if smask == 0:
                imgdict = doc.extractImage(xref)
                image = imread(imgdict["image"])
                process_image(f, image, logger, pagenum=page)
            else:
                logger.error(
                    f"Cannot process {f} - page {page} - image {xref} - smask=={smask}"
                )
    else:
        # TODO: support multi-image TIFF with
        #   https://imageio.readthedocs.io/en/stable/userapi.html#imageio.mimread
        logger.error(f"Cannot process {f}: unknown file format")


def process_file(f):
    logger = logging.getLogger("worker_hough")
    logger.info(f"Processing {f}")
    image = imread(f)
    process_image(f, image, logger)


def process_image(f, page, logger, pagenum=""):
    global arguments
    if arguments.csv:
        logger_csv = logging.getLogger("worker_csv")
    filename = os.path.basename(f)

    if page.ndim > 2:
        logger.debug(f"{f} is multichannel - converting to grayscale")
        page = rgb2gray(page)
    pageh, pagew = page.shape
    logger.debug(f"{filename} - {page.shape}")

    # Remove the margins, which are often dirty due to skewing
    # 0.33" of an 8.5" page is approximately 1/25th
    pos = crop(page, pagew // 25)

    if is_low_contrast(pos):
        logger.debug(f"{filename} - low contrast - blank page?")
        logger_csv.info(f'"{f}","","",{pagew},{pageh}')
        return

    neg = 255 - pos

    h_angles, v_sums_row, h_edges_grey = hough_angles(pos, neg, "row")
    v_angles, h_sums_col, v_edges_grey = hough_angles(pos, neg, "column")

    angles = []

    if h_angles and v_sums_row > h_sums_col:
        angle = np.median(h_angles)
        if arguments.debug:
            imwrite(f"out/{arguments.now}/{filename}_{angle}_hlines.png", h_edges_grey)
        logger.debug(f"{filename}  Hough H angle: {angle} deg (median)")
    elif v_angles:
        angle = np.median(v_angles)
        if arguments.debug:
            imwrite(f"out/{arguments.now}/{filename}_{angle}_vlines.png", v_edges_grey)
        logger.debug(f"{filename}  Hough V angle: {angle} deg (median)")
    else:
        if arguments.debug:
            imwrite(f"out/{arguments.now}/{filename}_no_hlines.png", h_edges_grey)
            imwrite(f"out/{arguments.now}/{filename}_no_vlines.png", v_edges_grey)
        logger.debug(f"{filename}  FAILED peak sum horizontal & vertical Hough")

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
                _, x0, y0, x1, y1 = "H", x_0, y_0, x_1, y_1
            else:
                _, x0, y0, x1, y1 = "V", y_0, -x_0, y_1, -x_1
            # flip angle so that X delta is positive (East quadrants).
            k = 1 if x1 > x0 else -1
            a = np.rad2deg(np.math.atan2(k * (y1 - y0), k * (x1 - x0)))

            # Zero angles are suspicious -- could be a cropping margin.
            # If not, they don't add information anyway.
            if a != 0:
                angles.append(-a)
                rr, cc, val = line_aa(c0=x_0, r0=y_0, c1=x_1, r1=y_1)
                for k, v in enumerate(val):
                    edges_grey[rr[k], cc[k]] = (1 - v) * edges_grey[rr[k], cc[k]] + v

        if angles:
            angle = np.mean(angles)
            if arguments.debug:
                imwrite(
                    f"out/{arguments.now}/{filename}_{angle}_lines_vertical.png",
                    edges_grey,
                )
                imwrite(
                    f"out/{arguments.now}/{filename}_{angle}_lines_verticaldilated.png",
                    bool_to_255f(dilated),
                )
            logger.debug(
                f"{filename}  angle vertical: {angle} deg (mean)  {np.median(angles)} deg (median)"
            )
        else:
            angle = None
            if arguments.debug:
                imwrite(f"out/{arguments.now}/{filename}_dilated.png", dilated)
                imwrite(f"out/{arguments.now}/{filename}_dilate_edges.png", edges)
            logger.debug("{}  FAILED dilated vertical Hough".format(filename))

    if arguments.csv:
        logger_csv.info(
            '"{}",{},{},{},{},{}'.format(
                f,
                int(pagenum) or "",
                angle or "",
                np.var(angles) if angles else "",
                pagew,
                pageh,
            )
        )

    return 0
