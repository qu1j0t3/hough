#!/bin/bash

echo $1|( IFS=, read FILEPATH ANGLE VARIANCE PAGEW PAGEH
  # -extent converts it to RGB :(
  if [ "$ANGLE" ] ; then
    gm convert "$FILEPATH" \
      -rotate $ANGLE \
      -gravity center -extent ${PAGEW}x${PAGEH} \
      -channel Green \
      process/`basename "$FILEPATH"`
  fi
)
