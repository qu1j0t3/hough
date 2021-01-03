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

import skimage
import skimage.data
import skimage.morphology
import skimage.filters
import scipy.ndimage

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
    h, w = shape(page)
    pagecropped = page[0 : h-(h%8), 0 : w-(w%8)]
    downsampled = skimage.transform.downscale_local_mean(pagecropped, (8,8))

    out = scipy.ndimage.median_filter(downsampled, size=23)

    outupsampled = skimage.transform.resize(out, output_shape=(h-(h%8),w-(w%8)))
    flatpage = np.subtract(pagecropped, outupsampled)
    #imwrite('{}-median.png'.format(filename), out)
    imwrite('{}.tif'.format(filename), np.clip((flatpage+128)*2, 0, 255).astype(uint8))

