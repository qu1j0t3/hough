#!/usr/local/bin/python
# -*- coding: utf-8 -*-

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
from scipy.ndimage import imread, measurements
from scipy.misc import imresize, imsave
from numpy import *

import os
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Pipe the output to    ./distribute.sh

def grey(x):
    return 0.4 if x else 0.0
greyf = np.vectorize(grey)

for f in sys.argv[1:]:
    filename = os.path.basename(f)
    #if i == 30:
    #    exit()
    page = imread(f)
    pageh, pagew = page.shape

    # Remove about 1/4" from page margin, because this is often dirty
    # due to skewing
    pos = crop(page, 150)

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
        edges = binary_dilation( canny(pos[row-150:row+150], 2) )
        edgesg = greyf(edges)
        # Now try Hough transform
        lines = probabilistic_hough_line(
                 edges,
                 line_length=pagew*0.15,
                 line_gap=3,
                 theta=arange(deg2rad(-93.0), deg2rad(-87.0), deg2rad(0.02)))

        angles = []
        for ((x0,y0),(x1,y1)) in lines:
            # Ensure line is moving rightwards
            k = 1 if x1 > x0 else -1
            angles.append( - rad2deg(math.atan2(k*(y1-y0), k*(x1-x0))) )
            rr, cc, val = line_aa(x0=x0, y0=y0, x1=x1, y1=y1)
            for k, v in enumerate(val):
                edgesg[rr[k], cc[k]] = (1-v)*edgesg[rr[k], cc[k]] + v

        if angles:
            a = mean(angles)
            angle = a
            imsave('out/{}_{}_lines.png'.format(filename, a), edgesg)
            eprint("{}  Hough angle: {} deg (mean)   {} deg (median)".format(filename, a, median(angles)))
        else:
            imsave('out/{}_no_lines.png'.format(filename), edgesg)
            eprint("{}  FAILED horizontal Hough".format(filename))

            t = threshold_otsu(neg)

            # grab area +/- 100 pixels from row - this is about 3° rotation at 600dpi
            thresh = neg[row-100:row+100] > t
            labels = label(thresh, connectivity=1)

            aspectmax = 0
            thinnest = None
            for r in regionprops(labels, pos[row-100:row+100]):
                w = r.bbox[3]-r.bbox[1]
                aspect = float(w) / (r.bbox[2]-r.bbox[0])

                # If the aspect is < say 80? 60?, it's unlikely to be an actual rule,
                # or it might be a rule intersected by text or other rules.
                # Maybe in this case we could do Hough transform and try to pick
                # very long lines?
                if(aspect > aspectmax):
                    aspectmax = aspect
                    thinnest = r

            if thinnest and aspectmax > 60:
                a = rad2deg(thinnest.orientation)
                # Drop other labels
                def relabel(x):
                    return x if x == thinnest.label else 0
                relabel_func = np.vectorize(relabel)
                relabelled = relabel_func(labels)
                out = mark_boundaries(pos[row-100:row+100], relabelled, color=(1,0,0))
                imsave('out/{}_rule.png'.format(filename), out)
                eprint("{}  found rule: {}  aspect: {}  angle: {} deg".format(filename, thinnest.label, aspectmax, a))
                angle = a
            else:
                # If we didn't find a good feature at the horizontal sum peak,
                # let's brutally dilate everything and look for a vertical margin
                small = downscale_local_mean(neg, (2,2))
                # FIXME: This dilation is SLOW
                dilated = binary_dilation(small > t, rectangle(60, 1))

                # The Canny must use a very wide Gaussian to smooth out inter-line bumps
                edges = canny(dilated)
                edgesg = greyf(edges)
                # Now try Hough transform
                th = np.concatenate( (arange(deg2rad(-93.0), deg2rad(-87.0), deg2rad(0.02)),
                                      arange(deg2rad( -3.0), deg2rad(  3.0), deg2rad(0.02))) )
                lines = probabilistic_hough_line(
                         edges,
                         line_length=pageh*0.05,
                         line_gap=6,
                         theta=th)
                eprint(lines)

                angles = []
                for ((x0,y0),(x1,y1)) in lines:
                    if abs(x1-x0) > abs(y1-y0):
                        # Horizontal - ensure it's moving East
                        k = 1 if x1 > x0 else -1
                        a = rad2deg(math.atan2(k*(y0-y1), k*(x1-x0)))
                        eprint("  XXX h line a: {}".format(a))
                    else:
                        # Vertical - ensure it's moving South
                        k = 1 if y1 > y0 else -1
                        a = rad2deg(math.atan2(k*(x1-x0), k*(y1-y0)))
                        eprint("  XXX v line a: {}".format(a))
                    angles.append( a )
                    rr, cc, val = line_aa(x0=x0, y0=y0, x1=x1, y1=y1)
                    for k, v in enumerate(val):
                        edgesg[rr[k], cc[k]] = (1-v)*edgesg[rr[k], cc[k]] + v

                imsave('out/{}_dilated.png'.format(filename), dilated)
                if angles:
                    a = mean(angles)
                    angle = a
                    imsave('out/{}_{}_lines_vertical.png'.format(filename, a), edgesg)
                    eprint("{}  angle vertical: {} deg (mean)  {} deg (median)".format(filename, a, median(angles)))
                else:
                    imsave('out/{}_dilate_edges.png'.format(filename), edges)
                    eprint("{}  FAILED vertical".format(filename))

    if angle:
        print("'{}'".format(f))
        print(angle)
        print("{}x{}".format(pagew, pageh))
        print(filename)
        sys.stdout.flush()
