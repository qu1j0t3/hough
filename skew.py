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

from __future__ import print_function

import numpy as np

from skimage.exposure import *
from skimage.transform import *
from skimage.morphology import *
from skimage.measure import *
from skimage.segmentation import *
from skimage.feature import *
from skimage.draw import *
from skimage import img_as_uint, img_as_ubyte
from skimage.filters import threshold_otsu
from skimage.util import crop
from skimage.transform import resize
import scipy.ndimage
from scipy.ndimage import measurements
from imageio import imread, imwrite
from numpy import *

import os
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def grey(x):
    return 0.3 if x else 0.0
greyf = np.vectorize(grey)

def bool_to_255(x):
    return 255 if x else 0
bool_to_255f = np.vectorize(bool_to_255)

hough_prec = deg2rad(0.02)
hough_theta_h  = arange(deg2rad(-93.0), deg2rad(-87.0), hough_prec)
hough_theta_v  = arange(deg2rad(-3.0), deg2rad(3.0), hough_prec)
hough_theta_hv = np.concatenate( (hough_theta_v, hough_theta_h) )

try:
    os.mkdir('out')
except OSError:
    pass

def hlines(edges, length):
    lines = probabilistic_hough_line( edges, line_length=int(length), line_gap=2, theta=hough_theta_h)
    hangles = []
    for ((x0,y0),(x1,y1)) in lines:
        # Ensure line is moving rightwards
        k = 1 if x1 > x0 else -1
        hangles.append( (True, - rad2deg(math.atan2(k*(y1-y0), k*(x1-x0))), x0, y0, x1, y1, length) )
    return hangles

def vlines(edges, length):
    lines = probabilistic_hough_line( edges, line_length=int(length), line_gap=2, theta=hough_theta_v)
    vangles = []
    for ((x0,y0),(x1,y1)) in lines:
        # Ensure line is moving upwards
        k = 1 if y1 > y0 else -1
        vangles.append( (False, 90 - rad2deg(math.atan2(k*(y1-y0), k*(x1-x0))), x0, y0, x1, y1, length) )
    return vangles

