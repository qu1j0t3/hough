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
from scipy.ndimage import imread, measurements
from scipy.misc import imresize, imsave
from numpy import *

import os
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Pipe the output to    ./distribute.sh

for f in sys.argv[1:]:
    filename = os.path.basename(f)
    #if i == 30:
    #    exit()
    pos = imread(f)
    pageh, pagew = pos.shape

    #neg = img_as_ubyte(pos < t)
    neg = 255-pos

    # find row with maximum sum - this should pass thru the centre of the horizontal rule

    def sum(a):
        return a.sum()
    sums = np.apply_along_axis(sum, 1, neg)
    row = sums.argmax(0)

    eprint(filename)

    angle = None

    # Ignore peaks that are too close to edge of page.
    if row > 150 and row < pageh-150:

        # Detect edges
        edges = binary_dilation( canny(pos[row-100:row+100], 2) )
        # Now try Hough transform
        lines = probabilistic_hough_line(
                 edges,
                 line_length=pagew*0.2,
                 theta=arange(deg2rad(-93.0), deg2rad(-87.0), deg2rad(0.02)))

        def grey(x):
            return 0.5 if x else 0.0
        greyf = np.vectorize(grey)
        edgesg = greyf(edges)

        angles = []
        for x in lines:
            ((x0,y0),(x1,y1)) = x
            # Ensure line is in East quadrants
            if x1 < x0:
                x0, x1, y0, y1 = x1, x0, y1, y0
            rr, cc, val = line_aa(x0=x0, y0=y0, x1=x1, y1=y1)
            angles.append(math.atan2(y1-y0, x1-x0))
            for j, v in enumerate(val):
                edgesg[rr[j], cc[j]] = (1-v)*edgesg[rr[j], cc[j]] + v

        if angles:
            a = rad2deg(mean(angles))
            eprint("  mean angle: {} deg".format(a))
            angle = -a
            imsave('out/{}_{}_edges.png'.format(filename, a), edgesg)
        else:
            eprint("  no lines detected by Probabilistic Hough")

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
                eprint("  found rule: {}  aspect: {}  angle: {} deg".format(thinnest.label, aspectmax, a))
                # Drop other labels
                def relabel(x):
                    return x if x == thinnest.label else 0
                relabel_func = np.vectorize(relabel)
                relabelled = relabel_func(labels)
                out = mark_boundaries(pos[row-100:row+100], relabelled, color=(1,0,0))
                imsave('out/{}.png'.format(filename), out)
                angle = a
            else:
                eprint("  did not find rule")
    else:
        eprint("  Horizontal peak was too close to page margin, probably bogus")

    if angle:
        print("'{}'".format(f))
        print(angle)
        print("{}x{}".format(pagew, pageh))
        print(filename)
        sys.stdout.flush()
