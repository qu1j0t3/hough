#!/bin/bash

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

CORES=${CORES:-4}
RCORES=${RCORES:-2}

echo "Using $CORES cores for skew analysis. (env var CORES)"
echo "Using $RCORES cores for rotation.     (env var RCORES)"
echo "(Adjust these defaults in distribute.sh)"
echo "Debugging output in out/    (please review after run)"
echo 'Rotated output in process/  (note that pages are skipped if skew was not computable!)'

(xargs -n 1 -P $CORES ./skew.py) | xargs -n 1 -P $RCORES ./rotate.sh