for f in sys.argv[1:]:
    filename = os.path.basename(f)
    #if i == 30:
    #    exit()
    page = imread(f)
    if page.ndim == 3:        # probably RGB
        print("Multichannel - extracting 2nd channel")
        page = page[:, :, 1]  # extract green channel
    pageh, pagew = page.shape
    eprint("{} - {}".format(filename, page.shape))

    # Remove about 1/4" from page margin, because this is often dirty
    # due to skewing
    pos = crop(page, 150)

    angles = []
    angle = None
    if is_low_contrast(pos):
        eprint("{} - low contrast - blank page?".format(filename))
    else:
        #neg = img_as_ubyte(pos < t)
        # pos page is 0 = black, 255 = white
        # remove lightest 20% of grey pixels to reduce false positives on h/v rule detection
        thr = 255*0.8
        p = np.clip(pos, 0, thr)
        neg = thr-p

        # find row with maximum sum - this should pass thru the centre of the horizontal rule
        # low pass filtering in the desired direction makes detection more reliable
        hblur = scipy.ndimage.median_filter(neg, size=(51,1))
        hsums = np.apply_along_axis(sum, 1, hblur)
        row = hsums.argmax(0)

        # Cannot use the raw image with the Hough transform because it will detect lines
        # within solid areas! So we need to edge detect first.

        # This dilation is dangerous if it's going to touch the page edges,
        # since then a lot of 0/90° lines will be found, likely ruining the results.
        hedges = binary_dilation(canny( pos[max(row-150, 0):min(row+150, pageh)] , 2))

        # find col with maximum sum - this should pass thru the centre of a vertical rule
        vblur = scipy.ndimage.median_filter(neg, size=(1,51))
        vsums = np.apply_along_axis(sum, 0, vblur)
        col = vsums.argmax(0)

        # Detect edges
        vedges = binary_dilation(canny( pos[:, max(col-150, 0):min(col+150, pagew)] , 2))

        lines = hlines(hedges, pagew*0.15) + vlines(vedges, pagew*0.15)

        if len(lines) == 0:
            imwrite('out/{}_no_hlines.png'.format(filename), (greyf(hedges)*255.0).astype(np.uint8))
            imwrite('out/{}_no_vlines.png'.format(filename), (greyf(vedges)*255.0).astype(np.uint8))
            vc = binary_dilation(canny(vblur, 2, low_threshold=100))
            hc = binary_dilation(canny(hblur, 2, low_threshold=100))
            lines = hlines(vc, pagew*0.15) + vlines(hc, pagew*0.15)
            hedgesg = greyf(vc)
            vedgesg = greyf(hc)
        else:
            hedgesg = greyf(hedges)
            vedgesg = greyf(vedges)

        if len(lines) > 0:
            angle = a = median([x[1] for x in lines])
            eprint("{}  Hough simple rule angle: {} deg (median) (length {})".format(filename, a, lines[0][6]))
            hs = 0
            vs = 0
            for result in lines:
                is_h, _, x0, y0, x1, y1, _ = result
                # draw line for debugging
                rr, cc, val = line_aa(c0=x0, r0=y0, c1=x1, r1=y1)
                if is_h:
                    hs += 1
                    for k, v in enumerate(val):
                        hedgesg[rr[k], cc[k]] = (1-v)*hedgesg[rr[k], cc[k]] + v
                else:
                    vs += 1
                    for k, v in enumerate(val):
                        vedgesg[rr[k], cc[k]] = (1-v)*vedgesg[rr[k], cc[k]] + v
            if hs > 0:
                imwrite('out/{}_{}_Hlines.png'.format(filename, a), (hedgesg*255.0).astype(np.uint8))
            if vs > 0:
                imwrite('out/{}_{}_Vlines.png'.format(filename, a), (vedgesg*255.0).astype(np.uint8))
        else:
            #imwrite('out/{}_hblur.png'.format(filename), hblur)
            #imwrite('out/{}_vblur.png'.format(filename), vblur)

            # If we didn't find a simple rule,
            # let's brutally dilate everything and look for a vertical margin
            small = downscale_local_mean(neg, (2,2))
            t = threshold_otsu(small)
            dilated = binary_dilation(small > t, np.ones((60,60)))

            edges = canny(dilated, 3)
            edgesg = greyf(edges)
            # Now try Hough transform
            lines = probabilistic_hough_line(
                     edges,
                     line_length=int(pageh*0.04),
                     line_gap=6,
                     theta=hough_theta_hv)

            angles = []
            for ((x_0,y_0),(x_1,y_1)) in lines:
                # angle is <= π/4 from horizontal or vertical
                if abs(x_1-x_0) > abs(y_1-y_0):
                    dir, x0, y0, x1, y1 = 'H',  x_0,  y_0,  x_1,  y_1
                else:
                    dir, x0, y0, x1, y1 = 'V',  y_0, -x_0,  y_1, -x_1
                # flip angle so that X delta is positive (East quadrants).
                k = 1 if x1 > x0 else -1
                a = rad2deg(math.atan2(k*(y1-y0), k*(x1-x0)))
                # Zero angles are suspicious -- could be a cropping margin. If not, they don't add information anyway.
                if(a != 0):
                    angles.append( -a )
                    rr, cc, val = line_aa(c0=x_0, r0=y_0, c1=x_1, r1=y_1)
                    #eprint("{}  line: {} {}   {},{} - {},{}".format(filename, a, dir, x_0, y_0, x_1, y_1))
                    for k, v in enumerate(val):
                        edgesg[rr[k], cc[k]] = (1-v)*edgesg[rr[k], cc[k]] + v

            if angles:
                a = median(angles)
                angle = a
                imwrite('out/{}_{}_lines_vertical.png'.format(filename, a), (edgesg*255.0).astype(np.uint8))
                #imwrite('out/{}_{}_lines_verticaldilated.png'.format(filename, a), bool_to_255f(dilated))
                eprint("{}  angle vertical: {} deg (mean)  {} deg (median)".format(filename, a, median(angles)))
            else:
                imwrite('out/{}_dilated.png'.format(filename), dilated.astype(np.uint8))
                imwrite('out/{}_dilate_edges.png'.format(filename), edges.astype(np.uint8))
                eprint("{}  FAILED vertical".format(filename))

    print('"{}",{},{},{},{}'.format(f, angle or '', np.var(angles) if angles else '', pagew, pageh))
    sys.stdout.flush()
