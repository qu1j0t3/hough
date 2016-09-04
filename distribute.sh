#!/bin/bash

(xargs -n 1 -P 6 ./skew.py) | xargs -n 1 -P 2 ./rotate.sh
