#!/bin/bash

gm convert "$1" -rotate $2 -gravity center -extent $3 process/$4
