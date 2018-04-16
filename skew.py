#!/usr/local/bin/python
# -*- coding: utf-8 -*-

#    This file is part of "hough", which detects skew angles in scanned images
#    Copyright (C) 2016 Toby Thain, toby@telegraphics.com.au
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
from scipy.ndimage import measurements
from skimage.transform import resize
from imageio import imread, imwrite
from numpy import *

import os
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Pipe the output to    ./distribute.sh

def grey(x):
    return 0.3 if x else 0.0
greyf = np.vectorize(grey)

hough_prec = deg2rad(0.02)
hough_theta_h  = arange(deg2rad(-93.0), deg2rad(-87.0), hough_prec)
hough_theta_hv = np.concatenate( (arange(deg2rad(-3.0), deg2rad(3.0), hough_prec), hough_theta_h) )

try:
    os.mkdir('out')
except OSError:
    pass

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
        neg = 255-pos

        # find row with maximum sum - this should pass thru the centre of the horizontal rule
        def sum(a):
            return a.sum()
        sums = np.apply_along_axis(sum, 1, neg)
        row = sums.argmax(0)

        # Detect edges
        cropped = pos[max(row-150, 0):min(row+150, pageh)]
        edges = binary_dilation(canny(cropped, 2))
        edgesg = greyf(edges)

        # Now try Hough transform
        lines = probabilistic_hough_line(
                 edges,
                 line_length=pagew*0.15,
                 line_gap=2,
                 theta=hough_theta_h)

        for ((x0,y0),(x1,y1)) in lines:
            # Ensure line is moving rightwards
            k = 1 if x1 > x0 else -1
            angles.append( - rad2deg(math.atan2(k*(y1-y0), k*(x1-x0))) )
            rr, cc, val = line_aa(c0=x0, r0=y0, c1=x1, r1=y1)
            for k, v in enumerate(val):
                edgesg[rr[k], cc[k]] = (1-v)*edgesg[rr[k], cc[k]] + v

        if angles:
            a = mean(angles)
            angle = a
            imwrite('out/{}_{}_lines.png'.format(filename, a), edgesg)
            eprint("{}  Hough angle: {} deg (mean)   {} deg (median)".format(filename, a, median(angles)))
        else:
            imwrite('out/{}_no_lines.png'.format(filename), edgesg)
            eprint("{}  FAILED horizontal Hough".format(filename))


            # If we didn't find a good feature at the horizontal sum peak,
            # let's brutally dilate everything and look for a vertical margin
            small = downscale_local_mean(neg, (2,2))
            t = threshold_otsu(small)
            dilated = binary_dilation(small > t, rectangle(60, 60))

            edges = canny(dilated, 3)
            edgesg = greyf(edges)
            # Now try Hough transform
            lines = probabilistic_hough_line(
                     edges,
                     line_length=pageh*0.04,
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
                a = mean(angles)
                angle = a
                imwrite('out/{}_{}_lines_vertical.png'.format(filename, a), edgesg)
                eprint("{}  angle vertical: {} deg (mean)  {} deg (median)".format(filename, a, median(angles)))
            else:
                imwrite('out/{}_dilated.png'.format(filename), dilated)
                imwrite('out/{}_dilate_edges.png'.format(filename), edges)
                eprint("{}  FAILED vertical".format(filename))

    print('"{}",{},{},{},{}'.format(f, angle or '', np.var(angles) if angles else '', pagew, pageh))
    sys.stdout.flush()
