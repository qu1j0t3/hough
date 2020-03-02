## A program for finding document skew angles using the Hough transform

I developed this to meet my scanning needs, since scanning pages through
ADF scanners* leads to unavoidable skew rates (sometimes as much as 2.5°).

As such it has no real user interface and is oriented to batch processing
on Linux or OS X. It can make use of multiple cores, because the
analysis and image processing is very CPU intensive.

#### Input data parameters

I use it with TIFF page images (one page per file),
as this is convenient on the scanning side, and fits all steps of my
personal workflow. However, the program should work on various input
formats, and both grey scale and RGB images.

* If you only have input bilevel bitmaps, things should still work,
  but the output quality will be less than desired. For best results,
  it is very important that deskewing is done on grey scale (or RGB) files.

*Most of the heuristics are tuned for resolutions around 300-600 dpi.*

If you want to see example documents, just about all of
[these files](http://docs.telegraphics.com.au/) have been deskewed this way.

*Please note:* This is an inexact process, with many heuristics discovered
by trial and error, and this software is still being improved.
It has worked on many thousands of pages of my own material, of varied layouts,
but may not work well on your material without tuning and modification.
(See comment below about debugging output.)

### Setting up

* If you want to actually fix rotations, you will need GraphicsMagick:
  - `sudo apt-get install graphicsmagick`
* Check out this repository and change working directory
  to the top level project directory
* Create a Python [virtual environment](https://docs.python.org/3/tutorial/venv.html)
  - `python3 -m venv .venv`
  - (On Ubuntu you may need to do this first: `sudo apt-get install python3-venv`)
* Activate it:
  - `source .venv/bin/activate`
* Install Python dependencies:
  - `pip install -r requirements.txt`

#### Troubleshooting

* If you see `error: invalid command 'bdist_wheel'`,
  try (from [this page](https://stackoverflow.com/a/44862371/173515):
  - `pip install wheel`
  - `pip install -r requirements.txt`

### How can I get skew angles for my pages

The skew calculator is `skew.py`.

The arguments are a list of input filenames.

You could use `ls | xargs ./skew.py` to provide these names,
but this will use just one core for processing.

The output is CSV for further use:

    (.venv) toby@w8pc:~/hough$ ls ~/my-pages/orig/* |head -5|xargs ./skew.py 2> /dev/null
    "/home/toby/my-pages/orig/a--0000.pgm.tif",-0.07699791151672428,0.001073874144832815,5014,6659
    "/home/toby/my-pages/orig/a--0001.pgm.tif",,,5018,6630
    "/home/toby/my-pages/orig/a--0002.pgm.tif",0.24936351676615068,0.005137031681286154,5021,6629
    "/home/toby/my-pages/orig/a--0003.pgm.tif",,,5020,6608
    "/home/toby/my-pages/orig/a--0004.pgm.tif",-0.037485115754500545,0.025945115897015238,5021,6616

The CSV columns are:
* Full path to input file
* Computed angle
* Variance of computed angles (not currently used)
* Page width in pixels
* Page height in pixels

#### Debugging output

Note that `skew.py` cannot always determine a skew for a page
(e.g. blank pages in particular), and will sometimes get the skew wrong
(in my experience much less than 1% of the time, depending on source material).
Therefore it produces debugging images for review, in the `out/` directory
in the working directory.
*You should review these files before shipping the final result.
Or at least, review the auto-rotated pages.*

### Batch skew analysis and rotation

To run a batch job on multiple cores, including both analysis and
the corrective rotation, use this command:

    ls /path/to/pages/* | ./distribute.sh

(The number of concurrent cores is defined in that script.
I have an 8 core machine, so I typically use six.)

Output, file per page, is to the `process/` directory in the current
working directory (which can be a symlink to somewhere else).


* - I use a *Fujitsu fi-4530C, USB model,* which is fast, high quality,
    and cheaply available on ebay if you have some patience to deal with
    its Windows XP driver (VirtualBox works). I've done thousands of pages
    with mine.


    This file is part of "hough", which detects skew angles in scanned images
    Copyright (C) 2016-2020 Toby Thain, toby@telegraphics.com.au

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
