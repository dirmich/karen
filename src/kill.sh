#!/bin/sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd $DIR

export DISPLAY=:0
python3.7 ./karen.py --log-level debug --brain-exec kill_all