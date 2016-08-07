#!/bin/bash

./skew.py $* | xargs -L 4 -P 2 ./rotate.sh
