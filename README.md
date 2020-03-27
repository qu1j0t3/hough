# hough - Skew detection in scanned images

<p align="center">
<a href="https://github.com/wohali/hough/actions"><img alt="Actions Status" src="https://github.com/wohali/hough/workflows/Tests/badge.svg"></a>
<a href="https://github.com/wohali/hough/blob/master/COPYING"><img src="https://img.shields.io/github/license/wohali/hough.svg" alt="GitHub license" /></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
</p>

_Hough_ finds skew angles in scanned document pages, using the Hough transform.

It is oriented to batch processing, and can make use of multiple cores. (You'll
want this - analysis and image processing is very CPU intensive!)

# Installation and usage

## Installation

Eventually, this will be published, so you'll be able to run `pip install hough`.
It requires Python 3.6.1+ to run.

For now, you'll need to install [Poetry](https://python-poetry.org/docs/#installation),
then run:

```
poetry run pip install -U pip setuptools
poetry install
poetry shell
```

The first line is required to update `pip` to a new enough version to be compatible with
`manylinux` wheel packaging, required for PyMuPDF.

## Usage

To get started right away, here's some examples.

Generate angles (in CSV form) for a bunch of TIFF page images, one page per file:

```
hough --csv in/*.tif
```

The same, but for a PDF file, and display a histogram at the end:

```
hough --histogram Able_Attach_Sep83.pdf
```

The same, but show progress while running:

```
hough -v --histogram Able_Attach_Sep83.pdf
```


The deskewing results are placed in the `results.csv` file. Example:

```csv
"Input File","Computed angle","Variance of computed angles","Image width (px)","Image height (px)"
"/home/toby/my-pages/orig/a--0000.pgm.tif",-0.07699791151672428,0.001073874144832815,5014,6659
"/home/toby/my-pages/orig/a--0001.pgm.tif",,,5018,6630
"/home/toby/my-pages/orig/a--0002.pgm.tif",0.24936351676615068,0.005137031681286154,5021,6629
"/home/toby/my-pages/orig/a--0003.pgm.tif",,,5020,6608
"/home/toby/my-pages/orig/a--0004.pgm.tif",-0.037485115754500545,0.025945115897015238,5021,6616
```

The program should work on various image input formats, and with both grey scale
and RGB images. _Hough_ works best with images ≥300dpi.

Here's a histogram sample:

```
=== Skew statistics ===
0.00° - 0.10°  [57]  ████████████████████████████████████████
0.10° - 0.20°  [39]  ███████████████████████████▍
0.20° - 0.30°  [30]  █████████████████████
0.30° - 0.40°  [30]  █████████████████████
0.40° - 0.50°  [11]  ███████▊
0.50° - 0.60°  [11]  ███████▊
0.60° - 0.70°  [ 3]  ██▏
0.70° - 0.80°  [ 4]  ██▊
0.80° - 0.90°  [ 0]
0.90° - 1.00°  [ 1]  ▊
1.00° - 1.10°  [ 1]  ▊
1.10° - 1.20°  [ 0]
1.20° - 1.30°  [ 1]  ▊
1.30° - 1.40°  [ 1]  ▊
1.40° - 1.50°  [ 1]  ▊
1.50° - 1.60°  [ 2]  █▍
1.60° - 1.70°  [ 0]
1.70° - 1.80°  [ 1]  ▊
1.80° - 1.90°  [ 2]  █▍
1.90° - 2.00°  [ 0]
Samples: 195
50th percentile: 0.20°
90th percentile: 0.55°
99th percentile: 1.77°
```

## Command line options

You can list them by running `hough --help`:

```
hough - straighten scanned pages using the Hough transform.

Usage:
  hough (-h | --help)
  hough [options] <file>...

Arguments:
  file                          Input file(s) to process

Options:
  -h --help                     Display this help and exit
  -v --verbose                  print status messages
  -d --debug                    retain debug image output in out/ directory
                                (also enables --verbose)
  --version                     Display the version number and exit
  -c --csv                      Save rotation results in CSV format
  --results=<file>              Save rotation results to named file.
                                Extension comes from format (.csv, ...)
                                [default: results]
  --histogram                   Display rotation angle histogram summary
                                (implies --csv)
  -j <jobs> --jobs=<jobs>       Specify the number of jobs to run
                                simultaneously. Default: total # of CPUs
```

# Examples

Just about all of [these files](http://docs.telegraphics.com.au/) have been
deskewed this way.

# Getting the best results

### NOTE: This is a beta product!

There's a few guidelines you should follow to get the best deskewing results
from your document scans:

1. Bilevel (black-and-white) bitmaps will produce lower quality results.
   For best results, scan to greyscale or RGB first, deskew with Hough, then
   reduce the colour depth to bilevel.
1. Hough deskewing is an inexact process, with many heuristics discovered
   by trial and error. _Hough_ may not work well on your material without tuning
   and further modification. (We'd love your pull requests!)

## Debugging output

You can spy on _Hough_'s attempts to perform deskewing by passing the `--debug`
flag on the command line. The generated images, and any detected lines in them,
are placed in the `out/<datetime>/` directory.

Note that _Hough_ cannot always determine a skew for a page (e.g. blank pages
in particular), and will very occasionally get the skew wrong (depending on
source material). It's worth reviewing these images if _Hough_ makes a bad
decision on your scans.

## Recommended scanners

The authors have tested this software with output from the following scanners:

* Fujitsu fi-4530C, USB
  * Fast
  * Cheap on eBay
  * Requires a Windows XP VirtualBox for drivers
* Brother ADS-2700W, USB + Ethernet + WiFi
  * Fast
  * Can scan directly to the network or to a memory stick
  * Factory reconditioned models stilll available (March 2020)
  * Very low skew out of the box
* Epson WF-7610, USB + Ethernet + WiFi
  * 11"x17" and duplex capable
  * Can scan directly to the network or to a memory stick

## License notice

```
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
```
