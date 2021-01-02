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

from skimage.transform import resize
from imageio import imread, imwrite
from numpy import *

import matplotlib.pyplot as plt
import matplotlib.image as mpimg

import os
import sys

for f in sys.argv[1:]:
    filename = os.path.basename(f)
    page = imread(f)
    if page.ndim == 3:        # probably RGB
        #print("Multichannel")
        #print("{} - {}".format(filename, page.shape))

        # Remove about 1/4" from page margin,
        # because this is often dirty due to skewing
        croppx = 100
        h, w, _ = page.shape
        cropped = page[croppx : h-croppx, croppx : w-croppx]

        pageh, pagew, _ = cropped.shape
        rchan, gchan, bchan = cropped[:, :, 0], cropped[:, :, 1], cropped[:, :, 2]
        # Choose a percentile such that 90% of the image's pixels are brighter
        # Find this level in the histogram and we will consider it paper white
        thresh = pageh*pagew*0.1
        thresh2 = pageh*pagew*0.2  # more aggressive threshold used in duotone testing

        hist, _ = np.histogram(rchan, 256)
        rt = len(list(filter(lambda x: x < thresh, np.cumsum(hist))))
        rtt = len(list(filter(lambda x: x < thresh2, np.cumsum(hist))))

        hist, _ = np.histogram(gchan, 256)
        gt = len(list(filter(lambda x: x < thresh, np.cumsum(hist))))
        gtt = len(list(filter(lambda x: x < thresh2, np.cumsum(hist))))

        hist, _ = np.histogram(bchan, 256)
        bt = len(list(filter(lambda x: x < thresh, np.cumsum(hist))))
        btt = len(list(filter(lambda x: x < thresh2, np.cumsum(hist))))

        pts = set()
        matt = []
        num = 0
        den = 0
        num2 = 0
        den2 = 0
        samplestep = 5
        for i in range(0, pageh, samplestep):
          for j in range(0, pagew, samplestep):
            r, g, b = cropped[i, j]
            pts.add((r, g, b))
            d = max(r,g,b) - min(r,g,b)
            if r < rt or g < gt or b < bt:
              #matt.append(d)
              if d > 90:
                num += 1
              else:
                den += 1
            if r < rtt or g < gtt or b < btt:
              if d > 90:
                num2 += 1
              else:
                den2 += 1

        # duotone page test (black/orange, DEC datatrieve manual)
        # for a pure b&w image that is in rgb format, it will be 0

        # Not duotone: pages04aap.tif,1,0.06716292606481222,210,212,203

        pct_coloured = num*100.0/den
        print(f"{filename},{pct_coloured:.4f},{num2*100.0/den2:.4f},{rt},{gt},{bt}")
        sys.stdout.flush()
        #print("Pixels % where max - min rgb > 90: {}".format(pct_coloured))

        markersize = 0.2
        #fig, axs = plt.subplots(1, 4)
        #axs[0].set_xlabel('R')
        #axs[0].set_ylabel('G')
        #axs[0].scatter(list(map(lambda t: t[0], list(pts))), list(map(lambda t: t[1], list(pts))), markersize)
        #axs[0].scatter([rt], [gt], color="white")
        #axs[1].set_xlabel('R')
        #axs[1].set_ylabel('B')
        #axs[1].scatter(list(map(lambda t: t[0], list(pts))), list(map(lambda t: t[2], list(pts))), markersize)
        #axs[1].scatter([rt], [bt], color="white")
        #axs[2].set_xlabel('G')
        #axs[2].set_ylabel('B')
        #axs[2].scatter(list(map(lambda t: t[1], list(pts))), list(map(lambda t: t[2], list(pts))), markersize)
        #axs[2].scatter([gt], [bt], color="white")

        #plt.hist(matt, bins=32)
        #fig.tight_layout()
        #plt.show()

        #imwrite('{}crop.png'.format(filename), cropped)
    else:
        print("Monochrome")

