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

echo $1|( IFS=, read FILEPATH ANGLE VARIANCE PAGEW PAGEH
  # -extent converts it to RGB :(
  if [ "$ANGLE" ] ; then
    gm convert "$FILEPATH" \
      -rotate $ANGLE \
      -gravity center -extent ${PAGEW}x${PAGEH} \
      process/`basename "$FILEPATH"`
  fi
)
